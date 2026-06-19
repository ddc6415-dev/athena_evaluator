import streamlit as st
import docx
import io
import requests
import re
from bs4 import BeautifulSoup
import youtube_transcript_api

def write_report_to_word_bytes(report_text):
    doc = docx.Document()
    doc.add_heading('Hexaxial Evaluation Report', 0)
    doc.add_paragraph(report_text)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def main():
    st.title("ATHENA-1: EVALUATION NODE")
    input_method = st.radio("Select input source", ["Local File (.docx)", "Web URL"])
    extracted_text = ""
    is_ready = False

    if input_method == "Web URL":
        target_url = st.text_input("Enter target URL")
        if st.button("Run Evaluation"):
            try:
                if "youtube.com" in target_url:
                    video_id = re.search(r"v=([a-zA-Z0-9_-]+)", target_url).group(1)
                    extracted_text = " ".join([t['text'] for t in youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)])
                else:
                    response = requests.get(target_url, headers={'User-Agent': 'Mozilla/5.0'})
                    extracted_text = BeautifulSoup(response.text, 'html.parser').get_text()
                is_ready = True
            except Exception as e:
                st.error(f"Input Processing Failed: {e}")
    else:
        uploaded_file = st.file_uploader("Upload Target Document", type=["docx"])
        if st.button("Run Evaluation"):
            if uploaded_file:
                doc = docx.Document(uploaded_file)
                extracted_text = "\n".join([p.text for p in doc.paragraphs])
                is_ready = True

    if is_ready:
        st.success("Extraction complete.")
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
            payload = {"contents": [{"parts": [{"text": f"Evaluate this text: {extracted_text}"}]}]}
            
            response = requests.post(url, json=payload).json()
            
            if "candidates" in response:
                result = response["candidates"][0]["content"]["parts"][0]["text"]
                st.write(result)
                doc_buffer = write_report_to_word_bytes(result)
                st.download_button("Download Report", data=doc_buffer, file_name="Athena_Report.docx")
            else:
                st.error(f"API Error: {response}")
        except Exception as e:
            st.error(f"Evaluation Failed: {e}")

if __name__ == "__main__":
    main()
