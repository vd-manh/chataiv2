import sys

try:
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    # Nếu chạy local (Windows/Mac) không có pysqlite3 thì bỏ qua
    pass

import streamlit as st
# ... các dòng import phía sau giữ nguyên
import os
import uuid
import shutil
from datetime import datetime
import streamlit as st
import pysqlite3


# --- CẤU HÌNH TRANG (PHẢI ĐẶT ĐẦU TIÊN) ---
st.set_page_config(
    page_title="VMVM AI", 
    page_icon="🎓", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- THIẾT KẾ GIAO DIỆN (CSS CUSTOM) ---
st.markdown("""
    <style>
    .stApp { color: var(--text-color); }
    .chat-header h1 {
        text-align: center;
        padding-bottom: 1.5rem;
        font-weight: 800;
        color: inherit; 
    }
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    section[data-testid="stSidebar"] {
        border-right: 1px solid rgba(128, 128, 128, 0.2);
    }
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 4px;
        padding: 5px 15px;
        font-weight: 600;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 10rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- IMPORT CÁC MODULE ---
from app_config import load_project_env, resolve_device, get_unified_vector_db_path
from chatbot_utility import get_chapter_list
from get_yt_video import get_yt_video_link
from observability import get_logger
from qa_engine import answer_from_sources
from fast_ingest import run_ingest 
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder

# --- KHỞI TẠO CẤU HÌNH ---
working_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = load_project_env(working_dir)
DEVICE = resolve_device()
UNIFIED_VECTOR_DB_PATH = get_unified_vector_db_path(parent_dir)
subjects_list = ["Physics", "Chemistry", "Biology", "Math"]
logger = get_logger()

# --- CÁC HÀM GET RESOURCE (CACHE) ---
@st.cache_resource(show_spinner=False)
def get_embeddings():
    model_name = "paraphrase-multilingual-MiniLM-L12-v2" 
    return HuggingFaceEmbeddings(model_name=model_name, model_kwargs={"device": DEVICE})

@st.cache_resource(show_spinner=False)
def get_vectorstore():
    if not os.path.exists(UNIFIED_VECTOR_DB_PATH):
        os.makedirs(os.path.dirname(UNIFIED_VECTOR_DB_PATH), exist_ok=True)
        return None
    return Chroma(persist_directory=UNIFIED_VECTOR_DB_PATH, embedding_function=get_embeddings())

@st.cache_resource(show_spinner=False)
def get_llm():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

@st.cache_resource(show_spinner=False)
def get_reranker():
    try: return CrossEncoder("BAAI/bge-reranker-base")
    except: return None

# --- TỪ ĐIỂN NGÔN NGỮ (KOREAN) ---
LANG = {
    "title": "학습 어시스턴트",
    "sidebar_title": "🎓 Study Sphere",
    "query_mode": "🔍 조회 모드 선택",
    "mode_subject": "선택 과목",
    "mode_docs": "내 문서 (PDF)",
    "subject_select": "과목 선택:",
    "chapter_input": "단원 입력 (전체 질문 시 비워둠):",
    "manage_kb": "📂 지식 베이스 관리",
    "upload_pdf": "새 PDF 문서 업로드",
    "update_btn": "🚀 시스템 업데이트",
    "clear_btn": "🗑️ 모든 데이터 초기화",
    "input_placeholder": "문서에 대해 질문하세요...",
    "welcome_msg": "안녕하세요! 학습 도우미입니다. 왼쪽에서 문서를 업로드하고 질문을 시작하세요.",
    "tab_ans": "💡 답변",
    "tab_src": "📄 참고 문헌",
    "tab_vid": "🎥 추천 영상",
    "status_ingest": "데이터 분석 중...",
    "status_success": "성공! {num}개의 지식 조각을 학습했습니다.",
    "status_search": "지식을 검색하고 답변을 생성 중입니다...",
    "no_src": "관련 출처를 찾을 수 없습니다."
}

# --- KHỞI TẠO SESSION STATE ---
for key in ["chat_history", "video_history", "citation_history", "session_id"]:
    if key not in st.session_state:
        st.session_state[key] = [] if "history" in key else uuid.uuid4().hex[:12]

# --- QUAN TRỌNG: KHỞI TẠO VECTORSTORE TRƯỚC SIDEBAR ---
if 'active_vectorstore' not in st.session_state:
    st.session_state.active_vectorstore = get_vectorstore()

active_vectorstore = st.session_state.active_vectorstore

# --- SIDEBAR QUẢN LÝ ---
with st.sidebar:
    st.title(LANG["sidebar_title"])
    
    st.header(LANG["query_mode"])
    source_mode_kr = st.radio(LANG["query_mode"], [LANG["mode_subject"], LANG["mode_docs"]], index=1, label_visibility="collapsed")
    source_mode = "Selected Subjects" if source_mode_kr == LANG["mode_subject"] else "My Documents"
    
    selected_subject = None
    selected_chapter = ""
    
    if source_mode == "Selected Subjects":
        selected_subject = st.selectbox(LANG["subject_select"], subjects_list)
        selected_chapter = st.text_input(LANG["chapter_input"])

    st.divider()
    st.header(LANG["manage_kb"])
    uploaded_files = st.file_uploader(LANG["upload_pdf"], type="pdf", accept_multiple_files=True)

    if st.button(LANG["update_btn"], type="primary"):
        if uploaded_files:
            with st.status(LANG["status_ingest"], expanded=True) as status:
                st.cache_resource.clear()
                save_path = os.path.join(parent_dir, "data", "my_doc")
                os.makedirs(save_path, exist_ok=True)
                for f in uploaded_files:
                    with open(os.path.join(save_path, f.name), "wb") as pf:
                        pf.write(f.getbuffer())
                num = run_ingest() 
                # Cập nhật lại vectorstore sau khi ingest
                st.session_state.active_vectorstore = get_vectorstore()
                status.update(label=LANG["status_success"].format(num=num), state="complete")
            st.rerun()

    if st.button(LANG["clear_btn"]):
        try:
            st.cache_resource.clear()
            folder_to_clean = os.path.join(parent_dir, "data", "my_doc")
            if os.path.exists(folder_to_clean):
                for filename in os.listdir(folder_to_clean):
                    file_path = os.path.join(folder_to_clean, filename)
                    if os.path.isfile(file_path): os.unlink(file_path)
                    elif os.path.isdir(file_path): shutil.rmtree(file_path)

            # Sửa lỗi 'active_vectorstore' not defined bằng cách dùng session_state
            if st.session_state.active_vectorstore is not None:
                results = st.session_state.active_vectorstore.get(where={"subject": "My Documents"})
                if results and results.get('ids'):
                    st.session_state.active_vectorstore.delete(ids=results['ids'])
                    st.toast(f"Đã xóa {len(results['ids'])} dữ liệu cá nhân.")

            st.success("✅ 개인 문서 데이터가 초기화되었습니다!")
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi xóa dữ liệu: {e}")

# --- GIAO DIỆN CHAT CHÍNH ---
st.markdown(f"<div class='chat-header'><h1>{LANG['title']}</h1></div>", unsafe_allow_html=True)

chat_ready = active_vectorstore is not None 

if not chat_ready:
    st.info(f"💡 {LANG['welcome_msg']}")

def render_assistant_response(ans, cits, vids):
    t1, t2, t3 = st.tabs([LANG["tab_ans"], LANG["tab_src"], LANG["tab_vid"]])
    
    with t1: 
        st.markdown(ans)
    
    with t2:
        if cits:
            for c in cits: 
                st.caption(f"📌 **{c.get('filename')}** - {c.get('page')}페이지")
        else: 
            st.write(LANG["no_src"])
            
    with t3:
        if vids:
            st.subheader("🎥 추천 학습 영상")
            for title, link in vids:
                # Chia tỉ lệ [2, 1] để video chiếm 2/3 chiều rộng, giúp khung hình nhỏ lại
                col1, col2 = st.columns([1, 3]) 
                with col1:
                    st.video(link)
                    st.caption(f"**{title}**")
                st.divider()
        else: 
            st.warning("관련 추천 영상이 없습니다.")

# --- BẢO VỆ RENDER LOOP (TRÁNH LỆCH INDEX) ---
assistant_count = 0
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if msg["role"] == "assistant":
            if assistant_count < len(st.session_state.citation_history) and \
               assistant_count < len(st.session_state.video_history):
                
                render_assistant_response(
                    msg["content"], 
                    st.session_state.citation_history[assistant_count],
                    st.session_state.video_history[assistant_count]
                )
            else:
                st.markdown(msg["content"])
            assistant_count += 1
        else:
            st.markdown(msg["content"])

# --- XỬ LÝ NHẬP LIỆU ---
user_input = st.chat_input(LANG["input_placeholder"], disabled=not chat_ready)

if user_input:
    # 1. Lưu câu hỏi của người dùng
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    with st.chat_message("user"): 
        st.markdown(user_input)

    # 2. Xử lý phản hồi
    with st.chat_message("assistant"):
        with st.spinner(LANG["status_search"]):
            target_subject = selected_subject if source_mode == "Selected Subjects" else "My Documents"
            
            # Gọi AI lấy câu trả lời
            ans, low_conf, cits = answer_from_sources(
                user_input=user_input,
                selected_subject=target_subject,
                selected_chapter=selected_chapter.strip() if selected_chapter else "All",
                chat_history=st.session_state.chat_history,
                vectorstore=active_vectorstore,
                llm=get_llm(),
                reranker=get_reranker(),
                query_mode=source_mode,
                output_language="the same language as the user's question", 
                use_metadata_filter=True
            )
            
            # 3. LẤY VIDEO TỪ YOUTUBE
            current_vids = []
            try:
                t, l = get_yt_video_link(user_input)
                if t and l:
                    current_vids = [(t[i], l[i]) for i in range(min(3, len(t)))]
            except Exception as e:
                print(f"❌ Video Error: {e}")

        # 4. HIỂN THỊ RA MÀN HÌNH
        render_assistant_response(ans, cits, current_vids)
        
        # 5. LƯU VÀO LỊCH SỬ (QUAN TRỌNG: Lưu cùng lúc để đồng bộ index)
        st.session_state.chat_history.append({"role": "assistant", "content": ans})
        st.session_state.citation_history.append(cits)
        st.session_state.video_history.append(current_vids)
        
        # Rerun để UI cập nhật mượt mà
        st.rerun()
