"""Utility functions used in our graph."""

import os
from typing import Any, Union
from langgraph.graph import StateGraph

def split_model_and_provider(fully_specified_name: str) -> dict:
    """Initialize the configured chat model."""
    if "/" in fully_specified_name:
        provider, model = fully_specified_name.split("/", maxsplit=1)
    else:
        provider = None
        model = fully_specified_name
    return {"model": model, "provider": provider}


def save_graph_image(graph: StateGraph, save="./results/graph_output.png"):
    png_data = graph.get_graph().draw_mermaid_png()
    os.makedirs(os.path.dirname(save), exist_ok=True)
    with open(save, "wb") as f:
        f.write(png_data)
    print(f"Saved to {save}")


def format_data_to_string(data: Union[dict, list, Any], indent: int = 0) -> str:
    """Format a dictionary or list into a readable string representation.
    
    Args:
        data: The input data structure (dictionary, list, or any other type)
        indent: The current indentation level (used for recursion)
    
    Returns:
        A formatted string representation of the data structure
    """
    indent_str = '    ' * indent
    result = []
    
    if isinstance(data, dict):
        if not data:
            return f"{indent_str}{{}}"
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                result.append(f"{indent_str}{key} :")
                result.append(format_data_to_string(value, indent + 1))
            else:
                result.append(f"{indent_str}{key} : {value}")
    elif isinstance(data, list):
        if not data:
            return f"{indent_str}[]"
        for item in data:
            if isinstance(item, (dict, list)):
                result.append(format_data_to_string(item, indent))
            else:
                result.append(f"{indent_str}{item}")
    else:
        return f"{indent_str}{data}"
    
    return "\n".join(result)