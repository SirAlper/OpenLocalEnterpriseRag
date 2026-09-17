import os
import streamlit as st
import requests
import json

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(
    page_title="Enterprise Local RAG",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #6c757d;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 12px;
        border-left: 4px solid #009688;
        margin-bottom: 10px;
    }
    .source-box {
        background-color: rgba(0, 150, 136, 0.08);
        border-radius: 6px;
        padding: 10px;
        margin-top: 8px;
        border-left: 3px solid #009688;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


# API Helper Functions
def fetch_stats():
    try:
        res = requests.get(f"{API_BASE_URL}/api/v1/stats", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


def fetch_documents():
    try:
        res = requests.get(f"{API_BASE_URL}/api/v1/documents", timeout=5)
        if res.status_code == 200:
            return res.json().get("documents", [])
    except Exception:
        return []
    return []


def upload_document(uploaded_file):
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        res = requests.post(f"{API_BASE_URL}/api/v1/upload-file", files=files, timeout=60)
        return res.status_code == 200, res.json().get("message", "Unknown response.")
    except Exception as e:
        return False, str(e)


def delete_document_api(filename):
    try:
        res = requests.delete(f"{API_BASE_URL}/api/v1/documents/{filename}", timeout=10)
        return res.status_code == 200, res.json().get("message", "Deleted.")
    except Exception as e:
        return False, str(e)


def fetch_database_status():
    try:
        res = requests.get(f"{API_BASE_URL}/api/v1/database/status", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        return None
    return None


def sync_table_api(table_name):
    try:
        res = requests.post(f"{API_BASE_URL}/api/v1/database/sync-table", json={"table_name": table_name}, timeout=60)
        return res.status_code == 200, res.json().get("message", "Operation completed.")
    except Exception as e:
        return False, str(e)


def query_rag_api(question):
    try:
        res = requests.post(
            f"{API_BASE_URL}/api/v1/query",
            json={"question": question},
            timeout=180
        )
        if res.status_code == 200:
            return res.json()
        return {"status": "error", "answer": f"Error: {res.text}", "sources": []}
    except Exception as e:
        return {"status": "error", "answer": f"API Connection Error: {e}", "sources": []}


# --- SESSION STATE INITIALIZATION ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hello! I am your enterprise local AI assistant. I can answer questions grounded strictly in your internal documents and connected databases.",
            "sources": []
        }
    ]


# --- SIDEBAR (CONTROL PANEL) ---
with st.sidebar:
    st.title("⚙️ Control Panel")

    # 1. System Status
    stats = fetch_stats()
    if stats:
        st.success("🟢 API Connected")
        st.markdown(f"**Device:** `{stats.get('device', 'Unknown')}`")
        st.markdown(f"**Model:** `{stats.get('llm_model', '').split('/')[-1]}`")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Documents", stats.get("total_documents", 0))
        with col2:
            st.metric("Vector Chunks", stats.get("total_chunks", 0))
    else:
        st.error("🔴 API Offline (FastAPI server not reachable)")
        st.info("Start backend in terminal: `uvicorn src.main:app --reload`")

    st.divider()

    # 2. Document Upload
    st.subheader("📤 Upload Document")
    uploaded_file = st.file_uploader(
        "Choose a PDF, Word, or TXT file",
        type=["pdf", "docx", "txt"],
        help="Uploaded files are automatically parsed, contextualized, and indexed into ChromaDB."
    )
    if uploaded_file is not None:
        if st.button("🚀 Upload and Index", use_container_width=True):
            with st.spinner("Parsing and vectorizing document..."):
                success, msg = upload_document(uploaded_file)
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(f"Upload failed: {msg}")

    st.divider()

    # 3. Indexed Documents List & Deletion
    st.subheader("📚 Indexed Documents")
    docs = fetch_documents()
    if docs:
        for doc in docs:
            col_info, col_del = st.columns([4, 1])
            with col_info:
                st.markdown(f"**{doc['filename']}**  \n<small>{doc['size_kb']} KB | {doc['chunk_count']} chunks</small>", unsafe_allow_html=True)
            with col_del:
                if st.button("🗑️", key=f"del_{doc['filename']}", help=f"Delete '{doc['filename']}'"):
                    success, msg = delete_document_api(doc['filename'])
                    if success:
                        st.toast(f"'{doc['filename']}' deleted!", icon="🗑️")
                        st.rerun()
                    else:
                        st.error(msg)
            st.write("---")
    else:
        st.caption("No indexed documents found.")

    st.divider()

    # 4. Database Management (SQLAlchemy Universal Connector)
    st.subheader("🗄️ Database")
    db_data = fetch_database_status()
    if db_data and db_data.get("connection", {}).get("status") == "connected":
        conn = db_data["connection"]
        dialect = conn.get("dialect", "").upper()
        tables = conn.get("tables", [])
        st.success(f"🟢 **{dialect}** Connected")
        st.caption(f"Accessible Tables: {len(tables)}")

        if tables:
            selected_table = st.selectbox("Select Table to Vectorize", tables)
            if st.button("🔄 Vectorize Table", key="sync_table_btn", use_container_width=True):
                with st.spinner(f"Vectorizing table '{selected_table}'..."):
                    success, msg = sync_table_api(selected_table)
                    if success:
                        st.toast(msg, icon="✅")
                        st.rerun()
                    else:
                        st.error(msg)

            with st.expander("🔍 Inspect Database Schema"):
                st.code(db_data.get("schema_summary", "Schema unavailable."), language="text")
    elif db_data and db_data.get("connection", {}).get("status") == "not_configured":
        st.caption("⚪ Database Not Configured")
        st.info("Optional: Set DATABASE_URL in .env to connect PostgreSQL, MSSQL, MySQL, Oracle, or SQLite.")
    else:
        st.caption("⚪ Database Offline")

    st.divider()
    if st.button("🧹 Clear Conversation", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Conversation history cleared. Ready for new questions!",
                "sources": []
            }
        ]
        st.rerun()


