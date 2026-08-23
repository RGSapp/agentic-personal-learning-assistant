import os
import streamlit as st
import requests

# ── Constants ────────────────────────────────────────────────────────────────
_raw_backend = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").strip().rstrip("/")
if not _raw_backend.startswith(("http://", "https://")):
    scheme = "http://" if ("localhost" in _raw_backend or "127.0.0.1" in _raw_backend) else "https://"
    _BACKEND = f"{scheme}{_raw_backend}"
else:
    _BACKEND = _raw_backend

CHAT_URL     = f"{_BACKEND}/chat"
UPLOAD_URL   = f"{_BACKEND}/upload"
DOCS_URL     = f"{_BACKEND}/documents"

ROUTE_META = {
    "learning":  {"icon": "🧠", "label": "Learning",  "color": "#6c63ff"},
    "quiz":      {"icon": "📝", "label": "Quiz",      "color": "#f5a623"},
    "research":  {"icon": "🔬", "label": "Research",  "color": "#1db954"},
    "unknown":   {"icon": "❓", "label": "Unknown",   "color": "#888"},
}

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agentic Learning Assistant",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── Global Reset ─────────────────────────── */
html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
    background: #0d0f1a;
    color: #e2e8f0;
}

[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(135deg, #0d0f1a 0%, #111827 60%, #0d1528 100%);
}

/* ─── Sidebar ──────────────────────────────── */
[data-testid="stSidebar"] {
    background: rgba(15, 17, 32, 0.95) !important;
    border-right: 1px solid rgba(108, 99, 255, 0.2);
    backdrop-filter: blur(20px);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* ─── Header ───────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, rgba(108,99,255,0.15) 0%, rgba(29,185,84,0.08) 100%);
    border: 1px solid rgba(108, 99, 255, 0.25);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 24px;
    backdrop-filter: blur(10px);
    text-align: center;
}
.app-header h1 {
    font-size: 2rem;
    font-weight: 700;
    background: linear-gradient(90deg, #a78bfa, #6c63ff, #1db954);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 6px 0;
}
.app-header p {
    color: #94a3b8;
    font-size: 0.95rem;
    margin: 0;
}

/* ─── Chat Messages ────────────────────────── */
.msg-wrapper {
    display: flex;
    margin-bottom: 16px;
    animation: fadeSlideIn 0.3s ease;
}
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}
.msg-bubble {
    max-width: 80%;
    padding: 14px 18px;
    border-radius: 16px;
    line-height: 1.6;
    font-size: 0.93rem;
}
.msg-user {
    margin-left: auto;
    background: linear-gradient(135deg, #6c63ff, #5a52d5);
    color: #fff;
    border-bottom-right-radius: 4px;
    box-shadow: 0 4px 20px rgba(108, 99, 255, 0.3);
}
.msg-assistant {
    margin-right: auto;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    color: #e2e8f0;
    border-bottom-left-radius: 4px;
    backdrop-filter: blur(10px);
}

/* ─── Route Badge ──────────────────────────── */
.route-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    margin-top: 6px;
    border: 1px solid;
}

/* ─── Sidebar Sections ─────────────────────── */
.sidebar-section {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 14px;
}
.sidebar-section-title {
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6c63ff !important;
    margin-bottom: 10px;
}

/* ─── Doc Chip ─────────────────────────────── */
.doc-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: rgba(108, 99, 255, 0.08);
    border: 1px solid rgba(108, 99, 255, 0.2);
    border-radius: 8px;
    margin-bottom: 6px;
    font-size: 0.8rem;
    color: #c4b5fd;
    word-break: break-all;
}

/* ─── Input Box ────────────────────────────── */
[data-testid="stChatInput"] {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(108, 99, 255, 0.3) !important;
    border-radius: 14px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #6c63ff !important;
    box-shadow: 0 0 0 3px rgba(108, 99, 255, 0.15) !important;
}

/* ─── Divider ──────────────────────────────── */
hr { border-color: rgba(255,255,255,0.08) !important; }

/* ─── Buttons ──────────────────────────────── */
.stButton > button {
    background: linear-gradient(135deg, #6c63ff, #5a52d5) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(108,99,255,0.4) !important;
}

/* ─── File Uploader ────────────────────────── */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.03) !important;
    border: 1px dashed rgba(108, 99, 255, 0.4) !important;
    border-radius: 12px !important;
}

/* ─── Hide default Streamlit branding ─────── */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session State Init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None
if "indexed_docs" not in st.session_state:
    st.session_state.indexed_docs = []
if "docs_loaded" not in st.session_state:
    st.session_state.docs_loaded = False


