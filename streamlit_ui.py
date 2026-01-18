"""
Streamlit UI for OSRS Wiki RAG System
OSRS-themed interface using Streamlit + CSS only
"""

import streamlit as st
import yaml
from rag_system import RAGSystem
import hashlib
import os

# --------------------------------------------------
# Page config
# --------------------------------------------------
st.set_page_config(
    page_title="OSRS Wiki Sage",
    page_icon="⚔️",
    layout="wide"
)

# --------------------------------------------------
# Paths for custom avatars
# --------------------------------------------------
ICON_FOLDER = os.path.join(os.path.dirname(__file__), "assets", "icons")
USER_ICON = os.path.join(ICON_FOLDER, "user.png")
ASSISTANT_ICON = os.path.join(ICON_FOLDER, "assistant.png")

def get_avatar(role: str) -> str:
    return USER_ICON if role == "user" else ASSISTANT_ICON

# --------------------------------------------------
# OSRS-style CSS
# --------------------------------------------------
st.markdown("""
<style>
/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* App background */
.stApp { background-color: #0e0e0e; }

/* Headings */
h1, h2, h3 {
    font-family: Georgia, serif;
    color: #ffffff;
    text-shadow: 1px 1px #e4d6b0;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #e4d6b0;
    border-right: 3px solid #8b5a2b;
}

/* Buttons */
.stButton > button {
    background-color: #6b3e1e;
    color: #f4e6c1;
    border: 2px solid #3b240f;
    font-weight: bold;
}
.stButton > button:hover { background-color: #8b5a2b; }

/* Chat messages */
.stChatMessage {
    background-color: #f7efd8;
    border: 2px solid #8b5a2b;
    border-radius: 6px;
    padding: 10px;
    margin-bottom: 8px;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Load config
# --------------------------------------------------
@st.cache_data
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

config = load_config()
auth_config = config.get("auth", {})
auth_enabled = auth_config.get("enabled", False)

# --------------------------------------------------
# Authentication
# --------------------------------------------------
def check_password():
    if not auth_enabled:
        return True

    def password_entered():
        if (
            st.session_state["username"] == auth_config.get("username", "admin")
            and st.session_state["password"] == auth_config.get("password", "changeme")
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("Username", key="username", on_change=password_entered)
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        return False

    if not st.session_state["password_correct"]:
        st.text_input("Username", key="username", on_change=password_entered)
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        st.error("The gates remain closed.")
        return False

    return True

if not check_password():
    st.stop()

# --------------------------------------------------
# Session state
# --------------------------------------------------
if "rag_system" not in st.session_state:
    with st.spinner("Consulting ancient tomes..."):
        try:
            st.session_state.rag_system = RAGSystem()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Failed to summon the Oracle: {e}")
            st.session_state.initialized = False

if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_id" not in st.session_state:
    session_id = str(id(st.session_state))
    st.session_state.user_id = hashlib.md5(session_id.encode()).hexdigest()[:8]

# --------------------------------------------------
# Header
# --------------------------------------------------
st.markdown("""
<div style="text-align:center; padding:10px;">
    <img src="https://oldschool.runescape.wiki/images/Official_website_banner_logo.png?cce42" width="560">
    <h2 style="color: #ffffff;">Wiki Sage</h2>
    <p style="color: #09c040;">Seek Wisdom from the Old School RuneScape Archives</p>
</div>
""", unsafe_allow_html=True)

# --------------------------------------------------
# Sidebar
# --------------------------------------------------
with st.sidebar:
    st.header("📜 Adventurer's Log")

    if st.session_state.initialized:
        st.success("✓ Oracle Ready")
        st.info(f"{st.session_state.rag_system.collection.count()} pages indexed")

        st.divider()
        st.header("Protections:")

        if st.session_state.rag_system.enable_rate_limiting:
            st.info("Rate Limiting Active")

        if st.session_state.rag_system.enable_security:
            st.info("Input Validation Active")

        if st.session_state.rag_system.enable_logging:
            log_count = st.session_state.rag_system.security_manager.get_log_count()
            st.info(f"Queries Recorded: {log_count}")

            if st.button("Burn the Logs"):
                if st.session_state.rag_system.security_manager.clear_logs():
                    st.success("The records are no more.")
                    st.rerun()
                else:
                    st.error("The flames failed.")

    else:
        st.error("✗ Sage Unavailable")

    if auth_enabled:
        st.divider()
        if st.button("Leave the Chamber"):
            for key in list(st.session_state.keys()):
                if key != "password_correct":
                    del st.session_state[key]
            st.session_state["password_correct"] = False
            st.rerun()

# --------------------------------------------------
# Main chat
# --------------------------------------------------
if st.session_state.initialized:

    # Display chat history with dynamic avatars
    for message in st.session_state.messages:
        avatar_path = get_avatar(message["role"])
        with st.chat_message(message["role"], avatar=avatar_path):
            st.markdown(message["content"])

            if message["role"] == "assistant" and "sources" in message:
                with st.expander("Referenced Tomes"):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"{i}. **{source}**")

            if message.get("error"):
                st.warning(f"⚠️ {message['error']}")

    # Chat input
    if prompt := st.chat_input("Ask the Wise Old Man..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=ASSISTANT_ICON):
            with st.spinner("Searching forgotten scrolls..."):
                try:
                    result = st.session_state.rag_system.query(
                        prompt,
                        user_id=st.session_state.user_id
                    )

                    if result.get("rejected"):
                        st.error("The gods reject your question.")
                        st.markdown(result["answer"])
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "error": "Rejected by protections"
                        })
                        st.rerun()

                    if result.get("error") == "rate_limit":
                        wait_time = result.get("wait_time", 2.0)
                        st.warning("You must wait before asking again.")
                        st.markdown(result["answer"])
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result["answer"],
                            "error": f"Wait {wait_time:.1f}s"
                        })
                        st.rerun()

                    st.markdown(result["answer"])

                    if result.get("sources"):
                        with st.expander("Referenced Tomes"):
                            for i, source in enumerate(result["sources"], 1):
                                st.markdown(f"{i}. **{source}**")

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result["answer"],
                        "sources": result.get("sources", [])
                    })

                except Exception as e:
                    error_msg = f"The Sage falters: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "error": str(e)
                    })

    # Chat controls
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Clear Scrolls"):
            st.session_state.messages = []
            st.rerun()

    with col2:
        if st.button("Refresh"):
            st.rerun()

else:
    st.error("The Oracle could not be summoned.")
    st.markdown("""
    **Ensure the following:**
    1. Vector database exists
    2. Ollama is running with Qwen 2.5 14B
    3. Configuration is correct
    """)
