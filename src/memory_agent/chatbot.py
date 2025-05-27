from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from memory_agent.tools import wine_search, sort_wines
from memory_agent.prompts import SYSTEM_PROMPT
from langgraph.managed import IsLastStep, RemainingSteps
from typing import List, TypedDict
from langchain_core.messages import BaseMessage
from memory_agent.settings import get_settings

settings = get_settings()
class AgentStateWithWines(TypedDict):
    messages: List[BaseMessage]
    wines: list[dict] | None
    is_last_step: IsLastStep
    remaining_steps: RemainingSteps




tools = [wine_search, sort_wines]
model = init_chat_model(model="gemini-2.0-flash-lite", model_provider="google_genai", api_key=settings.gemini_api_key).bind_tools(tools)

agent = create_react_agent(model, tools, prompt=SYSTEM_PROMPT)

if __name__ == "__main__":
    messages = []
    while True:
        user_input = input("User: ")
        messages.append({"role": "user", "content": user_input})
        response = agent.invoke({"messages": messages})
        messages.append(response["messages"][-1])
        print("*" * 50)
        print("Assistant:", response["messages"][-1].content)
        print("*" * 50)