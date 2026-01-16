"""
Streamlit UI for OSRS Wiki RAG System
Lightweight web interface with chat-like experience.
Includes authentication and security features.
"""

import streamlit as st
import yaml
from rag_system import RAGSystem

# Page config
st.set_page_config(
    page_title="OSRS Wiki RAG",
    page_icon="⚔️",
    layout="wide"
)

# Load config for authentication
@st.cache_data
def load_config():
    with open("config.yaml", 'r') as f:
        return yaml.safe_load(f)

config = load_config()
auth_config = config.get('auth', {})
auth_enabled = auth_config.get('enabled', False)

# Authentication
def check_password():
    """Returns `True` if the user had the correct password."""
    if not auth_enabled:
        return True
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if (st.session_state["username"] == auth_config.get('username', 'admin') and
            st.session_state["password"] == auth_config.get('password', 'changeme')):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input("Username", key="username", on_change=password_entered)
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.text_input("Username", key="username", on_change=password_entered)
        st.text_input("Password", type="password", key="password", on_change=password_entered)
        st.error("😕 Username/password incorrect")
        return False
    else:
        # Password correct
        return True

# Check authentication
if not check_password():
    st.stop()

# Initialize session state
if 'rag_system' not in st.session_state:
    with st.spinner("Initializing RAG system..."):
        try:
            st.session_state.rag_system = RAGSystem()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"Error initializing RAG system: {e}")
            st.session_state.initialized = False

if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'user_id' not in st.session_state:
    # Generate a simple user ID based on session
    import hashlib
    session_id = str(id(st.session_state))
    st.session_state.user_id = hashlib.md5(session_id.encode()).hexdigest()[:8]

# Header
st.title("⚔️ OSRS Wiki RAG System")
st.markdown("Ask questions about Old School RuneScape using the wiki knowledge base!")

# Sidebar
with st.sidebar:
    st.header("About")
    st.markdown("""
    This RAG system uses:
    - **Chroma** for vector storage
    - **Sentence Transformers** for embeddings
    - **Ollama (Qwen 2.5 14B)** for generation
    
    Ask questions about items, quests, skills, monsters, and more!
    """)
    
    if st.session_state.initialized:
        st.success("✓ System Ready")
        st.info(f"📚 {st.session_state.rag_system.collection.count()} documents indexed")
        
        # Security info
        st.divider()
        st.header("Security")
        if st.session_state.rag_system.enable_rate_limiting:
            st.info("🛡️ Rate limiting: Enabled")
        if st.session_state.rag_system.enable_security:
            st.info("🛡️ Input validation: Enabled")
        if st.session_state.rag_system.enable_logging:
            log_count = st.session_state.rag_system.security_manager.get_log_count()
            st.info(f"📝 Queries logged: {log_count}")
            
            if st.button("🗑️ Clear Query Logs"):
                if st.session_state.rag_system.security_manager.clear_logs():
                    st.success("Logs cleared!")
                    st.rerun()
                else:
                    st.error("Failed to clear logs")
    else:
        st.error("✗ System Not Ready")
    
    if auth_enabled:
        st.divider()
        if st.button("🔒 Logout"):
            for key in list(st.session_state.keys()):
                if key != "password_correct":
                    del st.session_state[key]
            st.session_state["password_correct"] = False
            st.rerun()

# Main chat interface
if st.session_state.initialized:
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if available
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 Sources"):
                    for i, source in enumerate(message["sources"], 1):
                        st.markdown(f"{i}. **{source}**")
            
            # Show error info if available
            if message.get("error"):
                st.warning(f"⚠️ {message['error']}")
    
    # Chat input
    if prompt := st.chat_input("Ask a question about OSRS..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Searching wiki and generating answer..."):
                try:
                    result = st.session_state.rag_system.query(
                        prompt, 
                        user_id=st.session_state.user_id
                    )
                    
                    # Handle rejected queries
                    if result.get('rejected'):
                        st.error("❌ Query Rejected")
                        st.markdown(result['answer'])
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result['answer'],
                            "error": "Query was rejected by security filters"
                        })
                        st.rerun()
                    
                    # Handle rate limiting
                    if result.get('error') == 'rate_limit':
                        wait_time = result.get('wait_time', 2.0)
                        st.warning(f"⏱️ Rate Limit Exceeded")
                        st.markdown(result['answer'])
                        st.info(f"Please wait {wait_time:.1f} seconds before your next query.")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": result['answer'],
                            "error": f"Rate limit: wait {wait_time:.1f}s"
                        })
                        st.rerun()
                    
                    # Display answer
                    st.markdown(result['answer'])
                    
                    # Display sources
                    if result.get('sources'):
                        with st.expander("📚 Referenced Wiki Pages"):
                            for i, source in enumerate(result['sources'], 1):
                                st.markdown(f"{i}. **{source}**")
                    
                    # Add to chat history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result['answer'],
                        "sources": result.get('sources', [])
                    })
                    
                except Exception as e:
                    error_msg = f"Error processing query: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg,
                        "error": str(e)
                    })
    
    # Clear chat button
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear Chat"):
            st.session_state.messages = []
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()

else:
    st.error("RAG system failed to initialize. Please check your configuration and ensure:")
    st.markdown("""
    1. Vector database exists (run `create_vector_db.py`)
    2. Ollama is running with Qwen 2.5 14B model
    3. Configuration file is correct
    """)
