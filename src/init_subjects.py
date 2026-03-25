import os
import warnings
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

warnings.filterwarnings("ignore")

# --- CẤU HÌNH ĐƯỜNG DẪN TỰ ĐỘNG ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "vector_db" / "class_12_unified_vector_db")
SUBJECTS_DIR = str(BASE_DIR / "data" / "subjects")

def ingest_all_subjects():
    print(f"📍 Đang chạy tại: {BASE_DIR}")
    embeddings = HuggingFaceEmbeddings(
        model_name="paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'}
    )
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    
    if not os.path.exists(SUBJECTS_DIR):
        print(f"❌ LỖI: Không thấy thư mục {SUBJECTS_DIR}")
        return

    for subject_name in os.listdir(SUBJECTS_DIR):
        subject_path = os.path.join(SUBJECTS_DIR, subject_name)
        if os.path.isdir(subject_path):
            print(f"\n--- 📂 Môn: {subject_name.upper()} ---")
            for pdf_file in os.listdir(subject_path):
                if pdf_file.endswith(".pdf"):
                    print(f"   + Đang nạp: {pdf_file}...")
                    try:
                        loader = PyPDFLoader(os.path.join(subject_path, pdf_file))
                        docs = loader.load()
                        for d in docs:
                            d.metadata["subject"] = subject_name
                        splits = text_splitter.split_documents(docs)
                        # Nạp cuốn chiếu để tránh treo máy
                        Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=DB_PATH)
                        print(f"   => ✅ Xong {len(splits)} đoạn.")
                    except Exception as e:
                        print(f"   ❌ Lỗi file {pdf_file}: {e}")
    print(f"\n🚀 Hoàn tất nạp môn học vào: {DB_PATH}")

if __name__ == "__main__":
    ingest_all_subjects()