from typing import Any, Dict, Optional, Annotated, Literal
from langchain.schema import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import MessagesState
from models import Plan
import logging
from template import apply_prompt_template
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.types import Command, interrupt
import os
from memory_agent.tools import wine_search
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from config import Configuration
import json
from utils import repair_json_output
from models import StepType
from tools import python_repl_tool

logger = logging.getLogger(__name__)

llm_model_plan = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-preview-05-20",
    thinking_budget=100,
    api_key=os.getenv("GEMINI_API_KEY"),
    credentials=None
)

llm_model = init_chat_model(
    model="gemini-2.0-flash",
    model_provider="google_genai",
    api_key=os.getenv("GEMINI_API_KEY"),
    credentials=None
)

from langgraph.prebuilt import create_react_agent

from template import apply_prompt_template


# Create agents using configured LLM types
def create_agent(agent_name: str, tools: list, prompt_template: str):
    """Factory function to create agents with consistent configuration."""
    return create_react_agent(
        name=agent_name,
        model=llm_model.bind_tools(tools),
        tools=tools,
        prompt=lambda state: apply_prompt_template(prompt_template, state),
    )


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    observations: list[str] = []
    plan_iterations: int = 0
    current_plan: Plan | str = None
    final_report: str = ""


@tool
def handoff_to_planner(
    task_title: Annotated[str, "The wine planning task to be handed off, including event details like occasion, number of guests, food pairings, and any specific preferences."]
):
    """Handoff the wine planning task to the Wine Event Planner agent. This should be used when you have gathered enough initial context about the event (e.g., occasion, number of guests, food being served, wine preferences). The planner will create a detailed plan for wine selection and quantity calculation."""
    # This tool signals that we should transition to the planner agent
    # The planner will create a wine selection plan and execute it
    return

def coordinator_node(
    state: State, config: RunnableConfig
) -> Command[Literal["planner",  "__end__"]]:
    logger.info("Coordinator talking.")
    messages = apply_prompt_template("coordinator", state)
    response = llm_model.bind_tools(handoff_to_planner).invoke(messages)
    logger.debug(f"Current state messages: {state['messages']}")
    goto = "__end__"

    if len(response.tool_calls) > 0:
        goto = "planner"
        return Command(
            goto = goto,
        )
    else:
        logger.warning(
            "Coordinator response contains no tool calls. Terminating workflow execution."
        )
        logger.debug(f"Coordinator response: {response}")
    
    return Command(
        goto = goto,
        update = {
            "messages": [AIMessage(content=response.content, name="coordinator")],
        }
    )


def planner_node(
    state: State, config: RunnableConfig
) -> Command[Literal["human_feedback", "reporter"]]:
    """Wine Event Planner node that generates a detailed plan for wine selection.
    This includes determining wine types needed, quantities, and budget allocation."""
    logger.info("Planner generating full plan")
    configurable = Configuration.from_runnable_config(config)
    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    messages = apply_prompt_template("planner", state, configurable)

    llm = llm_model.with_structured_output(
            Plan,
            method="json_mode",
        )
    # if the plan iterations is greater than the max plan iterations, return the reporter node
    if plan_iterations >= configurable.max_plan_iterations:
        return Command(goto="reporter")

    try:
        response = llm.invoke(messages)
        logger.debug(f"Current state messages: {state['messages']}")
        logger.info(f"Planner response: {response}")
        # Check if all steps are complete first
        if response.steps and all(step.execution_res for step in response.steps):
            return Command(
                update={
                    "messages": [AIMessage(content=response.model_dump_json(indent=4), name="planner")],
                    "current_plan": response,
                },
                goto="reporter",  # All steps are done, go to reporter
            )
        if response.has_enough_context:
            logger.info("Planner response has enough context.")
            return Command(
                update={
                    "messages": [AIMessage(content=response.model_dump_json(indent=4), name="planner")],
                    "current_plan": response,
                },
                goto="research_team",  # Changed from reporter to research_team to execute the plan
            )
        return Command(
            update={
                "messages": [AIMessage(content=response.model_dump_json(indent=4), name="planner")],
                "current_plan": response,
            },
            goto="human_feedback",
        )
    except Exception as e:
        logger.error(f"Error processing planner response: {e}")
        if plan_iterations > 0:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

