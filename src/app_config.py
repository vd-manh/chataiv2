import os
from pathlib import Path
from dotenv import load_dotenv

def load_project_env(working_dir):
    working_path = Path(working_dir).resolve()
    parent_path = working_path.parent
    # Tải file .env nếu có (chủ yếu dùng khi chạy local)
    load_dotenv(parent_path / ".env")
    return str(parent_path)

def resolve_device():
    # Streamlit Cloud không có GPU miễn phí, dùng CPU là an toàn nhất
    return "cpu"

def get_unified_vector_db_path(parent_dir):
    # Đường dẫn đến thư mục chứa dữ liệu não bộ AI
    return os.path.join(parent_dir, "data", "unified_vector_db")
