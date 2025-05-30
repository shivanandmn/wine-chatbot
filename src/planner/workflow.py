from dotenv import load_dotenv
load_dotenv()
from graph import build_graph_with_memory
import logging
from memory_agent.utils import save_graph_image
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


logger = logging.getLogger(__name__)

graph = build_graph_with_memory()

def run_agent_workflow(user_input: str, max_plan_iterations: int = 1, max_step_num: int = 3):
    initial_state = {
        "messages": [{"role": "user", "content": user_input}]
    }
    config = {
        "configurable": {
            "thread_id": "default",
            "max_plan_iterations": max_plan_iterations,
            "max_step_num": max_step_num,
        },
        "recursion_limit":10
    }
    last_message_cnt = 0
    for s in graph.stream(initial_state, config=config, stream_mode="values"):
        try:
            if isinstance(s, dict) and "messages" in s:
                if len(s["messages"]) <= last_message_cnt:
                    continue
                last_message_cnt = len(s["messages"])
                message = s["messages"][-1]
                if isinstance(message, tuple):
                    print(message)
                else:
                    message.pretty_print()
            else:
                # For any other output format
                print(f"Output: {s}")
        except Exception as e:
            logger.error(f"Error processing stream output: {e}")
            print(f"Error processing output: {str(e)}")

    logger.info("Workflow completed successfully")


def run_terminal_conversation(initial_input: str, thread_id: str = "cli_conversation_2"):
    """Runs a continuous conversation with the memory_agent graph via the terminal."""
    logger.info(f"Starting terminal conversation with thread_id: {thread_id}")
    
    config = {
        "configurable": {
            "thread_id": thread_id,
            "max_plan_iterations": 2,
            "max_step_num": 5
        },
        "recursion_limit": 25
    }
    
    # Initialize message history
    message_history = []
    current_input = initial_input

    while True:
        if not current_input.strip():
            current_input = input("User: ")
            if not current_input.strip():
                continue

        try:
            # Create a human message
            human_message = HumanMessage(content=current_input)
            logger.debug(f"Sending message to graph: {human_message}")
            
            # Pass the message to the graph
            output = graph.invoke({"messages": [human_message]}, config=config)
            logger.debug(f"Received output from graph: {output}")

            if output and isinstance(output, dict) and 'messages' in output:
                messages = output['messages']
                logger.debug(f"Messages in output: {messages}")
                
                # Find the last response message
                response = None
                for msg in reversed(messages):
                    logger.debug(f"Processing message: {type(msg)} - {msg}")
                    
                    if hasattr(msg, 'content'):
                        # Check if it's a direct string response from coordinator
                        if isinstance(msg, str):
                            response = msg
                            print(f"\nAssistant: {response}")
                            break
                        # Check if it's an AIMessage
                        elif isinstance(msg, AIMessage):
                            response = msg.content
                            print(f"\nAssistant: {response}")
                            break
                        # Check if it's a ToolMessage
                        elif isinstance(msg, ToolMessage):
                            print(f"\nTool Output ({msg.name}): {msg.content}")
                            break
                        # Check content directly from response object
                        elif hasattr(msg, 'content') and msg.content:
                            response = msg.content
                            print(f"\nAssistant: {response}")
                            break
                
                if not response:
                    logger.warning("No suitable response message found in output")
                    print("\nAssistant: I'm having trouble formulating a response.")
            else:
                logger.warning(f"Unexpected output format: {output}")
                print("\nAssistant: (No response)")
        
        except Exception as e:
            logger.error(f"Error during graph.invoke: {e}", exc_info=True)
            print(f"\nError communicating with the assistant: {e}")

        # Get next input
        user_next_input = input("\nUser: ")
        if user_next_input.lower() in ["exit", "quit"]:
            logger.info("Exiting terminal conversation.")
            print("Exiting conversation.")
            break
        current_input = user_next_input

if __name__ == "__main__":
    # To run the planner workflow (existing):
    # run_agent_workflow("What is the best wine for a dinner party?")

    # To run the new terminal conversation with the memory_agent graph:
    print("Starting VinoVoss Chatbot (type 'exit' or 'quit' to end)...")
    run_terminal_conversation(initial_input="red wine, for birthday party, 5 guests, each guest will have 2 bottles, budget under $500, steak ribeye")

    # save_graph_image(graph, save="./results/planner_graph.png")
    # print(graph.get_graph(xray=True).draw_mermaid())
    # run_agent_workflow("What is the best wine for a dinner party?")