def human_feedback_node(
    state,
) -> Command[Literal["planner", "research_team", "reporter", "__end__"]]:
    current_plan = state.get("current_plan", "")
    feedback = interrupt("Please Review the Plan.")

    # if the feedback is not accepted, return the planner node
    if feedback and str(feedback).upper().startswith("[EDIT_PLAN]"):
        return Command(
            update={
                "messages": [
                    HumanMessage(content=feedback, name="feedback"),
                ],
            },
            goto="planner",
        )
    elif feedback and str(feedback).upper().startswith("[ACCEPTED]"):
        logger.info("Plan is accepted by user.")
    else:
        raise TypeError(f"Interrupt value of {feedback} is not supported.")

    plan_iterations = state["plan_iterations"] if state.get("plan_iterations", 0) else 0
    goto = "research_team"
    try:
        current_plan = repair_json_output(current_plan)
        # increment the plan iterations
        plan_iterations += 1
        # parse the plan
        new_plan = json.loads(current_plan)
        if new_plan["has_enough_context"]:
            goto = "reporter"
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        if plan_iterations > 0:
            return Command(goto="reporter")
        else:
            return Command(goto="__end__")

    return Command(
        update={
            "current_plan": Plan.model_validate(new_plan),
            "plan_iterations": plan_iterations
        },
        goto=goto,
    )

def reporter_node(state: State):
    """Wine Report Generator node that creates a formatted markdown table.
    
    Generates a markdown table with the following columns:
    Wine Name, Description, Vintage Year, Region, Country, User Rating,
    Price per Bottle, Estimated Quantity, Total Price"""
    logger.info("Reporter write final report")
    current_plan = state.get("current_plan")
    input_ = {
        "messages": [
            HumanMessage(
                f"# Research Requirements\n\n## Task\n\n{current_plan.title}\n\n## Description\n\n{current_plan.thought}"
            )
        ]
    }
    invoke_messages = apply_prompt_template("reporter", input_)
    observations = state.get("observations", [])

    # Add a reminder about the CSV format requirements
    invoke_messages.append(
        HumanMessage(
            content="IMPORTANT: Generate a markdown table with the following columns in order:\n\n"
                   "| Wine Name | Description | Vintage Year | Region | Country | "
                   "User Rating | Price per Bottle | Estimated Quantity | Total Price |\n"
                   "|-----------|-------------|--------------|--------|---------|-------------|"
                   "-----------------|-------------------|-------------|\n\n"
                   "Use '-' for any missing data, except vintage_year which should be 0.",
            name="system",
        )
    )

    for observation in observations:
        invoke_messages.append(
            HumanMessage(
                content=f"Below are some observations for the research task:\n\n{observation}",
                name="observation",
            )
        )
    logger.debug(f"Current invoke messages: {invoke_messages}")
    response = llm_model.invoke(invoke_messages)
    response_content = response.content
    logger.info(f"reporter response: {response_content}")

    return {"final_report": response_content}

def research_team_node(
    state: State,
) -> Command[Literal["planner", "researcher", "coder"]]:
    """Wine Research Team node that coordinates between:
    - Wine Data Retriever (researcher) for finding wines using wine_search
    - Python Calculator (coder) for quantity and cost calculations
    - Wine Event Planner (planner) for plan refinement"""
    logger.info("Research team is collaborating on tasks.")
    current_plan = state.get("current_plan")
    if not current_plan or not current_plan.steps:
        return Command(goto="planner")
    if all(step.execution_res and step.execution_res.strip() for step in current_plan.steps):
        return Command(goto="reporter")  # All steps are complete, go to reporter
    
    for step in current_plan.steps:
        if not step.execution_res:
            # Execute this step
            if step.step_type == StepType.RESEARCH:
                return Command(goto="researcher")
            else:
                return Command(goto="coder")

    return Command(goto="planner")