# --- MAIN PANEL (CHAT) ---
st.markdown('<div class="main-header">🏢 Enterprise Local RAG Assistant</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Zero-leakage, on-premise generative AI assistant running 100% locally on your infrastructure.</div>', unsafe_allow_html=True)

# Render Message History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Audit & Verification Badges
        if msg.get("is_refined") is True:
            st.caption("✍️ *LangGraph Audit: Response re-evaluated and refined according to company documents.*")
        elif msg.get("verified") is True and msg.get("sources"):
            st.caption("🛡️ *LangGraph Audit: Verified directly against company documents.*")
        elif msg.get("verified") is False and msg.get("sources"):
            st.caption("⚠️ *LangGraph Audit: Could not be fully verified against company documents.*")

        # Render Referenced Sources
        if msg.get("sources"):
            with st.expander(f"📚 Referenced Sources ({len(msg['sources'])} Chunks)"):
                for idx, src in enumerate(msg["sources"], 1):
                    distance_info = f" (Distance: {src['distance']})" if src.get("distance") is not None else ""
                    st.markdown(f"**{idx}. 📄 `{src['source']}` — Chunk #{src['chunk_index']}{distance_info}**")
                    st.markdown(f"> *\"{src['content'].strip()}\"*")
                    st.write("")

# User Input
if prompt := st.chat_input("Ask a question about your enterprise documents (e.g., 'What is our annual leave policy?')..."):
    # Append user message
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Query Backend with Thinking Spinner
    with st.chat_message("assistant"):
        with st.spinner("💭 Thinking and reviewing enterprise documents..."):
            res = query_rag_api(prompt)

        answer = res.get("answer", "No response received.")
        sources = res.get("sources", [])
        is_refined = res.get("is_refined", False)
        grade = str(res.get("hallucination_grade", "")).strip().lower()
        is_verified = ("evet" in grade or "yes" in grade) or is_refined

        # Render complete answer
        st.markdown(answer)

        # Audit Badges
        if is_refined:
            st.caption("✍️ *LangGraph Audit: Response re-evaluated and refined according to company documents.*")
        elif is_verified and sources:
            st.caption("🛡️ *LangGraph Audit: Verified directly against company documents.*")
        elif not is_verified and sources:
            st.caption("⚠️ *LangGraph Audit: Could not be fully verified against company documents.*")

        # Referenced Sources
        if sources:
            with st.expander(f"📚 Referenced Sources ({len(sources)} Chunks)"):
                for idx, src in enumerate(sources, 1):
                    distance_info = f" (Distance: {src['distance']})" if src.get("distance") is not None else ""
                    st.markdown(f"**{idx}. 📄 `{src['source']}` — Chunk #{src['chunk_index']}{distance_info}**")
                    st.markdown(f"> *\"{src['content'].strip()}\"*")
                    st.write("")

        # Save to session history
        st.session_state.messages.append({
            "role": "assistant",
            "content": answer,
            "sources": sources,
            "verified": is_verified,
            "is_refined": is_refined
        })
