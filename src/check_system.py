import os
from dotenv import load_dotenv

def check_env():
    load_dotenv()
    print("--- KIỂM TRA BIẾN MÔI TRƯỜNG (.env) ---")
    keys = ["GROQ_API_KEY"]
    for key in keys:
        value = os.getenv(key)
        if value:
            print(f"✅ {key}: Đã tìm thấy (Bắt đầu bằng: {value[:6]}...)")
        else:
            print(f"❌ {key}: CHƯA CÓ! (Bạn cần thêm vào file .env)")

def check_files():
    print("\n--- KIỂM TRA FILE DỮ LIỆU ---")
    files = {
        "Vector DB NCERT": "vector_db/class_12_unified_vector_db",
        "Font Tiếng Hindi": "assets/fonts/NotoSansDevanagari-Regular.ttf",
        "File cấu hình dự án": "app_config.py",
        "QA Engine": "qa_engine.py"
    }
    for name, path in files.items():
        if os.path.exists(path):
            print(f"✅ {name}: Đã sẵn sàng.")
        else:
            print(f"❌ {name}: Thiếu! (Đường dẫn: {path})")

def check_system_tools():
    print("\n--- KIỂM TRA CÔNG CỤ HỆ THỐNG (Cho PDF) ---")
    # Kiểm tra poppler cho Windows
    import shutil
    poppler = shutil.which("pdftoppm")
    if poppler:
        print(f"✅ Poppler: Đã cài đặt.")
    else:
        print(f"⚠️  Poppler: Có thể thiếu (Cần thiết để unstructured đọc PDF).")

if __name__ == "__main__":
    check_env()
    check_files()
    check_system_tools()