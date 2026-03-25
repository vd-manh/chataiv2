from youtube_search import YoutubeSearch
import re

def get_yt_video_link(query):
    # 1. Làm sạch query
    clean_query = re.sub(r'[^\w\s]', '', query).strip()
    print(f"🔍 Đang tìm video cho: '{clean_query}'")
    
    if not clean_query:
        return [], []
    
    try:
        # 2. Tìm kiếm video (Sử dụng thư viện youtube-search)
        results = YoutubeSearch(clean_query, max_results=3).to_dict()
        
        if not results:
            # Thử lại với từ khóa ngắn hơn
            short_query = " ".join(clean_query.split()[:3])
            results = YoutubeSearch(short_query, max_results=3).to_dict()

        if not results:
            print(f"❌ YouTube không trả về kết quả.")
            return [], []
        
        video_titles = [video['title'] for video in results]
        video_links = [f"https://www.youtube.com/watch?v={video['id']}" for video in results]
        
        print(f"✅ Đã tìm thấy: {video_titles[0]}")
        return video_titles, video_links
    
    except Exception as e:
        print(f"❌ Lỗi tìm YouTube: {e}")
        return [], []