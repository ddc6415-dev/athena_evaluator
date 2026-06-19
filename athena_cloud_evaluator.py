import streamlit as st
import docx
import io
import requests
import re
import json
import time
from bs4 import BeautifulSoup
from google import genai
import youtube_transcript_api

# ===============================================
# PHASE 1: GOOGLE IAM AUTHENTICATION LAYER
# ===============================================
if not st.user.is_logged_in:
    st.title("ATHENA-1: SECURE ACCESS NODE")
    st.warning("UNAUTHORIZED ACCESS. Please authenticate via Google Identity Access Management.")
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# ===============================================
# CORE SUBROUTINES
# ===============================================
def robust_network_request(url, headers, timeout_val=15, retries=3, wait_time=5):
    """Executes a network request with a three-try retry loop."""
    for attempt in range(1, retries + 1):
        try:
            res = requests.get(url, headers=headers, timeout=timeout_val)
            res.raise_for_status()
            return res
        except requests.exceptions.RequestException as e:
            if attempt < retries:
                st.warning(f"NETWORK DELAY: Connection attempt {attempt}/{retries} failed. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                st.error(f"NETWORK FAILURE: Unable to establish connection after {retries} attempts.")
                raise e

def write_report_to_word_bytes(report_text, metadata, source_text):
    """Generates a .docx byte stream from evaluation report."""
    doc = docx.Document()
    doc.add_heading('Hexaxial Evaluation Report', 0)
    doc.add_paragraph(report_text)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def main():
    st.title("ATHENA-1: SECURE ACCESS NODE")
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
            else:
                st.warning("Please upload a .docx file.")

    if is_ready:
        st.success(f"Extracted {len(extracted_text)} characters from target feed.")
        with st.spinner("Processing Hexaxial Metric evaluation..."):
            try:
                client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                evaluation_prompt = (
                    f"You are the Author node of the Athena-1 system.\n\n"
                    f"Your analytical methodology strictly aligns with the authoritative framework defined in "
                    f"FILE ID: EDC_202600_SPK_INT01.01_CUR_Human Knowledge as Functional Certainty_V14_SHORT.\n\n"
                    f"CRITICAL CONCEPTUAL REJECTION RULE (The JTB Critique):\n"
                    f"You must completely reject the traditional, static 'Justified True Belief' (JTB) binary definition of knowledge "
                    f"as a historical artifact built for an era of top-down monopolies. Modern real-world environments do not operate "
                    f"on perfect, metaphysical certainties. Do not look for binary absolute truth. Instead, measure information "
                    f"strictly across a pragmatic, fluid spectrum of reliability, defining the transition from information to knowledge "
                    f"strictly through its operational execution: 'Knowledge is human information sufficiently accurate for repeated use.'\n\n"
                    f"Task 1 (Executive Summary): At the very beginning of your response, provide an executive summary of your findings. "
                    f"You must explicitly state the final Operational Category (e.g., [LEVEL: FUNCTIONAL CERTAINTY]). "
                    f"Following the category, you MUST include a graphical '-- HEXAXIAL METRIC DISTRIBUTION --' section using proportional Unicode blocks "
                    f"([████████] for High, [████░░░░] for partial, etc.) to visually represent the score for all six axes.\n\n"
                    f"ALIGNMENT CONSTRAINT:\n"
                    f"Print each metric axis score directly on its own separate line using the following exact labels. Do not add leading spaces or markdown:\n"
                    f"Repeatability: [████████]\n"
                    f"Temporal Stability: [████████]\n"
                    f"Linguistic Precision: [████████]\n"
                    f"Cultural Validation: [████████]\n"
                    f"Technological Resolution: [████████]\n"
                    f"Sovereign Incentives: [████████]\n\n"
                    f"If an individual axis cannot be evaluated due to missing data context, output 'No Data Available' immediately following the colon.\n"
                    f"Finally, provide a strict 2-3 sentence justification for this determination based on the metrics.\n\n"
                    f"Task 2: Evaluate the target text payload strictly against the provided Hexaxial Evaluation Metrics framework definitions "
                    f"and environmental dependencies. Provide a clear, structured report assessing each of the six axes:\n"
                    f"1. Repeatability (Does the information consistently produce successful outcomes?)\n"
                    f"2. Temporal Stability (Does it remain reliable over time or decay rapidly?)\n"
                    f"3. Linguistic Precision (Is the language precise enough for the specific domain?)\n"
                    f"4. Cultural Validation (Is it accepted/validated by institutional trust networks?)\n"
                    f"5. Technological Resolution (Does it survive the best available observational tools?)\n"
                    f"6. Sovereign Incentives (Does it provide clear value to the end-user?)\n\n"
                    f"Task 3 (Operational Categorization): Assign the analyzed text payload to one of the four absolute operational categories defined by the framework:\n"
                    f"- [LEVEL: FUNCTIONAL CERTAINTY]: High reliability across all six dimensions.\n"
                    f"- [LEVEL: CONJECTURE]: The best available model given fluid or incomplete information.\n"
                    f"- [LEVEL: HYPOTHESIS / SPECULATIVE INFORMATION]: Logical internal coherence but low functional certainty.\n"
                    f"- [LEVEL: INSUFFICIENT INFORMATION]: Meaningful evaluation is operationally impossible.\n\n"
                    f"Task 4 (Advertising Screening Rule): Scan the text payload for any promotional messages, "
                    f"sponsorships, advertisements, or statements where someone is clearly trying to sell a product "
                    f"or service. You must completely ignore and discount this advertising noise when computing metric scores.\n"
                    f"Task 5 (Reporting Auditing Rule): At the absolute end of your report, append a mandatory section titled "
                    f"'[ADVERTISING_INTRUSION_LOG]'. If advertisements were detected, state exactly what was "
                    f"found and explicitly confirm that they were disregarded during scoring. If no promotional content was "
                    f"found, state 'No commercial advertisements detected within the target stream.'\n\n"
                    f"--- METRICS FRAMEWORK CRITERIA ---\n{extracted_text}"
                )
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=evaluation_prompt
                )
                st.write("---")
                st.subheader("AI EVALUATION STREAM OUTPUT")
                st.write(response.text)
                
                doc_buffer = write_report_to_word_bytes(response.text, {}, extracted_text)
                st.download_button(
                    label="Download Hexaxial Evaluation Report (.docx)",
                    data=doc_buffer,
                    file_name="Athena_Evaluation_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
            except Exception as e:
                st.error(f"Evaluation Subroutine Failed: {e}")

if __name__ == "__main__":
    main()
