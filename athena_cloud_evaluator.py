import streamlit as st
import docx
import io
import requests
import re
import time
from bs4 import BeautifulSoup
import google.generativeai as genai
import youtube_transcript_api

# ===============================================
# CORE SUBROUTINES
# ===============================================
def robust_network_request(url, headers, timeout_val=15, retries=3, wait_time=5):
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=timeout_val)
            res.raise_for_status()
            return res
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                time.sleep(wait_time)
            else:
                raise e

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
                    response = robust_network_request(target_url, headers={'User-Agent': 'Mozilla/5.0'})
                    soup = BeautifulSoup(response.text, 'html.parser')
                    extracted_text = soup.get_text()
                is_ready = True
            except Exception as e:
                st.error(f"Input Processing Failed: {e}")
    else:
        uploaded_file = st.file_uploader("Upload Target Document", type=["docx"])
        if st.button("Run Evaluation"):
            if uploaded_file:
                try:
                    doc = docx.Document(uploaded_file)
                    extracted_text = "\n".join([p.text for p in doc.paragraphs])
                    is_ready = True
                except Exception as e:
                    st.error(f"File Processing Failed: {e}")

    if is_ready:
        st.success("Extraction complete.")
        with st.spinner("Processing evaluation..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                model = genai.GenerativeModel('gemini-pro')
                
                evaluation_prompt = (
                    f"Follow the Hexaxial framework: Knowledge is information sufficiently accurate for repeated use. "
                    f"Task: Provide executive summary, HEXAXIAL METRIC DISTRIBUTION (Use: ████████), "
                    f"and assess the 6 axes: Repeatability, Temporal Stability, Linguistic Precision, "
                    f"Cultural Validation, Technological Resolution, Sovereign Incentives. "
                    f"Finally, append [ADVERTISING_INTRUSION_LOG].\n\n"
                    f"--- PAYLOAD ---\n{extracted_text}"
                )
                
                response = model.generate_content(evaluation_prompt)
                st.subheader("AI EVALUATION STREAM OUTPUT")
                st.write(response.text)
                
                doc_buffer = write_report_to_word_bytes(response.text)
                st.download_button("Download Report", data=doc_buffer, file_name="Athena_Report.docx")
            except Exception as e:
                st.error(f"Evaluation Failed: {e}")

if __name__ == "__main__":
    main()
