import sys
# 1. ÉP DÙNG PYSQLITE3 (BẮT BUỘC)
try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

import os
import shutil
from pathlib import Path
import streamlit as st

# 2. CẤU HÌNH TRANG
st.set_page_config(
    page_title="VM AI 학습 어시스턴트",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- ĐƯỜNG DẪN (ĐỒNG BỘ VỚI FAST_INGEST.PY) ---
BASE_DIR = Path(__file__).resolve().parent.parent
UNIFIED_VECTOR_DB_PATH = str(BASE_DIR / "vector_db" / "class_12_unified_vector_db")
PDF_SAVE_PATH = str(BASE_DIR / "data" / "my_doc")
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")                        # chataiv2/.env  ← ưu tiên
load_dotenv(BASE_DIR / "src" / ".env", override=False) # src/.env      ← fallbackgit push origin main

# --- CSS ---
st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', 'Noto Sans KR', sans-serif;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #0f172a 0%, #1e293b 100%);
    border-right: 1px solid rgba(99,102,241,0.2);
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] .stRadio label,
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stFileUploader label {
    color: #94a3b8 !important;
    font-size: 0.78rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-weight: 600;
}
section[data-testid="stSidebar"] h1 {
    font-size: 1.3rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #818cf8, #c084fc);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    padding-bottom: 0.5rem;
}
section[data-testid="stSidebar"] h2, 
section[data-testid="stSidebar"] h3 {
    font-size: 0.85rem !important;
    font-weight: 700 !important;
    color: #94a3b8 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
section[data-testid="stSidebar"] hr {
    border-color: rgba(99,102,241,0.25) !important;
    margin: 1rem 0 !important;
}

/* ── Main area ── */
.main .block-container {
    padding-top: 2.5rem;
    padding-bottom: 8rem;
    max-width: 900px;
}

/* ── Page header ── */
.vm-header {
    text-align: center;
    margin-bottom: 2rem;
}
.vm-header h1 {
    font-size: 2.1rem;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #06b6d4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
    margin-bottom: 0.3rem;
}
.vm-header p {
    color: #64748b;
    font-size: 0.9rem;
}

/* ── Chat messages ── */
.stChatMessage {
    border-radius: 16px !important;
    border: 1px solid rgba(99,102,241,0.12) !important;
    margin-bottom: 12px !important;
    backdrop-filter: blur(4px);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 2px solid rgba(99,102,241,0.15);
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px 8px 0 0 !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: #64748b !important;
    padding: 6px 14px !important;
}
.stTabs [aria-selected="true"] {
    color: #6366f1 !important;
    background: rgba(99,102,241,0.08) !important;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #a855f7) !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 0.85rem !important;
    padding: 0.55rem 1.2rem !important;
    transition: opacity 0.2s ease !important;
    width: 100%;
}
.stButton > button[kind="primary"]:hover {
    opacity: 0.88 !important;
}
.stButton > button:not([kind="primary"]) {
    border-radius: 10px !important;
    border: 1px solid rgba(99,102,241,0.3) !important;
    color: #94a3b8 !important;
    background: transparent !important;
    font-size: 0.82rem !important;
    width: 100%;
}
.stButton > button:not([kind="primary"]):hover {
    border-color: #ef4444 !important;
    color: #ef4444 !important;
}

/* ── Chat input ── */
.stChatInputContainer {
    border-top: 1px solid rgba(99,102,241,0.15) !important;
    padding-top: 1rem !important;
}

/* ── Info / warning boxes ── */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
}

/* ── Citation caption ── */
.citation-card {
    background: rgba(99,102,241,0.06);
    border-left: 3px solid #6366f1;
    border-radius: 0 8px 8px 0;
    padding: 8px 12px;
    margin: 6px 0;
    font-size: 0.82rem;
    color: #94a3b8;
}

