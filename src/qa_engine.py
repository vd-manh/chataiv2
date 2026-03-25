import math
import os

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

def _language_instruction():
    # Ép AI nhận diện ngôn ngữ cực kỳ nghiêm ngặt
    return (
        "STRICT RULE: Identify the language of the User's question. "
        "You MUST respond ONLY in that language. "
        "If Question is in English -> Answer in English. "
        "If Question is in Vietnamese -> Answer in Vietnamese. "
        "If Question is in Korean -> Answer in Korean. "
        "Ignore the language of the Context/Source text."
    )

def format_context(scored_docs, limit=3):
    if not scored_docs:
        return ""
    context_parts = []
    for idx, (doc, _) in enumerate(scored_docs[:limit], start=1):
        metadata = doc.metadata or {}
        filename = os.path.basename(metadata.get("filename") or metadata.get("source") or "Document")
        page_number = metadata.get("page", "N/A")
        if isinstance(page_number, int): page_number += 1
        
        context_parts.append(
            f"[Source {idx}] File: {filename} | Page: {page_number}\n{doc.page_content.strip()}"
        )
    return "\n\n".join(context_parts)

def build_citations(scored_docs, limit=4):
    if not scored_docs:
        return []
    citations = []
    for doc, score in scored_docs[:limit]:
        metadata = doc.metadata or {}
        page = metadata.get("page")
        if isinstance(page, int): page += 1
        filename = os.path.basename(metadata.get("filename") or metadata.get("source") or "Doc")

        citations.append({
            "filename": filename,
            "page": page or "N/A",
            "score": float(score),
            "snippet": doc.page_content[:200].strip()
        })
    return citations

def _retrieve_scored_docs(user_input, selected_subject, selected_chapter, vectorstore, reranker, use_metadata_filter):
    # Khởi tạo mặc định để tránh lỗi UnboundLocalError
    scored_docs = []
    confidence = 0.0
    
    # Sửa lỗi biến 'subj' chưa định nghĩa
    subj_name = selected_subject if selected_subject else "physics"
    retrieval_cfg = get_subject_retrieval_config(subj_name.lower())

    try:
        # TH 1: Tìm kiếm có lọc theo Chương (Metadata filtering)
        if use_metadata_filter and selected_chapter and selected_chapter != "All":
            scored_docs, confidence, retrieval_cfg = retrieve_with_mmr_and_rerank(
                vectorstore=vectorstore,
                query=user_input,
                subject=selected_subject,
                chapter=selected_chapter,
                reranker=reranker,
            )
        
        # TH 2: Tìm kiếm tự do (Dành cho My Documents hoặc môn học tổng quát)
        else:
            search_kwargs = {"k": 6}
            if selected_subject:
                search_kwargs["filter"] = {"subject": selected_subject}
            
            # 1. Tìm kiếm docs trước
            docs = vectorstore.similarity_search(user_input, **search_kwargs)
            
            if docs:
                # 2. Nếu có reranker thì mới dùng, không thì dùng docs gốc
                if reranker:
                    scored_docs = rerank_documents(query=user_input, docs=docs, reranker=reranker, top_n=3)
                else:
                    scored_docs = [(doc, 0.9) for doc in docs] # Gán score mặc định 0.9
                
                # 3. Tính toán confidence
                if scored_docs:
                    confidence = 1.0 / (1.0 + math.exp(-scored_docs[0][1])) if reranker else 0.9

    except Exception as e:
        print(f"[LOG] Retrieval Error: {e}")
        scored_docs = []
    
    return scored_docs, confidence, retrieval_cfg

def answer_from_sources(
    user_input, selected_subject, selected_chapter, chat_history, vectorstore, 
    llm, reranker, query_mode="Explain", output_language="Auto",
    use_metadata_filter=False, low_reliability_message=LOW_RELIABILITY_MESSAGE
):
    # 1. Lấy dữ liệu từ DB (Hàm này giờ đã trả về đúng 3 giá trị)
    scored_docs, confidence, _ = _retrieve_scored_docs(
        user_input, selected_subject, selected_chapter, vectorstore, reranker, use_metadata_filter
    )

    # 2. Kiểm tra độ tin cậy (Threshold 0.35)
    if not scored_docs or confidence < 0.35:
        return low_reliability_message, True, []

    # 3. Chuẩn bị Prompt
    context_text = format_context(scored_docs)
    citations = build_citations(scored_docs)
    lang_rule = _language_instruction()
    mode_inst = _mode_instruction(query_mode)

    prompt = f"""
SYSTEM ROLE:
You are an academic assistant.
{lang_rule}

STRICT RULES:
1. Use ONLY the Context below to answer.
2. Respond in the EXACT language of the Question.
3. If context is missing info, say you don't know in the user's language.
4. {mode_inst}

[Context]:
{context_text}

[Question]: {user_input}

Final Answer (in the same language as the Question):
"""
    response = llm.invoke(prompt)
    return response.content.strip(), False, citations