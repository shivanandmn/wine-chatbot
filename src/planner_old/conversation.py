"""
Conversation utilities for the wine chatbot.
"""
from typing import Dict, List, Any, Optional
from langchain.schema import HumanMessage, AIMessage, BaseMessage

def get_conversation_history(state: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Extract conversation history from the state.
    
    Args:
        state: The state dictionary from the wine planner
        
    Returns:
        List of message dictionaries with 'role' and 'content' keys
    """
    if 'messages' in state and isinstance(state['messages'], list):
        # Convert any LangChain message objects to dictionaries
        messages = []
        for msg in state['messages']:
            if isinstance(msg, BaseMessage):
                # Convert LangChain message to dict format
                role = 'user' if isinstance(msg, HumanMessage) else 'assistant'
                messages.append({'role': role, 'content': msg.content})
            elif isinstance(msg, dict) and 'role' in msg and 'content' in msg:
                # Already in the right format
                messages.append(msg)
        return messages
    return []

def get_latest_response(state: Dict[str, Any]) -> Optional[str]:
    """
    Get the latest assistant response from the state.
    
    Args:
        state: The state dictionary from the wine planner
        
    Returns:
        The content of the latest assistant message, or None if not found
    """
    # Check for LangChain message objects first
    if 'messages' in state and isinstance(state['messages'], list):
        for msg in reversed(state['messages']):
            # Handle LangChain AIMessage objects
            if isinstance(msg, AIMessage):
                return msg.content
            # Handle dictionary format messages
            elif isinstance(msg, dict) and msg.get('role') == 'assistant':
                return msg.get('content')
    
    # Fallback to processed conversation history
    messages = get_conversation_history(state)
    for msg in reversed(messages):
        if msg.get('role') == 'assistant':
            return msg.get('content')
            
    return None

def format_response(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the final response from the wine planner state.
    
    Args:
        state: The state dictionary from the wine planner
        
    Returns:
        Dictionary with 'response' and 'conversation_history' keys
    """
    response = get_latest_response(state)
    history = get_conversation_history(state)
    
    return {
        "response": response or "I'm not sure how to respond to that.",
        "conversation_history": history
    }
