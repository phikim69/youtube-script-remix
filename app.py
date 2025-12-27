import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import re

# --- CẤU HÌNH TRANG ---
st.set_page_config(page_title="YouTube AI Script Writer (Free)", page_icon="💎")

# --- CSS ---
st.markdown("""
<style>
    .stTextArea textarea {font-size: 16px;}
    .success-box {padding: 1rem; background-color: #d4edda; border-radius: 5px; color: #155724;}
</style>
""", unsafe_allow_html=True)

# --- CÁC HÀM XỬ LÝ ---

def extract_video_id(url):
    """Lấy ID video từ link YouTube"""
    regex = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    return None

def get_transcript(video_id):
    """Lấy phụ đề video (Tiếng Việt hoặc Anh)"""
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['vi', 'en'])
        full_text = " ".join([item['text'] for item in transcript_list])
        return full_text
    except Exception as e:
        return None

def process_with_gemini(api_key, text, mode="summary", style="Tự nhiên"):
    """Gửi yêu cầu đến Google Gemini"""
    try:
        # Cấu hình API
        genai.configure(api_key=api_key)
        
        # Sử dụng model Gemini 1.5 Flash (Nhanh và Free)
        model = genai.GenerativeModel('gemini-2.5-flash')

        if mode == "summary":
            prompt = f"""
            Hãy đóng vai một trợ lý nội dung giỏi. Nhiệm vụ của bạn là tóm tắt nội dung văn bản sau đây.
            Yêu cầu:
            - Tóm tắt bằng tiếng Việt.
            - Trình bày dưới dạng danh sách gạch đầu dòng (bullet points).
            - Tập trung vào các ý chính quan trọng nhất.
            
            Văn bản gốc:
            {text}
            """
        else: # mode == rewrite
            prompt = f"""
            Hãy đóng vai một biên kịch video chuyên nghiệp trên mạng xã hội.
            Nhiệm vụ: Viết lại một kịch bản video ngắn dựa trên nội dung được cung cấp.
            
            Phong cách viết: {style}
            
            Cấu trúc kịch bản bắt buộc:
            1. TIÊU ĐỀ (Giật tít, thu hút)
            2. HOOK (Câu mở đầu gây tò mò trong 3 giây đầu)
            3. NỘI DUNG CHÍNH (Cô đọng, chia thành các phân cảnh nhỏ)
            4. CTA (Kêu gọi hành động: like, share, comment)
            
            Nội dung gốc:
            {text}
            """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Lỗi Gemini: {str(e)}"

# --- GIAO DIỆN CHÍNH (UI) ---

st.title("💎 YouTube Script Remix (Gemini Free)")
st.write("Tự động tóm tắt và viết lại kịch bản video sử dụng Google Gemini.")

# Sidebar
with st.sidebar:
    st.header("⚙️ Cài đặt")
    api_key = st.text_input("Nhập Google Gemini API Key", type="password")
    st.caption("Lấy key miễn phí tại [Google AI Studio](https://aistudio.google.com/app/apikey)")
    
    st.divider()
    
    st.subheader("Phong cách viết lại")
    script_style = st.selectbox(
        "Chọn giọng văn kịch bản:",
        ("Hài hước & Vui nhộn", "Nghiêm túc & Chuyên gia", "Sâu sắc & Triết lý", "Kịch tính & Giật gân", "Tiên hiệp & Cổ trang")
    )

# Main Input
youtube_url = st.text_input("Dán link YouTube vào đây:", placeholder="https://www.youtube.com/watch?v=...")

if youtube_url and api_key:
    video_id = extract_video_id(youtube_url)
    
    if video_id:
        st.image(f"https://img.youtube.com/vi/{video_id}/0.jpg", use_column_width=True)
        
        if st.button("✨ Xử lý Video ngay"):
            
            # BƯỚC 1: LẤY TRANSCRIPT
            with st.spinner("Đang tải phụ đề video..."):
                transcript_text = get_transcript(video_id)
            
            if transcript_text:
                # Hiển thị Transcript gốc (ẩn đi cho gọn)
                with st.expander("Xem nội dung gốc (Raw Text)"):
                    st.text_area("", transcript_text, height=150)

                # BƯỚC 2: TÓM TẮT
                with st.spinner("Gemini đang đọc và tóm tắt..."):
                    summary = process_with_gemini(api_key, transcript_text, mode="summary")
                
                st.markdown("### 📝 Tóm tắt nội dung")
                st.info(summary)
                
                # BƯỚC 3: VIẾT LẠI KỊCH BẢN
                with st.spinner(f"Đang viết kịch bản phong cách: {script_style}..."):
                    script = process_with_gemini(api_key, transcript_text, mode="rewrite", style=script_style)
                
                st.markdown("### 🎬 Kịch bản mới")
                st.markdown(script) # Gemini trả về Markdown nên dùng st.markdown hiển thị rất đẹp
                
            else:
                st.error("⚠️ Video này không có phụ đề (CC). Ứng dụng chưa thể xử lý video chỉ có âm thanh mà không có text.")
    else:
        st.error("Link không hợp lệ.")
elif youtube_url and not api_key:
    st.warning("👈 Vui lòng nhập API Key bên tay trái để bắt đầu.")