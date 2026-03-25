import os
from pathlib import Path
from dotenv import load_dotenv

def load_project_env(working_dir):
    working_path = Path(working_dir).resolve()
    parent_path = working_path.parent
    load_dotenv(parent_path / ".env")
    return str(parent_path)

def resolve_device():
    # Streamlit Cloud dùng CPU là ổn định nhất
    return "cpu"

def get_unified_vector_db_path(parent_dir):
    # Đảm bảo đường dẫn này khớp với cấu trúc thư mục data trên GitHub của Mạnh
    return os.path.join(parent_dir, "data", "unified_vector_db")
