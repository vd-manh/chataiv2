import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# --- CẤU HÌNH ĐƯỜNG DẪN TỰ ĐỘNG ---
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = str(BASE_DIR / "vector_db" / "class_12_unified_vector_db")
PDF_PATH = str(BASE_DIR / "data" / "my_doc")

def run_ingest():
    print(f"📍 Đang xử lý tài liệu cá nhân tại: {BASE_DIR}")
    embeddings = HuggingFaceEmbeddings(model_name="paraphrase-multilingual-MiniLM-L12-v2")
    
    if not os.path.exists(PDF_PATH):
        os.makedirs(PDF_PATH)
        print(f"⚠️ Thư mục trống, hãy bỏ file PDF vào: {PDF_PATH}")
        return 0

    loader = PyPDFDirectoryLoader(PDF_PATH)
    documents = loader.load()
    
    if not documents:
        print("❌ LỖI: Không tìm thấy file PDF nào trong my_doc!")
        return 0

    for doc in documents:
        doc.metadata["subject"] = "My Documents"
        doc.metadata["chapter"] = "My Documents"

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
    splits = text_splitter.split_documents(documents)
    
    print(f"--- Đang nạp {len(splits)} đoạn tài liệu cá nhân ---")
    try:
        Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=DB_PATH)
        print("✅ HOÀN THÀNH CẬP NHẬT TÀI LIỆU CÁ NHÂN!")
        return len(splits)
    except Exception as e:
        print(f"❌ Lỗi ghi Database: {e}")
        return 0

if __name__ == "__main__":
    run_ingest()