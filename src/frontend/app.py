import os
import streamlit as st
import requests
import uuid
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# ── configurable via .env ──
API_BASE = os.getenv("API_BASE")
ANALYZE_TIMEOUT = int(os.getenv("ANALYZE_TIMEOUT"))
CHAT_TIMEOUT = int(os.getenv("CHAT_TIMEOUT"))

st.set_page_config(page_title="Contract Analyzer", page_icon="📄", layout="wide")
st.title("📄 Contract Analyzer")

API = st.sidebar.text_input("API URL", API_BASE)

tab1, tab2 = st.tabs(["📊 Compliance Analysis", "💬 Document Chat"])

# Tab 1: Compliance Analysis
with tab1:
    file = st.file_uploader("Upload PDF", type=["pdf"], key="analyze")
    
    if st.button("Analyze", disabled=not file) and file:
        with st.spinner("Analyzing..."):
            resp = requests.post(f"{API}/analyze", files={"file": (file.name, file.getvalue())}, timeout=ANALYZE_TIMEOUT)
        
        if resp.ok:
            df = pd.DataFrame([{
                "Question": i["compliance_question"],
                "State": i["compliance_state"],
                "Confidence": f"{i.get('confidence', 0)}%",
                "Relevant Quotes": "; ".join(i.get("relevant_quotes", [])) or "—",
                "Rationale": i.get("rationale", "")
            } for i in resp.json()["items"]])
            
            def color(val):
                colors = {"Fully Compliant": "#90EE90", "Partially Compliant": "#FFD700"}
                return f"background-color: {colors.get(val, '#FFB6C1')}"
            
            st.dataframe(df.style.applymap(color, subset=["State"]), hide_index=True, use_container_width=True)
        else:
            st.error(f"Error: {resp.status_code}")

# Tab 2: Document Chat
with tab2:
    if "session" not in st.session_state:
        st.session_state.session = str(uuid.uuid4())
        st.session_state.messages = []
        st.session_state.ready = False
    
    file = st.file_uploader("Upload PDF", type=["pdf"], key="chat")
    
    if st.button("Load", disabled=not file) and file:
        with st.spinner("Loading..."):
            resp = requests.post(f"{API}/rag/ingest", files={"file": (file.name, file.getvalue())},
                                 params={"session_id": st.session_state.session}, timeout=CHAT_TIMEOUT)
        if resp.ok:
            st.session_state.ready = True
            st.session_state.messages = []
            st.success(f"Loaded {resp.json()['chunks_added']} chunks")
    
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["content"])
    
    if prompt := st.chat_input("Ask...", disabled=not st.session_state.ready):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.chat_message("user").markdown(prompt)
        
        with st.chat_message("assistant"), st.spinner("..."):
            resp = requests.post(f"{API}/rag/chat",
                                 json={"session_id": st.session_state.session, "question": prompt}, timeout=CHAT_TIMEOUT)
            answer = resp.json()["answer"] if resp.ok else "Error"
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})