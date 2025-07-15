# lmstudio_add_memory_tool.py
"""
Defines the add_memory tool schema and a Python function to call the Graphiti server's add_memory endpoint.
"""
import requests

def add_memory(name: str, episode_body: str, graphiti_url: str = "http://localhost:8000/add_memory") -> str:
    """
    Calls the Graphiti server's add_memory endpoint.
    Args:
        name: The name of the memory episode.
        episode_body: The content to store in memory.
        graphiti_url: The endpoint for add_memory (default: local Graphiti).
    Returns:
        The server's response as a string (success or error message).
    """
    payload = {
        "name": name,
        "episode_body": episode_body,
    }
    try:
        resp = requests.post(graphiti_url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        return f"Error calling add_memory: {exc}"

# OpenAI function-calling schema for LM Studio add_memory tool
add_memory_tool_schema = {
    "type": "function",
    "function": {
        "name": "add_memory",
        "description": "Add a memory episode to the remote Graphiti server.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "The name of the memory episode."},
                "episode_body": {"type": "string", "description": "The content to store in memory."}
            },
            "required": ["name", "episode_body"]
        }
    }
} 