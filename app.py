import streamlit as st
import athena_cloud_evaluator

st.set_page_config(page_title="Athena-1 Evaluator", layout="wide")

st.title("Athena-1 Knowledge Evaluator")
st.markdown("### Manager: Edward David Callender Jr.")

st.sidebar.header("System Status")
st.sidebar.write("Architecture: Streamlit Cloud Deployment")
st.sidebar.write("Metric Alignment: Hexaxial Vector Space")

st.markdown("### Input Substrate")
input_mode = st.radio("Select Target Format:", ["Direct Text", "URL Extractor", "Document (.docx) Upload"])

target_text = ""

if input_mode == "Direct Text":
    target_text = st.text_area("Paste content for evaluation here:", height=300)
elif input_mode == "URL Extractor":
    target_text = st.text_input("Enter target URL:")
    st.info("URL content extraction will be routed through the core engine.")
elif input_mode == "Document (.docx) Upload":
    uploaded_file = st.file_uploader("Upload Word Document", type=["docx"])
    if uploaded_file is not None:
        st.info("Document loaded. Ready for parsing.")
        target_text = "FILE_LOADED"

if st.button("Execute Athena Evaluation"):
    if target_text:
        with st.spinner("Author is analyzing the data substrate..."):
            try:
                result = athena_cloud_evaluator.run_evaluation(target_text)
                st.success("Analysis Complete.")
                st.markdown("### Output")
                st.write(result)
            except Exception as e:
                st.error(f"Pipeline Error: Please verify function names in athena_cloud_evaluator.py match this interface. Details: {e}")
    else:
        st.warning("OPERATIONAL HALT: Please provide an input before executing.")
