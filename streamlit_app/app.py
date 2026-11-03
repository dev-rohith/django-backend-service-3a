import uuid

import requests
import streamlit as st

BACKEND = "http://localhost:8000"


def _headers() -> dict:
    return {"Authorization": f"Token {st.session_state.token}"}


def login(username: str, password: str) -> str | None:
    try:
        r = requests.post(
            f"{BACKEND}/api/auth/login/",
            json={"username": username, "password": password},
            timeout=10,
        )
        if r.status_code == 200:
            return r.json().get("token")
    except requests.RequestException:
        pass
    return None


def upload_file(file) -> dict:
    try:
        r = requests.post(
            f"{BACKEND}/api/agent/upload/",
            headers=_headers(),
            files={"file": (file.name, file.getvalue(), "application/octet-stream")},
            timeout=30,
        )
        return r.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


def send_message(message: str) -> dict:
    try:
        r = requests.post(
            f"{BACKEND}/api/agent/chat/",
            headers=_headers(),
            json={"message": message, "session_id": st.session_state.session_id},
            timeout=120,
        )
        return r.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}


st.set_page_config(page_title="GenAI Assistant", layout="wide", page_icon="🤖")

# ── Login gate ────────────────────────────────────────────────────────────────
if "token" not in st.session_state:
    st.title("GenAI Assistant")
    st.subheader("Login")

    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

    if submitted:
        token = login(username, password)
        if token:
            st.session_state.token = token
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.rerun()
        else:
            st.error("Invalid credentials. Try again.")

    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("Documents")
    uploaded = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])
    if uploaded:
        if st.button("Ingest Document", use_container_width=True):
            with st.spinner("Ingesting…"):
                result = upload_file(uploaded)
            if "error" in result:
                st.error(result["error"])
            else:
                st.success(
                    f"Ingested **{uploaded.name}** — "
                    f"{result['chunk_count']} chunks indexed."
                )

    st.divider()
    st.caption("Session controls")
    if st.button("New Conversation", use_container_width=True):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.caption(f"Session `{st.session_state.session_id[:8]}…`")
    st.divider()

    if st.button("Logout", use_container_width=True):
        for key in ["token", "session_id", "messages"]:
            st.session_state.pop(key, None)
        st.rerun()

# ── Chat interface ────────────────────────────────────────────────────────────
st.title("GenAI Assistant 🤖")
st.caption(
    "Ask anything — questions about uploaded documents, "
    "current weather in any city, or general topics."
)

for msg in st.session_state.get("messages", []):
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        sources = msg.get("sources") or []
        if sources:
            with st.expander(f"📄 {len(sources)} source chunk(s)", expanded=False):
                for i, src in enumerate(sources, 1):
                    st.markdown(f"**Source {i}** — document `{src['document_id']}`")
                    text = src["chunk_text"]
                    st.text(text[:500] + ("…" if len(text) > 500 else ""))
                    if i < len(sources):
                        st.divider()

prompt = st.chat_input("Ask anything…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            result = send_message(prompt)

        if "error" in result:
            st.error(result["error"])
            st.session_state.messages.append(
                {"role": "assistant", "content": f"Error: {result['error']}"}
            )
        else:
            response_text = result.get("response", "")
            sources = result.get("sources") or []

            st.write(response_text)

            if sources:
                with st.expander(f"📄 {len(sources)} source chunk(s)", expanded=True):
                    for i, src in enumerate(sources, 1):
                        st.markdown(f"**Source {i}** — document `{src['document_id']}`")
                        text = src["chunk_text"]
                        st.text(text[:500] + ("…" if len(text) > 500 else ""))
                        if i < len(sources):
                            st.divider()

            st.session_state.messages.append(
                {"role": "assistant", "content": response_text, "sources": sources}
            )