def _execute_agent_step(
    state: State, agent, agent_name: str
) -> Command[Literal["research_team"]]:
    """Helper function to execute a step using the specified agent."""
    current_plan = state.get("current_plan")
    observations = state.get("observations", [])

    # Find the first unexecuted step
    current_step = None
    completed_steps = []
    for step in current_plan.steps:
        if not step.execution_res:
            current_step = step
            break
        else:
            completed_steps.append(step)

    if not current_step:
        logger.warning("No unexecuted step found")
        return Command(goto="research_team")

    logger.info(f"Executing step: {current_step.title}, agent: {agent_name}")

    # Format completed steps information
    completed_steps_info = "# Existing Research Findings\n\n"
    if completed_steps:
        for i, step in enumerate(completed_steps):
            if step.execution_res and step.execution_res.strip():
                completed_steps_info += f"## Existing Finding {i + 1}: {step.title}\n\n"
                completed_steps_info += f"<finding>\n{step.execution_res}\n</finding>\n\n"
    else:
        # If no completed steps, still provide context about the task
        completed_steps_info += "No previous findings available. This is a standalone task.\n\n"

    # Prepare the input for the agent with completed steps info
    agent_input = {
        "messages": [
            HumanMessage(
                content=f"{completed_steps_info}# Current Task\n\n## Title\n\n{current_step.title}\n\n## Description\n\n{current_step.description}"
            )
        ]
    }

    # Invoke the agent
    default_recursion_limit = 25
    try:
        env_value_str = os.getenv("AGENT_RECURSION_LIMIT", str(default_recursion_limit))
        parsed_limit = int(env_value_str)

        if parsed_limit > 0:
            recursion_limit = parsed_limit
            logger.info(f"Recursion limit set to: {recursion_limit}")
        else:
            logger.warning(
                f"AGENT_RECURSION_LIMIT value '{env_value_str}' (parsed as {parsed_limit}) is not positive. "
                f"Using default value {default_recursion_limit}."
            )
            recursion_limit = default_recursion_limit
    except ValueError:
        raw_env_value = os.getenv("AGENT_RECURSION_LIMIT")
        logger.warning(
            f"Invalid AGENT_RECURSION_LIMIT value: '{raw_env_value}'. "
            f"Using default value {default_recursion_limit}."
        )
        recursion_limit = default_recursion_limit

    logger.info(f"Agent input: {agent_input}")
    result = agent.invoke(
        input=agent_input, config={"recursion_limit": recursion_limit}
    )

    # Process the result
    response_content = result["messages"][-1].content
    logger.debug(f"{agent_name.capitalize()} full response: {response_content}")

    # Only consider non-empty responses as valid execution results
    if response_content and response_content.strip():
        current_step.execution_res = response_content
        logger.info(f"Step '{current_step.title}' execution completed by {agent_name}")
    else:
        logger.warning(f"Empty response from {agent_name} for step '{current_step.title}'. Treating as incomplete.")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name=agent_name,
                )
            ],
            "observations": observations + [response_content],
        },
        goto="research_team",
    )



def _setup_and_execute_agent_step(
    state: State,
    config: RunnableConfig,
    agent_type: str,
    default_tools: list,
) -> Command[Literal["research_team"]]:
    """Helper function to set up an agent with appropriate tools and execute a step.

    This function handles the common logic for both researcher_node and coder_node:
    1. Creates an agent with the appropriate tools or uses the default agent
    2. Executes the agent on the current step

    Args:
        state: The current state
        agent_type: The type of agent ("researcher" or "coder")
        default_tools: The default tools to add to the agent

    Returns:
        Command to update state and go to research_team
    """
    # Use default tools if no MCP servers are configured
    agent = create_agent(agent_type, default_tools, agent_type)
    return _execute_agent_step(state, agent, agent_type)



def researcher_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Researcher node that do research"""
    logger.info("Researcher node is researching.")
    tools = [wine_search]
    logger.info(f"Researcher tools: {tools}")
    return _setup_and_execute_agent_step(
        state,
        config,
        "researcher",
        tools,
    )


def coder_node(
    state: State, config: RunnableConfig
) -> Command[Literal["research_team"]]:
    """Coder node that do code analysis."""
    logger.info("Coder node is coding.")
    return _setup_and_execute_agent_step(
        state,
        config,
        "coder",
        [python_repl_tool],
    )