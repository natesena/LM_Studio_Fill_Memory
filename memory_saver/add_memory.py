# add_memory.py
import requests

def add_memory_via_lmstudio(name, episode_body, lmstudio_url="http://127.0.0.1:1234/v1", model="qwen3-32b"):
    """Add memory using LM Studio chat completion API with tool calling."""
    try:
        tools = [{"type": "function", "function": {"name": "add_memory", "description": "Add memory", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "episode_body": {"type": "string"}}, "required": ["name", "episode_body"]}}}]
        payload = {"model": model, "messages": [{"role": "user", "content": f"Add memory: {name} - {episode_body}"}], "tools": tools, "stream": False}
        response = requests.post(f"{lmstudio_url}/chat/completions", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        if data["choices"][0]["message"].get("tool_calls"):
            tool_call = data["choices"][0]["message"]["tool_calls"][0]
            func_name = tool_call["function"]["name"]
            func_args = tool_call["function"]["arguments"]
            return f"Tool call: {func_name} with args: {func_args}"
        else:
            return f"Response: {data[choices][0][message][content]}"
    except Exception as exc:
        return f"Error: {exc}"

add_memory_schema = {"type": "function", "function": {"name": "add_memory", "description": "Add memory", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "episode_body": {"type": "string"}}, "required": ["name", "episode_body"]}}}
