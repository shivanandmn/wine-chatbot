import streamlit as st
from memory_agent.chatbot import agent
from langchain_core.messages import HumanMessage, AIMessage
from config import get_streamlit_config

# Apply Streamlit configurations
config = get_streamlit_config()
st.set_page_config(**config)

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []

def main():
    st.title("🍷 Wine Chatbot")
    st.write("Ask me anything about wines! I can help you search and sort wines based on your preferences.")
    
    init_session_state()
    
    # Display chat messages
    for message in st.session_state.messages:
        if isinstance(message, HumanMessage):
            with st.chat_message("user"):
                st.write(message.content)
        else:
            with st.chat_message("assistant"):
                st.write(message.content)
    
    # Chat input
    if prompt := st.chat_input("What would you like to know about wines?"):
        # Add user message to chat history
        st.session_state.messages.append(HumanMessage(content=prompt))
        with st.chat_message("user"):
            st.write(prompt)
            
        # Get bot response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = agent.invoke({"messages": st.session_state.messages})
                assistant_message = response["messages"][-1]
                st.session_state.messages.append(assistant_message)
                st.write(assistant_message.content)

if __name__ == "__main__":
    main()
