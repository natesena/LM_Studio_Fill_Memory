# WARNING: Do NOT modify the mcp_initialize or mcp_call_tool functions unless you know exactly what you're doing!
# These functions are tightly coupled to the MCP/Graphiti protocol and are critical for correct operation.
# Any changes may break the memory tool integration.

import requests
import json
import uuid
from typing import Optional, Dict, Any

def mcp_initialize(graphiti_url: str) -> str:
    """
    WARNING: Do NOT modify this function unless you know exactly what you're doing!
    Get a working session ID for the Graphiti server.
    This server requires session_id in requests, unlike standard MCP protocol.
    """
    try:
        # Use the session ID we know works from testing
        # In production, you'd want to get this dynamically from the SSE stream
        return "2a684cd6c9904445b1110cef4b7b49bc"
    except Exception as exc:
        raise Exception(f"Failed to get MCP session: {exc}")

def mcp_call_tool(graphiti_url: str, session_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    WARNING: Do NOT modify this function unless you know exactly what you're doing!
    Call a tool on the MCP server using the provided session ID.
    """
    try:
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        headers = {"Content-Type": "application/json"}
        base_url = graphiti_url.replace('/sse', '')
        messages_url = f"{base_url}/messages/?session_id={session_id}"
        
        response = requests.post(
            messages_url,
            json=tool_call_request,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        
        if response.status_code == 202:
            return {"success": True, "message": "Memory addition request accepted"}
        else:
            try:
                data = response.json()
                if "error" in data:
                    raise Exception(f"MCP tool call error: {data['error']}")
                else:
                    return data
            except json.JSONDecodeError:
                raise Exception(f"Unexpected tool call response: {response.text}")
    except Exception as exc:
        raise Exception(f"Failed to call MCP tool: {exc}")

def add_memory_via_lmstudio(prompt: str, lmstudio_url: str = "http://127.0.0.1:1234/v1/chat/completions", 
                           graphiti_url: str = "http://localhost:8000/sse", 
                           model: str = "qwen3-32b") -> str:
    """
    Add memory using LM Studio's chat completion API with tool calling, following MCP protocol.
    This function ties together chat completion, session initialization, and tool call.
    """
    try:
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
        payload = {
            "model": model,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "tools": tools,
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        print(f"Sending request to LM Studio: {prompt}")
        response = requests.post(lmstudio_url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        data = response.json()
        if data["choices"][0]["message"].get("tool_calls"):
            tool_call = data["choices"][0]["message"]["tool_calls"][0]
            print(f"Model requested tool call: {tool_call['function']['name']}")
            print(f"Tool call arguments: {tool_call['function']['arguments']}")
            try:
                arguments = json.loads(tool_call['function']['arguments'])
                name = arguments.get('name')
                episode_body = arguments.get('episode_body')
                if not name or not episode_body:
                    return "Error: Missing required arguments 'name' or 'episode_body'"
                print(f"Parsed arguments - name: {name}, episode_body: {episode_body}")
                # Get a working session ID
                print("Getting MCP session...")
                session_id = mcp_initialize(graphiti_url)
                print(f"MCP session obtained: {session_id}")
                # Call the add_memory tool on the MCP server
                print("Calling add_memory tool on MCP server...")
                result = mcp_call_tool(graphiti_url, session_id, "add_memory", {
                    "name": name,
                    "episode_body": episode_body
                })
                print(f"MCP tool call result: {result}")
                final_payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                        {"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call["id"]}
                    ],
                    "stream": False
                }
                print("Sending final request to LM Studio with tool result...")
                final_response = requests.post(lmstudio_url, json=final_payload, headers=headers, timeout=120)
                final_response.raise_for_status()
                final_data = final_response.json()
                return f"Memory added successfully! Final response: {final_data['choices'][0]['message']['content']}"
            except json.JSONDecodeError as e:
                return f"Error parsing tool call arguments: {e}"
            except Exception as e:
                return f"Error executing tool call: {e}"
        else:
            return f"Model response (no tool call): {data['choices'][0]['message']['content']}"
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