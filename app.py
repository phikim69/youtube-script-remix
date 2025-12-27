import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import yt_dlp
import os
import time
import re

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="YouTube AI Script Writer (Pro)", page_icon="🎧")

# --- CSS ---
st.markdown("""
<style>
    .stTextArea textarea {font-size: 16px;}
</style>
""", unsafe_allow_html=True)

# --- CÁC HÀM XỬ LÝ ---

def extract_video_id(url):
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def get_transcript(video_id):
    """Cố gắng lấy phụ đề text"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['vi', 'en'])
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
    except:
        return None

def download_audio(youtube_url):
    """Tải audio về máy chủ tạm thời"""
    output_filename = "audio_temp.mp3"
    
    # Xóa file cũ nếu tồn tại
    if os.path.exists(output_filename):
        os.remove(output_filename)
        
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '128',
        }],
        'outtmpl': 'audio_temp',
        'quiet': True
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        return output_filename
    except Exception as e:
        st.error(f"Lỗi tải audio: {str(e)}")
        return None

def process_content(api_key, content_input, input_type="text", mode="summary", style="Tự nhiên"):
    """
    Xử lý nội dung với Gemini.
    input_type: "text" hoặc "audio"
    """
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash') # Flash xử lý audio rất tốt và free

    # Tạo prompt chung
    if mode == "summary":
        task_prompt = "Tóm tắt nội dung chính bằng tiếng Việt dưới dạng gạch đầu dòng."
    else:
        task_prompt = f"""
        Viết lại kịch bản video ngắn (Shorts/TikTok) theo phong cách: {style}.
        Cấu trúc:
        1. Tiêu đề hấp dẫn
        2. Hook (3 giây đầu)
        3. Nội dung chính
        4. CTA (Kêu gọi hành động)
        Ngôn ngữ: Tiếng Việt.
        """

    try:
        if input_type == "text":
            # Xử lý văn bản thuần túy
            prompt = f"{task_prompt}\n\nNội dung gốc:\n{content_input}"
            response = model.generate_content(prompt)
            return response.text

        elif input_type == "audio":
            # Xử lý file âm thanh
            audio_file = genai.upload_file(path=content_input)
            
            # Đợi file được xử lý xong trên server Google
            while audio_file.state.name == "PROCESSING":
                time.sleep(2)
                audio_file = genai.get_file(audio_file.name)

            prompt = f"{task_prompt}\n\nHãy nghe file âm thanh đính kèm và thực hiện yêu cầu."
            response = model.generate_content([prompt, audio_file])
            
            # Xóa file trên server Google sau khi dùng xong để dọn dẹp (tùy chọn)
            # audio_file.delete() 
            return response.text

    except Exception as e:
        return f"Lỗi Gemini: {str(e)}"

# --- GIAO DIỆN CHÍNH ---

st.title("🎧 YouTube Script Remix (Audio Support)")
st.caption("Hỗ trợ cả video KHÔNG có phụ đề bằng cách nghe Audio.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Cài đặt")
    # Kiểm tra Key trong Secrets (cho deploy) hoặc nhập tay
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ Đã nạp API Key hệ thống")
    else:
        api_key = st.text_input("Nhập Google Gemini API Key", type="password")
    
    st.divider()
    script_style = st.selectbox(
        "Chọn giọng văn:",
        ("Hài hước", "Nghiêm túc", "Sâu sắc", "Kịch tính", "Review sản phẩm")
    )

youtube_url = st.text_input("Dán link YouTube:", placeholder="https://www.youtube.com/watch?v=...")

if youtube_url and api_key:
    video_id = extract_video_id(youtube_url)
    
    if video_id:
        st.image(f"https://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)
        
        if st.button("✨ Xử lý Video"):
            status_text = st.empty()
            
            # CHIẾN LƯỢC 1: THỬ LẤY TRANSCRIPT (TEXT) - NHANH
            status_text.info("🔍 Đang kiểm tra phụ đề...")
            transcript_text = get_transcript(video_id)
            
            content_source = None
            input_type = "text"

            if transcript_text:
                status_text.success("✅ Đã tìm thấy phụ đề text!")
                content_source = transcript_text
            
            # CHIẾN LƯỢC 2: KHÔNG CÓ TEXT -> TẢI AUDIO - CHẬM HƠN NHƯNG MẠNH HƠN
            else:
                status_text.warning("⚠️ Không có phụ đề. Đang chuyển sang chế độ tải Audio (sẽ mất khoảng 10-30s)...")
                audio_path = download_audio(youtube_url)
                
                if audio_path:
                    status_text.success("✅ Đã tải xong Audio! Đang gửi cho Gemini nghe...")
                    content_source = audio_path
                    input_type = "audio"
                else:
                    st.error("Không thể tải video này.")
            
            # GỬI CHO AI XỬ LÝ
            if content_source:
                # 1. Tóm tắt
                with st.spinner("Gemini đang phân tích..."):
                    summary = process_content(api_key, content_source, input_type, mode="summary")
                
                st.markdown("### 📝 Tóm tắt")
                st.info(summary)
                
                # 2. Viết kịch bản
                with st.spinner("Đang viết lại kịch bản..."):
                    script = process_content(api_key, content_source, input_type, mode="rewrite", style=script_style)
                
                st.markdown("### 🎬 Kịch bản mới")
                st.markdown(script)
                
                # Dọn dẹp file tạm nếu là audio
                if input_type == "audio" and os.path.exists("audio_temp.mp3"):
                    os.remove("audio_temp.mp3")
                    
    else:
        st.error("Link không hợp lệ.")
elif youtube_url and not api_key:
    st.warning("Vui lòng nhập API Key.")
