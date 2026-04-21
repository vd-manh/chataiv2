import math
import os
import re

from retrieval_utility import (
    retrieve_with_mmr_and_rerank,
    build_metadata_filter,
    get_subject_retrieval_config,
    rerank_documents,
)

# --- Cấu hình thông báo mặc định ---
LOW_RELIABILITY_MESSAGE = "Rất tiếc, tôi không tìm thấy thông tin đủ tin cậy trong tài liệu để trả lời câu hỏi này."


def _mode_instruction(query_mode):
    mode = (query_mode or "Explain").strip().lower()
    if mode == "exam answer":
        return "Provide a structured exam-style answer with clear headings and a concise conclusion."
    if mode == "short notes":
        return "Provide brief summary notes in bullet points (5-8 lines)."
    return "Explain clearly and academically."


def _detect_language(text):
    """
    Phát hiện ngôn ngữ dựa trên Unicode range.
    Hỗ trợ: Korean, Arabic, Chinese, Japanese, Thai, Russian, Hindi, Vietnamese.
    Fallback: 'english'
    """
    if not text:
        return "english"
    total = len(text.strip())
    if total == 0:
        return "english"

    def ratio(pattern):
        return len(re.findall(pattern, text)) / total

    # Korean (Hangul)
    if ratio(r'[\uAC00-\uD7AF\u1100-\u11FF\u3130-\u318F\uA960-\uA97F\uD7B0-\uD7FF]') > 0.08:
        return "korean"
    # Arabic (Ả Rập, Farsi, Urdu)
    if ratio(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]') > 0.08:
        return "arabic"
    # Japanese (Hiragana/Katakana — check trước Chinese vì Kanji overlap)
    if ratio(r'[\u3040-\u309F\u30A0-\u30FF\uFF65-\uFF9F]') > 0.05:
        return "japanese"
    # Chinese (Simplified + Traditional)
    if ratio(r'[\u4E00-\u9FFF\u3400-\u4DBF\uF900-\uFAFF]') > 0.08:
        return "chinese"
    # Thai
    if ratio(r'[\u0E00-\u0E7F]') > 0.08:
        return "thai"
    # Russian / Cyrillic
    if ratio(r'[\u0400-\u04FF\u0500-\u052F]') > 0.08:
        return "russian"
    # Hindi / Devanagari
    if ratio(r'[\u0900-\u097F\uA8E0-\uA8FF]') > 0.08:
        return "hindi"
    # Vietnamese (dấu thanh đặc trưng)
    if ratio(
        r'[àáảãạăắặằẳẵâấậầẩẫèéẻẽẹêếệềểễ'
        r'ìíỉĩịòóỏõọôốộồổỗơớợờởỡùúủũụưứựừửữỳýỷỹỵđ'
        r'ÀÁẢÃẠĂẮẶẰẲẴÂẤẬẦẨẪÈÉẺẼẸÊẾỆỀỂỄ'
        r'ÌÍỈĨỊÒÓỎÕỌÔỐỘỒỔỖƠỚỢỜỞỠÙÚỦŨỤƯỨỰỪỬỮỲÝỶỸỴĐ]'
    ) > 0.04:
        return "vietnamese"
    return "english"


# Tên hiển thị đầy đủ
_LANG_LABEL = {
    "korean":     "Korean (한국어)",
    "arabic":     "Arabic (العربية)",
    "chinese":    "Chinese (中文)",
    "japanese":   "Japanese (日本語)",
    "thai":       "Thai (ภาษาไทย)",
    "russian":    "Russian (Русский)",
    "hindi":      "Hindi (हिन्दी)",
    "vietnamese": "Vietnamese (Tiếng Việt)",
    "english":    "English",
}


def _language_instruction(user_input):
    """
    Trả về (instruction_str, lang_code).
    Tạo instruction động — hoạt động với bất kỳ ngôn ngữ nào detect được.
    """
    lang = _detect_language(user_input)
    label = _LANG_LABEL.get(lang, "English")

    instruction = (
        f"ABSOLUTE LANGUAGE RULE — VIOLATION IS NOT ALLOWED:\n"
        f"The user's question is written in {label.upper()}.\n"
        f"You MUST respond in {label} only — every single sentence, every single word.\n"
        f"Do NOT use English or any other language anywhere in your response.\n"
        f"Even if the source documents are in English or another language, "
        f"you MUST translate your entire response into {label}."
    )
    return instruction, lang


