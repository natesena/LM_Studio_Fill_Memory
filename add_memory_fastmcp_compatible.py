#!/usr/bin/env python3
"""
FastMCP-compatible memory addition script.
This implementation works with FastMCP's SSE design where:
1. SSE connections are short-lived and only used to get session_id
2. Tool calls are made via POST requests to /messages/?session_id=<id>
3. ClosedResourceError is expected and handled gracefully
"""

import requests
import json
import uuid
import sys
import logging
import http.client
from typing import Optional, Dict, Any

# -------------------------
# Debug / logging toggles
# -------------------------
DEBUG_HTTP = "--debug-http" in sys.argv
if DEBUG_HTTP:
    # Remove the flag so argparse in downstream code (if any) doesn't choke
    sys.argv.remove("--debug-http")
    http.client.HTTPConnection.debuglevel = 1  # show raw request/response
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3").setLevel(logging.DEBUG)
    logging.getLogger("requests").setLevel(logging.DEBUG)


class FastMcpClient:
    """FastMCP-compatible client that works with the server's SSE design."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.sse_url = f"{self.base_url}/sse"
        self.messages_url = f"{self.base_url}/messages"
    
    def get_session_id(self) -> str:
        """Get a session ID via SSE connection (short-lived)."""
        print(f"[FASTMCP] Getting session ID from {self.sse_url}")
        
        try:
            response = requests.get(
                self.sse_url,
                headers={
                    "Accept": "text/event-stream",
                    "Connection": "keep-alive"
                },
                stream=True,
                timeout=10
            )
            response.raise_for_status()
            
            # Read the first line to get session_id
            for line in response.iter_lines():
                if b"session_id=" in line:
                    session_id = line.split(b"session_id=")[1].decode()
                    print(f"[FASTMCP] Acquired session_id: {session_id}")
                    # Close the connection immediately - this is expected behavior
                    response.close()
                    return session_id
            
            raise Exception("No session_id found in SSE response")
            
        except Exception as e:
            print(f"[FASTMCP] Error getting session ID: {e}")
            raise
    
    def call_tool(self, session_id: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool using the session ID via POST request."""
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        
        url = f"{self.messages_url}/?session_id={session_id}"
        print(f"[FASTMCP] Calling tool {tool_name} at {url}")
        print(f"[FASTMCP] Arguments: {json.dumps(arguments, indent=2)}")
        
        try:
            response = requests.post(
                url,
                json=tool_call_request,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            print(f"[FASTMCP] Response status: {response.status_code}")
            print(f"[FASTMCP] Response body: {response.text}")
            
            # FastMCP returns 202 Accepted for successful tool calls
            if response.status_code == 202:
                print("[FASTMCP] Tool call accepted (202) - memory queued for processing")
                return {
                    "success": True, 
                    "message": "Memory addition request accepted and queued for processing"
                }
            else:
                response.raise_for_status()
                try:
                    return response.json()
                except json.JSONDecodeError:
                    return {"success": False, "message": response.text}
                    
        except requests.exceptions.RequestException as e:
            print(f"[FASTMCP] Error calling tool: {e}")
            raise
    
    def add_memory(self, name: str, episode_body: str, group_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a memory episode using FastMCP protocol."""
        print(f"[FASTMCP] Adding memory: {name}")
        
        # Get a fresh session ID for this operation
        session_id = self.get_session_id()
        
        # Prepare tool arguments
        arguments = {
            "name": name,
            "episode_body": episode_body
        }
        if group_id:
            arguments["group_id"] = group_id
        
        # Call the add_memory tool
        return self.call_tool(session_id, "add_memory", arguments)


def add_memory_via_fastmcp(
    prompt: str, 
    lmstudio_url: str = "http://127.0.0.1:1234/v1/chat/completions",
    graphiti_url: str = "http://localhost:8000",
    model: str = "qwen3-32b"
) -> str:
    """
    Add memory using LM Studio's chat completion API with tool calling, 
    using FastMCP-compatible protocol.
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
        print(f"[LMSTUDIO] Sending request: {prompt}")
        
        response = requests.post(lmstudio_url, json=payload, headers=headers, timeout=600)
        response.raise_for_status()
        data = response.json()
        
        if data["choices"][0]["message"].get("tool_calls"):
            tool_call = data["choices"][0]["message"]["tool_calls"][0]
            print(f"[LMSTUDIO] Model requested tool call: {tool_call['function']['name']}")
            
            try:
                arguments = json.loads(tool_call['function']['arguments'])
                name = arguments.get('name')
                episode_body = arguments.get('episode_body')
                
                if not name or not episode_body:
                    return "Error: Missing required arguments 'name' or 'episode_body'"
                
                print(f"[LMSTUDIO] Parsed arguments - name: {name}")
                
                # Use FastMCP client to add memory
                client = FastMcpClient(graphiti_url)
                result = client.add_memory(name, episode_body)
                
                print(f"[LMSTUDIO] FastMCP result: {result}")
                
                # Send final request to LM Studio with tool result
                final_payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": None, "tool_calls": [tool_call]},
                        {"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call["id"]}
                    ],
                    "stream": False
                }
                
                print("[LMSTUDIO] Sending final request with tool result...")
                final_response = requests.post(lmstudio_url, json=final_payload, headers=headers, timeout=600)
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


def test_fastmcp_compatibility():
    """Test the FastMCP-compatible implementation."""
    print("=== Testing FastMCP Compatibility ===")
    
    client = FastMcpClient()
    
    # Test 1: Get session ID
    print("\n1. Testing session ID acquisition...")
    try:
        session_id = client.get_session_id()
        print(f"   ✓ Session ID acquired: {session_id}")
    except Exception as e:
        print(f"   ✗ Failed to get session ID: {e}")
        return False
    
    # Test 2: Add memory
    print("\n2. Testing memory addition...")
    test_args = {
        "name": "FastMCP Compatibility Test",
        "episode_body": "This is a test memory to verify that the FastMCP-compatible implementation works correctly with the server's SSE design."
    }
    
    try:
        result = client.call_tool(session_id, "add_memory", test_args)
        print(f"   ✓ Memory addition result: {result}")
        return True
    except Exception as e:
        print(f"   ✗ Memory addition failed: {e}")
        return False


if __name__ == "__main__":
    print("FastMCP-Compatible Memory Addition")
    print("==================================")
    
    # Test the implementation
    if test_fastmcp_compatibility():
        print("\n✓ FastMCP compatibility test passed!")
        
        # Run the full LM Studio integration
        test_prompt = "Please add a memory about the FastMCP compatibility discovery we made. We discovered that FastMCP's SSE implementation is designed for short-lived connections that only serve to provide session IDs. The server expects clients to close the SSE connection after getting the session_id, then use that session_id for subsequent POST requests to /messages/?session_id=<id>. The ClosedResourceError we were seeing is actually expected behavior when the server tries to write responses back to the closed SSE connection. This is why our persistent connection approach wasn't working - we need to work with FastMCP's design rather than against it."
        
        print(f"\n=== Testing Full LM Studio Integration ===")
        result = add_memory_via_fastmcp(test_prompt)
        print(f"\n=== Result ===")
        print(result)
    else:
        print("\n✗ FastMCP compatibility test failed!")
        sys.exit(1) 