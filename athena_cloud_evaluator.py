import streamlit as st
import requests

def main():
    st.title("API Diagnostic Node")
    api_key = st.secrets.get("GEMINI_API_KEY")
    if st.button("List Available Models"):
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        response = requests.get(url).json()
        if "models" in response:
            for model in response["models"]:
                st.write(f"Available Model: {model['name']}")
        else:
            st.error(f"Error: {response}")

if __name__ == "__main__":
    main()
