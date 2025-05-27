
from memory_agent.utils import save_graph_image
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from langchain.chat_models import init_chat_model
from langgraph.graph import END, StateGraph, START
from memory_agent import tools
from langgraph.graph import MessagesState
from memory_agent.persistence import memory
from memory_agent.utils import save_graph_image
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from memory_agent.prompts import SYSTEM_PROMPT
from memory_agent.tools import wine_search, sort_wines
from datetime import datetime
import logging
import json
from memory_agent.utils import format_data_to_string


logger = logging.getLogger(__name__)
tools = [wine_search, sort_wines]
model = init_chat_model(model="gemini-2.0-flash-lite", model_provider="google_genai").bind_tools(tools)

class ConversationState(MessagesState):
    wines: list[dict] | None = None

# Define the logic to call the model
def assistant_bot(state: ConversationState):
    # Get messages or initialize empty list
    messages = state.get("messages", [])
    
    # If no messages or first message is not a system message, add system message
    if not messages or not isinstance(messages[0], SystemMessage):
        system_message = SYSTEM_PROMPT.format(
            user_info="James",
            time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        messages = [SystemMessage(content=system_message)] + messages
    
    # If no valid messages after filtering, return empty response
    if not messages:
        return {"messages": [], "wines": state.get("wines")}
    
    if isinstance(messages[-1], ToolMessage) and messages[-1].name == "wine_search":
        vintages_dict = json.loads(messages[-1].content)
        vintages =  [format_data_to_string(res["data"]) for res in vintages_dict]
        messages[-1].content = "\n\n".join(vintages)
        state["wines"] = [res["data"] for res in vintages_dict]
    
    if isinstance(messages[-1], ToolMessage) and messages[-1].name == "sort_wines":
        wines = json.loads(messages[-1].content)
        wines =  [format_data_to_string(res) for res in wines]
        messages[-1].content = "\n\n".join(wines)

    
    # Invoke the model and handle tool calls
    response = model.invoke(messages)

    if len(response.tool_calls) == 1 and response.tool_calls[0]["name"] == "sort_wines":
        response.tool_calls[0]["args"]["wines"] = state.get("wines")
    
    return {"messages": [response], "wines": state.get("wines")}

def route_to_wine_analysis(state: ConversationState):
    wines = state.get("wines")
    if wines is None:
        return "assistant_bot"
    return "wine_analysis"

def wine_analysis(state: ConversationState):
    wines = state.get("wines")
    if wines is None:
        return {"messages": []}
    
    
    
        



graph_builder = StateGraph(ConversationState)
graph_builder.add_node("tools", ToolNode(tools))
graph_builder.add_node("assistant_bot", assistant_bot)
graph_builder.add_node("wine_analysis", wine_analysis)
graph_builder.add_edge("tools", "assistant_bot")
graph_builder.add_conditional_edges(
     "assistant_bot", tools_condition
 )
graph_builder.add_edge("assistant_bot", "wine_analysis")
graph_builder.add_edge("wine_analysis", "assistant_bot")
graph_builder.add_edge("tools", "wine_analysis")
graph_builder.add_conditional_edges("wine_analysis", tools_condition)
graph_builder.set_entry_point("assistant_bot")
graph = graph_builder.compile(memory)
save_graph_image(graph)

# Create a thread
config = {"configurable": {"thread_id": "47"}}
input_message = "red wine, under 200, dry, no specific region/occasion/type/style"
while True:
    input_message = HumanMessage(content=input_message)
    output = graph.invoke({"messages": [input_message]}, config)
    # Start conversation
        
    for m in output['messages'][-1:]:
        if isinstance(m, ToolMessage):
            print(m.content)
                
        else:
            m.pretty_print()
    input_message = input("User: ")