def format_context(scored_docs, limit=3):
    if not scored_docs:
        return ""
    context_parts = []
    for idx, (doc, _) in enumerate(scored_docs[:limit], start=1):
        metadata = doc.metadata or {}
        filename = os.path.basename(
            metadata.get("filename") or metadata.get("source") or "Document"
        )
        page_number = metadata.get("page", "N/A")
        if isinstance(page_number, int):
            page_number += 1
        context_parts.append(
            f"[Source {idx}] File: {filename} | Page: {page_number}\n"
            f"{doc.page_content.strip()}"
        )
    return "\n\n".join(context_parts)


def build_citations(scored_docs, limit=4):
    if not scored_docs:
        return []
    citations = []
    for doc, score in scored_docs[:limit]:
        metadata = doc.metadata or {}
        page = metadata.get("page")
        if isinstance(page, int):
            page += 1
        filename = os.path.basename(
            metadata.get("filename") or metadata.get("source") or "Doc"
        )
        citations.append({
            "filename": filename,
            "page": page or "N/A",
            "score": float(score),
            "snippet": doc.page_content[:200].strip(),
        })
    return citations


def _retrieve_scored_docs(
    user_input, selected_subject, selected_chapter,
    vectorstore, reranker, use_metadata_filter
):
    scored_docs = []
    confidence = 0.0

    subj_name = selected_subject if selected_subject else "physics"
    retrieval_cfg = get_subject_retrieval_config(subj_name.lower())

    try:
        if use_metadata_filter and selected_chapter and selected_chapter != "All":
            scored_docs, confidence, retrieval_cfg = retrieve_with_mmr_and_rerank(
                vectorstore=vectorstore,
                query=user_input,
                subject=selected_subject,
                chapter=selected_chapter,
                reranker=reranker,
            )
        else:
            search_kwargs = {"k": 6}
            if selected_subject:
                search_kwargs["filter"] = {"subject": selected_subject}

            docs = vectorstore.similarity_search(user_input, **search_kwargs)

            if docs:
                if reranker:
                    scored_docs = rerank_documents(
                        query=user_input, docs=docs, reranker=reranker, top_n=3
                    )
                else:
                    scored_docs = [(doc, 0.9) for doc in docs]

                if scored_docs:
                    confidence = (
                        1.0 / (1.0 + math.exp(-scored_docs[0][1]))
                        if reranker
                        else 0.9
                    )

    except Exception as e:
        print(f"[LOG] Retrieval Error: {e}")
        scored_docs = []

    return scored_docs, confidence, retrieval_cfg


def answer_from_sources(
    user_input,
    selected_subject,
    selected_chapter,
    chat_history,
    vectorstore,
    llm,
    reranker,
    query_mode="Explain",
    output_language="Auto",
    use_metadata_filter=False,
    low_reliability_message=LOW_RELIABILITY_MESSAGE,
):
    # 1. Retrieve
    scored_docs, confidence, _ = _retrieve_scored_docs(
        user_input, selected_subject, selected_chapter,
        vectorstore, reranker, use_metadata_filter
    )

    # 2. Kiểm tra độ tin cậy
    if not scored_docs or confidence < 0.35:
        return low_reliability_message, True, []

    # 3. Chuẩn bị Prompt
    context_text = format_context(scored_docs)
    citations = build_citations(scored_docs)

    lang_rule, detected_lang = _language_instruction(user_input)
    mode_inst = _mode_instruction(query_mode)
    target_lang = _LANG_LABEL.get(detected_lang, "English")

    prompt = f"""SYSTEM ROLE: You are an academic assistant helping students understand course materials.

{'='*60}
{lang_rule}
{'='*60}

TASK RULES:
1. Use ONLY the [Context] below. Do NOT use outside knowledge.
2. If context is insufficient, say so IN {target_lang}.
3. {mode_inst}

[Context]:
{context_text}

{'='*60}
[Question] (in {target_lang}): {user_input}
{'='*60}

ANSWER (write entirely in {target_lang} — no other language):"""

    response = llm.invoke(prompt)
    return response.content.strip(), False, citations