"""Graphs that extract memories on a schedule."""

import asyncio
import logging
from datetime import datetime

from langchain.chat_models import init_chat_model
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph, START
from langgraph.store.base import BaseStore
from memory_agent import configuration, tools, utils
from memory_agent.state import State
from langgraph.graph import MessagesState
from memory_agent.persistence import memory
from memory_agent.utils import save_graph_image
from langchain_core.messages import SystemMessage, HumanMessage, RemoveMessage
from memory_agent.prompts import SYSTEM_PROMPT
from memory_agent.tools import wine_search
from langgraph.prebuilt import create_react_agent
logger = logging.getLogger(__name__)

# Initialize the language model to be used for memory extraction
model = init_chat_model(model="gemini-2.0-flash-lite", model_provider="google_genai").bind_tools([wine_search])

class State(MessagesState):
    summary: str

# Define the logic to call the model
def call_model(state: State):
    # Get messages or initialize empty list
    messages = state.get("messages", [])
    
    # If no messages or first message is not a system message, add system message
    if not messages or not isinstance(messages[0], SystemMessage):
        system_message = SYSTEM_PROMPT.format(
            user_info="Ravi",
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        messages = [SystemMessage(content=system_message)] + messages
    
    # Ensure all messages have content
    messages = [msg for msg in messages if msg.content.strip()]
    
    # If no valid messages after filtering, return empty response
    if not messages:
        return {"messages": []}
    
    # Invoke the model and handle tool calls
    response = model.invoke(messages)
    
    return {"messages": [response]}

def summarize_conversation(state: State):
    print("summarize_conversation :", state)
    # First, we get any existing summary
    summary = state.get("summary", "")

    # Create our summarization prompt 
    if summary:
        
        # A summary already exists
        summary_message = (
            f"This is summary of the conversation to date: {summary}\n\n"
            "Extend the summary by taking into account the new messages above:"
        )
        
    else:
        summary_message = "Create a summary of the conversation above:"

    # Add prompt to our history
    messages = state["messages"] + [HumanMessage(content=summary_message)]
    response = model.invoke(messages)
    
    # Delete all but the 2 most recent messages
    delete_messages = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]
    return {"summary": response.content, "messages": delete_messages}

# Determine whether to end or summarize the conversation
def should_continue(state: State):
    
    """Return the next node to execute."""
    
    messages = state["messages"]
    
    # # If there are more than six messages, then we summarize the conversation
    # if len(messages) > 6:
    #     return "summarize_conversation"
    
    # Otherwise we can just end
    return END


def create_graph(checkpointer=None):
    """Create and return the conversation graph.
    
    Args:
        checkpointer: Optional checkpointer for persistence
        
    Returns:
        Compiled graph ready for use
    """
    # Define a new graph
    workflow = StateGraph(State)
    workflow.add_node("conversation", call_model)
    workflow.add_node(summarize_conversation)

    # Set the entrypoint as conversation
    workflow.add_edge(START, "conversation")
    workflow.add_conditional_edges("conversation", should_continue)
    workflow.add_edge("summarize_conversation", END)

    # Compile
    graph = workflow.compile(checkpointer=checkpointer)
    graph.name = "MemoryAgent"
    save_graph_image(graph)
    
    return graph

if __name__ == "__main__":
    # When run directly, create the graph but don't execute any conversations
    graph = create_graph(memory )

    # Create a thread
    config = {"configurable": {"thread_id": "6"}}

    while True:
        input_message = input("User: ")
        input_message = HumanMessage(content=input_message)
        if "skip" in input_message:
            output = graph.invoke({"messages": []}, config)
        else:
            output = graph.invoke({"messages": [input_message]}, config)
        # Start conversation
         
        for m in output['messages'][-1:]:
            m.pretty_print()