/* ── Welcome card ── */
.welcome-card {
    background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.06));
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 16px;
    padding: 2rem;
    text-align: center;
    margin: 2rem auto;
    max-width: 560px;
}
.welcome-card h3 {
    font-size: 1.25rem;
    font-weight: 700;
    color: #6366f1;
    margin-bottom: 0.5rem;
}
.welcome-card p {
    color: #64748b;
    font-size: 0.9rem;
    line-height: 1.6;
}
</style>
""", unsafe_allow_html=True)

# --- IMPORT MODULES ---
from get_yt_video import get_yt_video_link
from qa_engine import answer_from_sources
from fast_ingest import run_ingest
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

# --- RESOURCE FUNCTIONS ---
@st.cache_resource(show_spinner=False)
def get_embeddings():
    return HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")

def get_vectorstore():
    if not os.path.exists(UNIFIED_VECTOR_DB_PATH) or not os.listdir(UNIFIED_VECTOR_DB_PATH):
        return None
    try:
        return Chroma(
            persist_directory=UNIFIED_VECTOR_DB_PATH,
            embedding_function=get_embeddings()
        )
    except Exception:
        return None

@st.cache_resource(show_spinner=False)
def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

@st.cache_resource(show_spinner=False)
def get_reranker():
    try:
        return CrossEncoder("BAAI/bge-reranker-base")
    except Exception:
        return None

# --- LANGUAGE DICTIONARY (Korean UI, consistent) ---
LANG = {
    # Sidebar
    "sidebar_title": "🎓 VM AI",
    "sidebar_subtitle": "학습 어시스턴트",
    "query_mode": "조회 모드",
    "mode_subject": "📚 선택 과목",
    "mode_docs": "📄 내 문서",
    "subject_select": "과목 선택",
    "chapter_input": "단원 입력 (선택 사항)",
    "chapter_placeholder": "예: 1. Introduction (비우면 전체 검색)",
    "manage_kb": "지식 베이스 관리",
    "upload_pdf": "PDF 문서 업로드",
    "update_btn": "🚀 업데이트",
    "clear_btn": "🗑️ 데이터 초기화",
    # Main
    "page_title": "VM AI 학습 어시스턴트",
    "page_subtitle": "RAG 기반 대학 강의 지원 챗봇",
    # Tabs
    "tab_ans": "💡 답변",
    "tab_src": "📄 참고 자료",
    "tab_vid": "🎥 관련 영상",
    # Status messages
    "status_ingest": "문서를 분석하고 있습니다...",
    "status_success": "완료! {num}개의 지식 블록을 학습했습니다.",
    "status_search": "관련 내용을 검색하고 답변을 생성 중입니다...",
    # Empty states
    "no_src": "관련 출처를 찾을 수 없습니다.",
    "no_vid": "관련 영상을 찾을 수 없습니다.",
    "no_db_warning": "⚠️ PDF를 먼저 업로드하고 '업데이트' 버튼을 눌러주세요!",
    # Input
    "input_placeholder": "문서에 대해 질문하세요... (한국어, 영어, 베트남어 가능)",
    # Welcome
    "welcome_title": "안녕하세요! 👋",
    "welcome_body": (
        "왼쪽 사이드바에서 PDF 문서를 업로드하고 "
        "🚀 업데이트 버튼을 누른 후 질문을 시작하세요.\n\n"
        "한국어, 영어, 베트남어로 질문하실 수 있습니다."
    ),
    # Citation label
    "page_label": "페이지",
}

# --- SESSION STATE INIT ---
for key in ["chat_history", "video_history", "citation_history"]:
    if key not in st.session_state:
        st.session_state[key] = []

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.title(LANG["sidebar_title"])
    st.caption(LANG["sidebar_subtitle"])
    st.divider()

    # 모드 선택
    st.subheader(LANG["query_mode"])
    source_mode_label = st.radio(
        label="mode",
        options=[LANG["mode_docs"], LANG["mode_subject"]],
        index=0,
        label_visibility="collapsed",
    )
    source_mode = "My Documents" if source_mode_label == LANG["mode_docs"] else "Selected Subjects"

    st.divider()

    # 과목/챕터 (Subject 모드일 때만)
    selected_subject = None
    selected_chapter = ""
    if source_mode == "Selected Subjects":
        selected_subject = st.selectbox(
            LANG["subject_select"],
            ["Physics", "Chemistry", "Biology", "Math"],
        )
        selected_chapter = st.text_input(
            LANG["chapter_input"],
            placeholder=LANG["chapter_placeholder"],
        )
        st.divider()

    # 지식베이스 관리
    st.subheader(LANG["manage_kb"])
    uploaded_files = st.file_uploader(
        LANG["upload_pdf"],
        type=["pdf"],
        accept_multiple_files=True,
        label_visibility="visible",
    )

    col_up, col_clr = st.columns(2)
    with col_up:
        update_clicked = st.button(LANG["update_btn"], type="primary", use_container_width=True)
    with col_clr:
        clear_clicked = st.button(LANG["clear_btn"], use_container_width=True)

    if update_clicked:
        if uploaded_files:
            with st.status(LANG["status_ingest"], expanded=True) as status:
                os.makedirs(PDF_SAVE_PATH, exist_ok=True)
                for f in uploaded_files:
                    with open(os.path.join(PDF_SAVE_PATH, f.name), "wb") as pf:
                        pf.write(f.getbuffer())
                num = run_ingest()
                status.update(
                    label=LANG["status_success"].format(num=num),
                    state="complete",
                )
            st.rerun()
        else:
            st.warning("업로드할 파일을 선택해주세요.")

    if clear_clicked:
        shutil.rmtree(str(BASE_DIR / "vector_db"), ignore_errors=True)
        shutil.rmtree(PDF_SAVE_PATH, ignore_errors=True)
        st.session_state.chat_history = []
        st.session_state.citation_history = []
        st.session_state.video_history = []
        st.rerun()

# ============================================================
# MAIN AREA
# ============================================================
st.markdown(
    f"""
    <div class="vm-header">
        <h1>{LANG['page_title']}</h1>
        <p>{LANG['page_subtitle']}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

