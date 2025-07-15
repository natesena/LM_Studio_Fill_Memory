# add_memory.py
"""
Defines the add_memory tool schema and Python functions to interact with MCP servers using LM Studio's chat completion API.
"""
import requests
from typing import Optional

def add_memory_via_lmstudio(name: str, episode_body: str, lmstudio_url: str = "http://127.0.0.1:1234/v1", model: str = "qwen3-32b") -> str:
    """
    Add memory using LM Studio's chat completion API with tool calling.
    Args:
        name: The name of the memory episode.
        episode_body: The content to store in memory.
        lmstudio_url: The LM Studio API URL (default: local LM Studio).
        model: The model name to use.
    Returns:
        The result as a string.
    """
    try:
        # Define the add_memory tool for LM Studio
        tools = [{
            "type": "function",
            "function": {
                "name": "add_memory",
                "description": "Add a memory episode to the MCP server.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "The name of the memory episode."},
                        "episode_body": {"type": "string", "description": "The content to store in memory."}
                    },
                    "required": ["name", "episode_body"]
                }
            }
        }]
        
        # Create the chat completion request
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": f"Please add a memory with name '{name}' and content '{episode_body}'"}
            ],
            "tools": tools,
            "stream": False
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Send request to LM Studio
        response = requests.post(f"{lmstudio_url}/chat/completions", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        # Check if the model wants to call the tool
        if data["choices"][0]["message"].get("tool_calls"):
            tool_call = data["choices"][0]["message"]["tool_calls"][0]
            print(f"Model requested tool call: {tool_call['function']['name']}")
            
            # Here you would execute the actual tool call to your MCP server
            # For now, we'll just return the tool call info
            return f"Tool call requested: {tool_call['function']['name']} with args: {tool_call['function']['arguments']}"
        else:
            return f"Model response: {data['choices'][0]['message']['content']}"
        
    except Exception as exc:
        return f"Error calling add_memory via LM Studio: {exc}"

# OpenAI function-calling schema for LM Studio add_memory tool
add_memory_schema = {
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