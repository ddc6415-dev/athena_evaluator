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

# ==========================================
# PHASE 1: GOOGLE IAM AUTHENTICATION LAYER
# ==========================================
if not st.user.is_logged_in:
    st.title("ATHENA-1: SECURE ACCESS NODE")
    st.warning("UNAUTHORIZED ACCESS. Please authenticate via Google Identity Access Management.")
    st.button("Log in with Google", on_click=st.login)
    st.stop()

# ==========================================
# CORE SUBROUTINES
# ==========================================
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

def extract_text_payload(source_type, source_data):
    """Routes to the appropriate ingestion subroutine."""
    metadata = {"title": "Unknown Title", "description": "No profile description available."}
    
    if source_type == "youtube":
        st.info("Invoking Transcript Ingestion Engine...")
        video_id = None
        if "v=" in source_data:
            video_id = source_data.split("v=")[1].split("&")[0]
        elif "youtu.be/" in source_data:
            video_id = source_data.split("youtu.be/")[1].split("?")[0]
            
        if not video_id:
            raise ValueError("Could not extract 11-character Video ID from the provided YouTube URL.")
            
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            meta_res = robust_network_request(f"https://www.youtube.com/watch?v={video_id}", headers=headers, timeout_val=10)
            html_content = meta_res.text
            json_match = re.search(r"ytInitialPlayerResponse\s*=\s*({.+?});", html_content)
            if json_match:
                player_data = json.loads(json_match.group(1))
                video_details = player_data.get("videoDetails", {})
                if video_details:
                    metadata["title"] = video_details.get("title", "Unknown Title")
                    metadata["description"] = f"Published by: {video_details.get('author', 'Unknown Creator')}."
        except Exception as e:
            st.warning(f"Metadata extraction warning: {e}")
            
        try:
            transcript_list = youtube_transcript_api.YouTubeTranscriptApi.get_transcript(video_id)
            text_segments = [seg['text'] for seg in transcript_list]
            return " ".join(text_segments), f"YT_{video_id}", metadata
        except Exception as e:
            raise RuntimeError(f"Transcript extraction failed: {e}")

    elif source_type == "web":
        st.info("Invoking HTML Web Scraping Engine...")
        headers = {"User-Agent": "Mozilla/5.0"}
        response = robust_network_request(source_data, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        title_tag = soup.find("title")
        if title_tag:
            metadata["title"] = title_tag.text.strip()
            
        for element in soup(["script", "style", "nav", "header", "footer"]):
            element.decompose()
            
        lines = (paragraph.get_text() for paragraph in soup.find_all("p"))
        text_payload = "\n".join(item.strip() for item in lines if item.strip())
        
        domain = source_data.split("//")[-1].split("/")[0].replace("www.", "")
        clean_domain = re.sub(r'[^a-zA-Z0-9]', '_', domain)
        metadata["description"] = f"Web documentation scraped from domain: {domain}."
        return text_payload, f"WEB_{clean_domain}", metadata

    elif source_type == "file":
        st.info("Invoking OpenXML Word Parsing Engine...")
        doc = docx.Document(source_data) # source_data is a file-like object from Streamlit
        text_segments = [p.text for p in doc.paragraphs if p.text.strip()]
        text_payload = "\n".join(text_segments)
        
        clean_base = re.sub(r'[^a-zA-Z0-9]', '_', source_data.name)
        metadata["title"] = source_data.name
        metadata["description"] = "OFFLINE INGESTION PROTOCOL: Processing localized text payload."
        return text_payload, f"DOC_{clean_base}", metadata

def write_report_to_word_bytes(report_text, metadata, source_text=""):
    """
    Parses evaluation text into a Word doc and returns it as a BytesIO object
    suitable for cloud downloading/emailing.
    """
    doc = docx.Document()
    title = doc.add_paragraph()
    title_run = title.add_run("ATHENA-1 HEXAXIAL EVALUATION REPORT")
    title_run.bold = True
    title_run.font.name = 'Arial'
    title_run.font.size = docx.shared.Pt(18)
    
    p_meta = doc.add_paragraph()
    p_meta.paragraph_format.space_before = docx.shared.Pt(12)
    p_meta.paragraph_format.space_after = docx.shared.Pt(12)
    
    if source_text:
        run_src = p_meta.add_run(f"LOCAL PAYLOAD ANALYSIS TARGET: {metadata['title']}\n")
        run_src.bold = True
        run_src.font.name = 'Arial'
        run_src.font.size = docx.shared.Pt(11)
        
        p_hdr = doc.add_paragraph()
        run_hdr = p_hdr.add_run("--- ORIGINAL LOCAL DOCUMENT CONTENTS ---")
        run_hdr.font.name = 'Arial'
        run_hdr.font.size = docx.shared.Pt(11)
        run_hdr.bold = True
        
        p_source_text = doc.add_paragraph()
        p_source_text.paragraph_format.space_after = docx.shared.Pt(12)
        run_text = p_source_text.add_run(source_text[:2000] + "\n...[TRUNCATED FOR DISPLAY]") # Prevent massive text dumps
        run_text.font.name = 'Arial'
        run_text.font.size = docx.shared.Pt(10)
    else:
        run_src = p_meta.add_run(f"This analysis is based upon the information presented in: {metadata['title']}\n")
        run_src.bold = True
        run_src.font.name = 'Arial'
        run_src.font.size = docx.shared.Pt(11)
        
    run_desc = p_meta.add_run(f"Origin Configuration: {metadata['description']}\n")
    run_desc.italic = True
    run_desc.font.name = 'Arial'
    run_desc.font.size = docx.shared.Pt(11)
    
    doc.add_paragraph("-" * 60)
    
    metric_axes = [
        "Repeatability:", "Temporal Stability:", "Linguistic Precision:",
        "Cultural Validation:", "Technological Resolution:", "Sovereign Incentives:"
    ]
    
    for line in report_text.split("\n"):
        cleaned_line = line.strip()
        if not cleaned_line:
            continue
            
        is_axis_line = any(cleaned_line.startswith(axis) for axis in metric_axes)
        if is_axis_line:
            matched_axis = next(axis for axis in metric_axes if cleaned_line.startswith(axis))
            bar_content = cleaned_line.replace(matched_axis, "").strip()
            
            table = doc.add_table(rows=1, cols=2)
            table.columns[0].width = docx.shared.Inches(2.5)
            table.columns[1].width = docx.shared.Inches(4.5)
            
            p_lbl = table.cell(0, 0).paragraphs[0]
            run_lbl = p_lbl.add_run(matched_axis)
            run_lbl.font.name = 'Arial'
            run_lbl.font.size = docx.shared.Pt(11)
            
            p_val = table.cell(0, 1).paragraphs[0]
            run_val = p_val.add_run(bar_content)
            run_val.font.name = 'Arial'
            run_val.font.size = docx.shared.Pt(11)
            continue
            
        if cleaned_line.startswith("[") or cleaned_line.startswith("**"):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = docx.shared.Pt(14)
            run = p.add_run(cleaned_line.replace("**", ""))
            run.bold = True
            run.font.name = 'Arial'
            run.font.size = docx.shared.Pt(14)
        else:
            p = doc.add_paragraph()
            run = p.add_run(cleaned_line.replace("**", ""))
            run.font.name = 'Arial'
            run.font.size = docx.shared.Pt(11)
            
    # Save to a BytesIO object for cloud memory stream
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# ==========================================
# MAIN APPLICATION UI
# ==========================================
def main():
    st.sidebar.write(f"**Operator:** {st.user.name}")
    st.sidebar.button("Log out", on_click=st.logout)
    
    st.title("ATHENA-1 EVALUATOR ENGINE")
    st.subheader("ACTIVE INDEPENDENCE CLOUD NODE")
    st.divider()

    # Load Metrics Configuration securely from repo
    try:
        with open("metrics_config.txt", "r") as config_file:
            metrics_rules = config_file.read()
    except Exception:
        st.error("CRITICAL FAILURE: metrics_config.txt not found in cloud repository.")
        st.stop()

    # Input Layer
    input_method = st.radio("Select Target Source:", ["URL (YouTube/Web)", "Local File (.docx)"])
    
    extracted_text, source_clean_id, metadata = None, None, None
    is_ready = False

    if input_method == "URL (YouTube/Web)":
        target_url = st.text_input("Paste target URL:")
        if st.button("Run Evaluation"):
            if target_url:
                try:
                    if "youtube.com" in target_url or "youtu.be" in target_url:
                        extracted_text, source_clean_id, metadata = extract_text_payload("youtube", target_url)
                    else:
                        extracted_text, source_clean_id, metadata = extract_text_payload("web", target_url)
                    is_ready = True
                except Exception as e:
                    st.error(f"Input Processing Failed: {e}")
            else:
                st.warning("Please provide a valid URL.")
                
    else:
        uploaded_file = st.file_uploader("Upload Target Document", type=["docx"])
        if st.button("Run Evaluation"):
            if uploaded_file:
                try:
                    extracted_text, source_clean_id, metadata = extract_text_payload("file", uploaded_file)
                    is_ready = True
                except Exception as e:
                    st.error(f"File Processing Failed: {e}")
            else:
                st.warning("Please upload a .docx file.")

    # Processing Layer
    if is_ready:
        st.success(f"Extracted {len(extracted_text)} characters from target feed.")
        
        with st.spinner("Processing Hexaxial Metric evaluation..."):
            try:
                # IMPORTANT: API Keys should be migrated to st.secrets in production
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
                    f"Following the category, you MUST include a graphical '-- HEXAXIAL METRIC DISTRIBUTION --' section using proportional Unicode block characters "
                    f"([██████████] for High, [████████░░] for partial, etc.) to visually represent the score for all six axes.\n\n"
                    f"ALIGNMENT CONSTRAINT:\n"
                    f"Print each metric axis score directly on its own separate line using the following exact labels. Do not add leading spaces or modify the spelling:\n"
                    f"Repeatability: [██████████]\n"
                    f"Temporal Stability: [████████░░]\n"
                    f"Linguistic Precision: [██████████]\n"
                    f"Cultural Validation: [██████░░░░]\n"
                    f"Technological Resolution: [██████████]\n"
                    f"Sovereign Incentives: [██████░░░░]\n\n"
                    f"If an individual axis cannot be evaluated due to missing data context, output 'No Data Available' immediately following the colon instead of a bar graph.\n\n"
                    f"Finally, provide a strict 2-3 sentence justification for this determination based on the metrics.\n\n"
                    f"Task 2: Evaluate the target text payload strictly against the provided Hexaxial Evaluation Metrics framework definitions "
                    f"and environmental dependencies. Provide a clear, structured report assessing each of the six axes:\n"
                    f"  1. Repeatability (Does the information consistently produce successful outcomes?)\n"
                    f"  2. Temporal Stability (Does it remain reliable over time or decay rapidly?)\n"
                    f"  3. Linguistic Precision (Is the language precise enough for the specific domain task?)\n"
                    f"  4. Cultural Validation (Is it accepted/validated by institutional trust networks?)\n"
                    f"  5. Technological Resolution (Does it survive the best available observational tools?)\n"
                    f"  6. Sovereign Incentives (Who benefits? How do power structures or survival incentives distort the reporting?)\n\n"
                    f"Task 3: Define the baseline target environment, bounding domains, and chronological parameters before calculating reliability. "
                    f"Assign the analyzed text payload to one of the four absolute operational categories defined by the framework:\n"
                    f"  - [LEVEL: FUNCTIONAL CERTAINTY]: High reliability across all six dimensions (practical facts/managed reliability).\n"
                    f"  - [LEVEL: CONJECTURE]: The best available model given fluid or incomplete information (volatile/open to revision).\n"
                    f"  - [LEVEL: HYPOTHESIS / SPECULATIVE INFORMATION]: Logical internal coherence but low functional certainty on Repeatability or Technological Resolution.\n"
                    f"  - [LEVEL: INSUFFICIENT INFORMATION]: Meaningful evaluation is operationally impossible due to missing data.\n\n"
                    f"Task 4 (Advertising Screening Rule): Scan the text payload for any promotional messages, "
                    f"sponsorships, advertisements, or statements where someone is clearly trying to sell a product "
                    f"or service. You must completely ignore and discount this advertising noise when computing metric scores.\n\n"
                    f"Task 5 (Reporting Auditing Rule): At the absolute end of your report, append a mandatory section titled "
                    f"'[ADVERTISING_INTRUSION_LOG]'. If advertisements or sponsorships were detected, state exactly what was "
                    f"found and explicitly confirm that they were disregarded during scoring. If no promotional content was "
                    f"found, state 'No commercial advertisements detected within the target stream.'\n\n"
                    f"--- METRICS FRAMEWORK CRITERIA ---\n{metrics_rules}\n\n"
                    f"--- TEXT PAYLOAD TO EVALUATE ---\n{extracted_text}"
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=evaluation_prompt
                )
                
                st.write("---")
                st.subheader("AI EVALUATION STREAM OUTPUT")
                st.write(response.text)
                
                # Render to memory and provide secure download
                source_text_inject = extracted_text if input_method == "Local File (.docx)" else ""
                doc_buffer = write_report_to_word_bytes(response.text, metadata, source_text_inject)
                
                st.write("---")
                st.download_button(
                    label="Download Hexaxial Evaluation Report (.docx)",
                    data=doc_buffer,
                    file_name=f"Athena_Report_{source_clean_id}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )
                
            except Exception as e:
                st.error(f"Evaluation Subroutine Failed: {e}")

if __name__ == "__main__":
    main()