active_vs = get_vectorstore()

# Welcome 카드 (DB 없을 때)
if active_vs is None and not st.session_state.chat_history:
    st.markdown(
        f"""
        <div class="welcome-card">
            <h3>{LANG['welcome_title']}</h3>
            <p>{LANG['welcome_body'].replace(chr(10), '<br>')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── 응답 렌더링 함수 ──────────────────────────────────────────
def render_assistant_response(ans, cits, vids):
    t1, t2, t3 = st.tabs([LANG["tab_ans"], LANG["tab_src"], LANG["tab_vid"]])

    with t1:
        st.markdown(ans)

    with t2:
        if cits:
            for c in cits:
                st.markdown(
                    f"<div class='citation-card'>"
                    f"📌 <strong>{c.get('filename', 'N/A')}</strong> "
                    f"— {LANG['page_label']} {c.get('page', 'N/A')}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                if c.get("snippet"):
                    with st.expander("미리보기", expanded=False):
                        st.caption(c["snippet"])
        else:
            st.info(LANG["no_src"])

    with t3:
        if vids:
            for title, link in vids:
                col1, col2 = st.columns([1, 2])
                col1.video(link)
                col2.markdown(f"**{title}**")
        else:
            st.info(LANG["no_vid"])


# ── 채팅 히스토리 표시 ────────────────────────────────────────
for i, msg in enumerate(st.session_state.chat_history):
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            idx = i // 2
            if idx < len(st.session_state.citation_history):
                render_assistant_response(
                    msg["content"],
                    st.session_state.citation_history[idx],
                    st.session_state.video_history[idx],
                )
        else:
            st.markdown(msg["content"])


# ── 입력창 ───────────────────────────────────────────────────
user_input = st.chat_input(LANG["input_placeholder"])

if user_input:
    # DB 재확인
    active_vs = get_vectorstore()

    if active_vs is None:
        st.warning(LANG["no_db_warning"])
    else:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner(LANG["status_search"]):
                # 모드에 따른 subject 결정
                query_subject = selected_subject if source_mode == "Selected Subjects" else "My Documents"
                query_chapter = selected_chapter if source_mode == "Selected Subjects" else "All"

                ans, low_conf, cits = answer_from_sources(
                    user_input=user_input,
                    selected_subject=query_subject,
                    selected_chapter=query_chapter,
                    chat_history=st.session_state.chat_history,
                    vectorstore=active_vs,
                    llm=get_llm(),
                    reranker=get_reranker(),
                    query_mode="Explain",
                    output_language="Auto",
                )

                vids = []
                try:
                    t, l = get_yt_video_link(user_input)
                    if t and l:
                        vids = [(t[i], l[i]) for i in range(min(3, len(t)))]
                except Exception:
                    pass

            render_assistant_response(ans, cits, vids)
            st.session_state.chat_history.append({"role": "assistant", "content": ans})
            st.session_state.citation_history.append(cits)
            st.session_state.video_history.append(vids)
            st.rerun()