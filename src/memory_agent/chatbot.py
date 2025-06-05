from langgraph.prebuilt import create_react_agent
from langchain.chat_models import init_chat_model
from memory_agent.tools import wine_search, sort_wines
from memory_agent.prompts import SYSTEM_PROMPT
from langgraph.managed import IsLastStep, RemainingSteps
from typing import List, TypedDict
from langchain_core.messages import BaseMessage
import streamlit as st
import logging
import os
from dotenv import load_dotenv
load_dotenv()
from settings import get_settings

class AgentStateWithWines(TypedDict):
    messages: List[BaseMessage]
    wines: list[dict] | None
    is_last_step: IsLastStep
    remaining_steps: RemainingSteps

# Get API key from Streamlit secrets
settings = get_settings()
api_key = settings.gemini_api_key
if not api_key:
    raise ValueError("Gemini API key not found in configuration")

logging.info("Initializing chat model...")
tools = [wine_search, sort_wines]

try:
    model = init_chat_model(
        model="gemini-2.5-flash-preview-05-20",
        model_provider="google_genai",
        api_key=api_key,
        credentials=None  # Explicitly set to None to force API key auth
    ).bind_tools(tools)
    logging.info("Chat model initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize chat model: {str(e)}")
    raise

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