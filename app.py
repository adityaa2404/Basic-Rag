# app.py
import streamlit as st
import requests
import os

# --- Configuration ---
BACKEND_URL = "http://127.0.0.1:8000"

# --- Session State Initialization ---
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- UI ---
st.set_page_config(page_title="📄 Document Q&A", layout="wide")
st.title("📄 Query Your Documents")

def remove_file(filename):
    """Callback function to handle file removal."""
    try:
        response = requests.post(f"{BACKEND_URL}/delete_document/", json={"filename": filename})
        if response.status_code == 200:
            st.session_state.processed_files.remove(filename)
            
            ### THIS IS THE NEW LINE TO FIX THE BUG ###
            st.session_state.messages = [] 
            
            st.toast(f"✅ Removed {filename} successfully!")
        else:
            st.error(f"❌ Error removing file: {response.json().get('detail', response.text)}")
    except requests.RequestException as e:
        st.error(f"❌ Connection Error: {e}")

with st.sidebar:
    st.header("Upload Documents")
    uploaded_files = st.file_uploader(
        "Choose files", type=["pdf", "txt", "xls", "xlsx"], accept_multiple_files=True
    )
    if st.button("Process and Index", use_container_width=True) and uploaded_files:
        with st.spinner("Processing files..."):
            api_files = [("files", (file.name, file.getvalue())) for file in uploaded_files]
            try:
                response = requests.post(f"{BACKEND_URL}/upload/", files=api_files)
                if response.status_code == 200:
                    processed_filenames = response.json().get("filenames", [])
                    for fname in processed_filenames:
                        if fname not in st.session_state.processed_files:
                            st.session_state.processed_files.append(fname)
                    st.success("✅ Files processed successfully!")
                else:
                    st.error(f"❌ Error: {response.json().get('detail', response.text)}")
            except requests.RequestException as e:
                st.error(f"❌ Connection Error: {e}")

    st.markdown("---")
    st.header("Indexed Documents")
    if not st.session_state.processed_files:
        st.info("No documents have been indexed yet.")
    else:
        for filename in st.session_state.processed_files:
            col1, col2 = st.columns([0.8, 0.2])
            with col1: st.text(filename)
            with col2: st.button("Remove", key=f"remove_{filename}", on_click=remove_file, args=[filename], use_container_width=True)

# --- Main Chat Interface ---
st.header("Ask a Question")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask about your documents..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    with st.chat_message("assistant"):
        if not st.session_state.processed_files:
            st.warning("Please upload and process a document first.")
        else:
            with st.spinner("Thinking..."):
                try:
                    response = requests.post(f"{BACKEND_URL}/ask/", json={"query": prompt})
                    if response.status_code == 200:
                        result = response.json()
                        answer = result.get("answer", "No answer found.")
                        sources = result.get("sources", [])
                        full_response = f"{answer}\n\n*Sources: {', '.join(sources)}*"
                        st.markdown(full_response)
                        st.session_state.messages.append({"role": "assistant", "content": full_response})
                    else:
                        st.error(f"❌ Error: {response.json().get('detail', response.text)}")
                except requests.RequestException as e:
                    st.error(f"❌ Connection Error: {e}")