def fetch_indexed_docs():
    try:
        r = requests.get(DOCS_URL, timeout=5)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return []


def render_route_badge(route: str):
    meta = ROUTE_META.get(route, ROUTE_META["unknown"])
    color = meta["color"]
    label = meta["label"]
    icon  = meta["icon"]
    return (
        f'<span class="route-badge" style="color:{color};border-color:{color};'
        f'background:rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.12);">'
        f'{icon} {label}</span>'
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-section-title">⚙️ Settings</div>', unsafe_allow_html=True)
    current_topic = st.text_input(
        "Current Topic",
        value="Machine Learning",
        help="The topic context for quizzes and learning responses.",
        label_visibility="collapsed",
        placeholder="Current topic (e.g. Machine Learning)",
    )

    st.divider()

    # ── Upload Section ────────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">📂 Upload Documents</div>', unsafe_allow_html=True)
    st.caption("Supports PDF, DOCX, TXT · Multiple files allowed")

    uploaded_files = st.file_uploader(
        "Upload documents",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="file_uploader",
    )

    if st.button("⬆️  Ingest Documents", use_container_width=True, disabled=not uploaded_files):
        if uploaded_files:
            with st.spinner("Embedding documents…"):
                file_tuples = [
                    ("files", (f.name, f.getvalue(), f.type))
                    for f in uploaded_files
                ]
                try:
                    resp = requests.post(UPLOAD_URL, files=file_tuples, timeout=120)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.success(data["message"])
                        st.session_state.indexed_docs = fetch_indexed_docs()
                    else:
                        st.error(f"Upload failed ({resp.status_code}): {resp.text}")
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach backend. Is the FastAPI server running?")

    st.divider()

    # ── Indexed Documents ─────────────────────────────────────────────────────
    st.markdown('<div class="sidebar-section-title">📑 Indexed Documents</div>', unsafe_allow_html=True)

    if not st.session_state.docs_loaded:
        st.session_state.indexed_docs = fetch_indexed_docs()
        st.session_state.docs_loaded = True

    if st.button("🔄 Refresh", use_container_width=True):
        st.session_state.indexed_docs = fetch_indexed_docs()

    docs = st.session_state.indexed_docs
    if docs:
        for doc in docs:
            st.markdown(
                f'<div class="doc-chip">📄 {doc}</div>',
                unsafe_allow_html=True,
            )
    else:
        st.caption("No documents indexed yet. Upload files above to get started.")

    st.divider()

    # ── Clear Chat ────────────────────────────────────────────────────────────
    if st.button("🗑️  Clear Chat History", use_container_width=True):
        st.session_state.messages = []
        st.session_state.pending_question = None
        st.rerun()

# ── Main Content ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
  <h1>🧠 Agentic Learning Assistant</h1>
  <p>Upload your study materials · Ask questions · Get quizzed · Explore research</p>
</div>
""", unsafe_allow_html=True)

# ── Chat History ──────────────────────────────────────────────────────────────
for message in st.session_state.messages:
    role = message["role"]
    content = message["content"]
    route = message.get("router_decision", "")

    if role == "user":
        st.markdown(
            f'<div class="msg-wrapper"><div class="msg-bubble msg-user">{content}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        badge_html = render_route_badge(route) if route else ""
        st.markdown(
            f'<div class="msg-wrapper">'
            f'<div class="msg-bubble msg-assistant">{content}{("<br>" + badge_html) if badge_html else ""}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ── Chat Input ────────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask a question, request a quiz, or explore a topic…"):
    # Show user bubble immediately
    st.markdown(
        f'<div class="msg-wrapper"><div class="msg-bubble msg-user">{prompt}</div></div>',
        unsafe_allow_html=True,
    )
    st.session_state.messages.append({"role": "user", "content": prompt})

    payload = {
        "query": prompt,
        "current_topic": current_topic,
        "pending_question": st.session_state.pending_question,
    }

    with st.spinner("Thinking…"):
        try:
            response = requests.post(CHAT_URL, json=payload, timeout=120)

            if response.status_code == 200:
                data = response.json()
                bot_output = data["output"]
                final_state = data["state"]

                st.session_state.pending_question = final_state.get("pending_question")
                route = final_state.get("router_decision", "unknown")

                badge_html = render_route_badge(route)
                st.markdown(
                    f'<div class="msg-wrapper">'
                    f'<div class="msg-bubble msg-assistant">{bot_output}<br>{badge_html}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": bot_output,
                    "router_decision": route,
                })
            else:
                st.error(f"API error {response.status_code}: {response.text}")

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            st.error(f"❌ Cannot reach backend at `{_BACKEND}`. Please make sure the FastAPI server is running.")

