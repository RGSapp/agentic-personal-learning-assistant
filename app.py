import streamlit as st
import requests

# Constants
API_URL = "http://127.0.0.1:8000/chat"

# Page config
st.set_page_config(
    page_title="Agentic Learning Assistant",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 Agentic Personal Learning Assistant")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "pending_question" not in st.session_state:
    st.session_state.pending_question = None

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    current_topic = st.text_input("Current Topic", value="Machine Learning", help="Set the topic you want to learn about.")
    st.divider()
    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.session_state.pending_question = None
        st.rerun()

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "router_decision" in message:
             st.caption(f"*Routed to: {message['router_decision']}*")

# React to user input
if prompt := st.chat_input("Ask a question, request a quiz, or research a topic..."):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Prepare payload for backend
    payload = {
        "query": prompt,
        "current_topic": current_topic,
        "pending_question": st.session_state.pending_question
    }

    with st.spinner("Thinking..."):
        try:
            # Send request to FastAPI backend
            response = requests.post(API_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                bot_output = data["output"]
                final_state = data["state"]
                
                # Update pending question state based on backend response
                st.session_state.pending_question = final_state.get("pending_question")
                router_decision = final_state.get("router_decision", "unknown")

                # Display assistant response in chat message container
                with st.chat_message("assistant"):
                    st.markdown(bot_output)
                    st.caption(f"*Routed to: {router_decision}*")
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": bot_output,
                    "router_decision": router_decision
                })
                
            else:
                st.error(f"Error from API: {response.status_code} - {response.text}")
                
        except requests.exceptions.ConnectionError:
             st.error("Failed to connect to the backend API. Is FastAPI running on http://127.0.0.1:8000 ?")
