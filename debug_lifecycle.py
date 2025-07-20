#!/usr/bin/env python3
"""
Debug Lifecycle Script for LM Studio + Graphiti Memory Integration

This script maps out the complete lifecycle of memory addition and provides
detailed logging for tools and tool usage to help diagnose issues.
"""

import requests
import json
import uuid
import re
import os
import time
from typing import Optional, Dict, Any, List
from datetime import datetime

class LifecycleDebugger:
    def __init__(self, lmstudio_url: str = "http://127.0.0.1:1234/v1/chat/completions", 
                 graphiti_url: str = "http://localhost:8000/sse",
                 model: str = "qwen3-32b"):
        self.lmstudio_url = lmstudio_url
        self.graphiti_url = graphiti_url
        self.model = model
        self.session_id = None
        self.debug_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Add a timestamped log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.debug_log.append(log_entry)
        
    def save_debug_log(self, filename: str = "debug_lifecycle.log"):
        """Save the debug log to a file"""
        with open(filename, 'w') as f:
            f.write('\n'.join(self.debug_log))
        self.log(f"Debug log saved to {filename}")
        
    def check_lmstudio_availability(self) -> bool:
        """Check if LM Studio is available and responding"""
        self.log("=== STEP 1: Checking LM Studio Availability ===")
        try:
            # Test basic connectivity
            self.log(f"Testing connection to LM Studio at: {self.lmstudio_url}")
            response = requests.get(self.lmstudio_url.replace('/v1/chat/completions', '/v1/models'), timeout=5)
            self.log(f"LM Studio models endpoint response: {response.status_code}")
            
            if response.status_code == 200:
                models = response.json()
                self.log(f"Available models: {[m.get('id', 'unknown') for m in models.get('data', [])]}")
                return True
            else:
                self.log(f"LM Studio not responding properly: {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"LM Studio connection failed: {e}", "ERROR")
            return False
            
    def check_graphiti_availability(self) -> bool:
        """Check if Graphiti server is available"""
        self.log("=== STEP 2: Checking Graphiti Server Availability ===")
        try:
            base_url = self.graphiti_url.replace('/sse', '')
            self.log(f"Testing connection to Graphiti at: {base_url}")
            
            # Test basic connectivity
            response = requests.get(base_url, timeout=5)
            self.log(f"Graphiti base endpoint response: {response.status_code}")
            
            # Test SSE endpoint
            sse_response = requests.get(self.graphiti_url, headers={"Accept": "text/event-stream"}, timeout=5)
            self.log(f"Graphiti SSE endpoint response: {sse_response.status_code}")
            
            return sse_response.status_code == 200
            
        except Exception as e:
            self.log(f"Graphiti connection failed: {e}", "ERROR")
            return False
            
    def discover_available_tools(self) -> List[Dict]:
        """Discover what tools are available on the Graphiti server"""
        self.log("=== STEP 3: Discovering Available Tools ===")
        try:
            # Get session first
            session_id = self.get_session()
            if not session_id:
                self.log("Cannot discover tools without session", "ERROR")
                return []
                
            # Try to list tools (this might not be available in all MCP implementations)
            base_url = self.graphiti_url.replace('/sse', '')
            messages_url = f"{base_url}/messages/?session_id={session_id}"
            
            # Try different tool discovery methods
            tool_discovery_methods = [
                {"method": "tools/list", "params": {}},
                {"method": "tools/list", "params": {"includeSchema": True}},
                {"method": "tools/list", "params": {"includeSchema": False}},
            ]
            
            for method_info in tool_discovery_methods:
                try:
                    request = {
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": method_info["method"],
                        "params": method_info["params"]
                    }
                    
                    self.log(f"Trying tool discovery method: {method_info['method']}")
                    response = requests.post(messages_url, json=request, headers={"Content-Type": "application/json"}, timeout=10)
                    self.log(f"Tool discovery response: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.log(f"Tool discovery result: {json.dumps(data, indent=2)}")
                        if "result" in data and "tools" in data["result"]:
                            tools = data["result"]["tools"]
                            self.log(f"Found {len(tools)} available tools:")
                            for tool in tools:
                                self.log(f"  - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')}")
                            return tools
                        else:
                            self.log(f"No tools found in response: {data}")
                    else:
                        self.log(f"Tool discovery failed with status {response.status_code}: {response.text}")
                        
                except Exception as e:
                    self.log(f"Tool discovery method {method_info['method']} failed: {e}")
                    
            self.log("All tool discovery methods failed", "WARNING")
            return []
            
        except Exception as e:
            self.log(f"Tool discovery failed: {e}", "ERROR")
            return []
            
    def get_session(self) -> Optional[str]:
        """Get a session ID from Graphiti server"""
        self.log("=== STEP 4: Getting MCP Session ===")
        try:
            if '/sse' in self.graphiti_url:
                sse_url = self.graphiti_url
            else:
                base_url = self.graphiti_url.replace('/sse', '')
                sse_url = f"{base_url}/sse"
            
            self.log(f"Requesting session from: {sse_url}")
            
            headers = {"Accept": "text/event-stream"}
            response = requests.get(sse_url, headers=headers, stream=True, timeout=10)
            
            if response.status_code != 200:
                self.log(f"Failed to connect to SSE endpoint: {response.status_code}", "ERROR")
                return None
            
            self.log("SSE connection established, parsing for session_id...")
            
            # Parse SSE stream for session_id
            for line in response.iter_lines():
                if b"session_id" in line:
                    self.log(f"Found session line: {line}")
                    match = re.search(rb'session_id=([a-f0-9]+)', line)
                    if match:
                        session_id = match.group(1).decode()
                        self.log(f"Extracted session_id: {session_id}")
                        self.session_id = session_id
                        return session_id
            
            self.log("Could not find session_id in SSE stream", "ERROR")
            return None
            
        except Exception as e:
            self.log(f"Failed to get MCP session: {e}", "ERROR")
            return None
            
    def test_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Test calling a specific tool"""
        self.log(f"=== STEP 5: Testing Tool Call - {tool_name} ===")
        try:
            if not self.session_id:
                self.log("No session ID available", "ERROR")
                return {"error": "No session ID"}
                
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
            
            headers = {"Content-Type": "application/json"}
            base_url = self.graphiti_url.replace('/sse', '')
            messages_url = f"{base_url}/messages/?session_id={self.session_id}"
            
            self.log(f"Tool call details:")
            self.log(f"  URL: {messages_url}")
            self.log(f"  Tool: {tool_name}")
            self.log(f"  Arguments: {json.dumps(arguments, indent=2)}")
            self.log(f"  Full Request: {json.dumps(tool_call_request, indent=2)}")
            
            start_time = time.time()
            response = requests.post(messages_url, json=tool_call_request, headers=headers, timeout=30)
            end_time = time.time()
            
            self.log(f"Tool call response:")
            self.log(f"  Status: {response.status_code}")
            self.log(f"  Time: {end_time - start_time:.2f}s")
            self.log(f"  Headers: {dict(response.headers)}")
            self.log(f"  Body: {response.text}")
            
            if response.status_code == 202:
                self.log("Server accepted the event (202). Memory addition is queued.")
                return {"success": True, "message": "Memory addition request accepted", "status": 202}
            else:
                try:
                    data = response.json()
                    if "error" in data:
                        self.log(f"Server returned error: {data['error']}", "ERROR")
                        return {"error": data['error']}
                    else:
                        self.log(f"Server returned data: {data}")
                        return data
                except json.JSONDecodeError:
                    self.log(f"Could not decode server response as JSON: {response.text}", "ERROR")
                    return {"error": f"Unexpected response: {response.text}"}
                    
        except Exception as e:
            self.log(f"Tool call failed: {e}", "ERROR")
            return {"error": str(e)}
            
    def test_lmstudio_tool_calling(self, test_prompt: str) -> Dict[str, Any]:
        """Test LM Studio's tool calling capabilities"""
        self.log("=== STEP 6: Testing LM Studio Tool Calling ===")
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
                "model": self.model,
                "messages": [{"role": "user", "content": test_prompt}],
                "tools": tools,
                "stream": False
            }
            
            self.log(f"LM Studio request:")
            self.log(f"  URL: {self.lmstudio_url}")
            self.log(f"  Model: {self.model}")
            self.log(f"  Prompt: {test_prompt}")
            self.log(f"  Tools: {json.dumps(tools, indent=2)}")
            
            start_time = time.time()
            response = requests.post(self.lmstudio_url, json=payload, headers={"Content-Type": "application/json"}, timeout=600)
            end_time = time.time()
            
            self.log(f"LM Studio response:")
            self.log(f"  Status: {response.status_code}")
            self.log(f"  Time: {end_time - start_time:.2f}s")
            
            response.raise_for_status()
            data = response.json()
            
            self.log(f"LM Studio response data: {json.dumps(data, indent=2)}")
            
            if data["choices"][0]["message"].get("tool_calls"):
                tool_call = data["choices"][0]["message"]["tool_calls"][0]
                self.log(f"Model requested tool call: {tool_call['function']['name']}")
                self.log(f"Tool call arguments: {tool_call['function']['arguments']}")
                
                try:
                    arguments = json.loads(tool_call['function']['arguments'])
                    return {
                        "success": True,
                        "tool_call": tool_call,
                        "arguments": arguments,
                        "raw_response": data
                    }
                except json.JSONDecodeError as e:
                    return {"error": f"Failed to parse tool call arguments: {e}"}
            else:
                return {
                    "success": False,
                    "message": "No tool call requested",
                    "content": data["choices"][0]["message"]["content"],
                    "raw_response": data
                }
                
        except Exception as e:
            self.log(f"LM Studio tool calling failed: {e}", "ERROR")
            return {"error": str(e)}
            
    def run_full_lifecycle_test(self, test_file_path: str = None):
        """Run the complete lifecycle test"""
        self.log("=== STARTING FULL LIFECYCLE TEST ===")
        
        # Step 1: Check LM Studio availability
        if not self.check_lmstudio_availability():
            self.log("LM Studio not available - stopping test", "ERROR")
            return
            
        # Step 2: Check Graphiti availability
        if not self.check_graphiti_availability():
            self.log("Graphiti server not available - stopping test", "ERROR")
            return
            
        # Step 3: Discover available tools
        tools = self.discover_available_tools()
        if not tools:
            self.log("No tools discovered - this might be normal for some MCP implementations", "WARNING")
            
        # Step 4: Get session
        session_id = self.get_session()
        if not session_id:
            self.log("Failed to get session - stopping test", "ERROR")
            return
            
        # Step 5: Test direct tool call
        test_args = {
            "name": "test_memory",
            "episode_body": "This is a test memory created during lifecycle debugging."
        }
        tool_result = self.test_tool_call("add_memory", test_args)
        self.log(f"Direct tool call result: {tool_result}")
        
        # Step 6: Test LM Studio tool calling
        if test_file_path and os.path.exists(test_file_path):
            with open(test_file_path, 'r', encoding='utf-8') as f:
                content = f.read()[:1000]  # Limit content
            test_prompt = f"Please add a memory with the name '{test_file_path}' and the following content: '{content[:200]}...'"
        else:
            test_prompt = "Please add a memory with the name 'test_lifecycle' and the content 'This is a test memory from the lifecycle debugger.'"
            
        lmstudio_result = self.test_lmstudio_tool_calling(test_prompt)
        self.log(f"LM Studio tool calling result: {lmstudio_result}")
        
        # Step 7: If LM Studio requested a tool call, execute it
        if lmstudio_result.get("success") and "arguments" in lmstudio_result:
            self.log("=== STEP 7: Executing LM Studio Tool Call ===")
            arguments = lmstudio_result["arguments"]
            name = arguments.get('name')
            episode_body = arguments.get('episode_body')
            
            if name and episode_body:
                final_result = self.test_tool_call("add_memory", {
                    "name": name,
                    "episode_body": episode_body
                })
                self.log(f"Final tool execution result: {final_result}")
            else:
                self.log("Missing required arguments from LM Studio", "ERROR")
        
        self.log("=== LIFECYCLE TEST COMPLETE ===")
        self.save_debug_log()

def main():
    """Main function to run the lifecycle debugger"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Debug the LM Studio + Graphiti memory lifecycle")
    parser.add_argument('--lmstudio-url', default="http://127.0.0.1:1234/v1/chat/completions", 
                       help="LM Studio API URL")
    parser.add_argument('--graphiti-url', default="http://localhost:8000/sse", 
                       help="Graphiti server URL")
    parser.add_argument('--model', default="qwen3-32b", 
                       help="Model to use")
    parser.add_argument('--test-file', 
                       help="Optional test file to use in the lifecycle test")
    
    args = parser.parse_args()
    
    debugger = LifecycleDebugger(
        lmstudio_url=args.lmstudio_url,
        graphiti_url=args.graphiti_url,
        model=args.model
    )
    
    debugger.run_full_lifecycle_test(args.test_file)

if __name__ == "__main__":
    main() 