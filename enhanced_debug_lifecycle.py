#!/usr/bin/env python3
"""
Enhanced Debug Lifecycle Script for LM Studio + Graphiti Memory Integration

This script specifically addresses the asynchronous processing nature of the Graphiti MCP server
and provides detailed debugging for the background processing pipeline.
"""

import requests
import json
import uuid
import re
import os
import time
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime

class EnhancedLifecycleDebugger:
    def __init__(self, lmstudio_url: str = "http://127.0.0.1:1234/v1/chat/completions", 
                 graphiti_url: str = "http://localhost:8000/sse",
                 model: str = "qwen3-32b"):
        self.lmstudio_url = lmstudio_url
        self.graphiti_url = graphiti_url
        self.model = model
        self.session_id = None
        self.debug_log = []
        self.test_memories = []
        
    def log(self, message: str, level: str = "INFO"):
        """Add a timestamped log entry"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level}] {message}"
        print(log_entry)
        self.debug_log.append(log_entry)
        
    def save_debug_log(self, filename: str = "enhanced_debug_lifecycle.log"):
        """Save the debug log to a file"""
        with open(filename, 'w') as f:
            f.write('\n'.join(self.debug_log))
        self.log(f"Debug log saved to {filename}")
        
    def check_lmstudio_availability(self) -> bool:
        """Check if LM Studio is available and responding"""
        self.log("=== STEP 1: Checking LM Studio Availability ===")
        try:
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
            
            # Test base endpoint
            response = requests.get(base_url, timeout=5)
            self.log(f"Graphiti base endpoint response: {response.status_code}")
            
            # Test SSE endpoint
            sse_response = requests.get(self.graphiti_url, headers={"Accept": "text/event-stream"}, timeout=5)
            self.log(f"Graphiti SSE endpoint response: {sse_response.status_code}")
            
            # Test status endpoint
            status_response = requests.get(f"{base_url}/status", timeout=5)
            self.log(f"Graphiti status endpoint response: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                self.log(f"Graphiti status: {status_data}")
            
            return sse_response.status_code == 200
            
        except Exception as e:
            self.log(f"Graphiti connection failed: {e}", "ERROR")
            return False
            
    def get_session(self) -> Optional[str]:
        """Get a session ID from Graphiti server"""
        self.log("=== STEP 3: Getting MCP Session ===")
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
            
    def test_direct_memory_addition(self, test_name: str, test_content: str, group_id: str = None) -> Dict[str, Any]:
        """Test direct memory addition and track the result"""
        self.log(f"=== STEP 4: Testing Direct Memory Addition - {test_name} ===")
        try:
            if not self.session_id:
                self.log("No session ID available", "ERROR")
                return {"error": "No session ID"}
                
            tool_call_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "add_memory",
                    "arguments": {
                        "name": test_name,
                        "episode_body": test_content,
                        "group_id": group_id
                    }
                }
            }
            
            headers = {"Content-Type": "application/json"}
            base_url = self.graphiti_url.replace('/sse', '')
            messages_url = f"{base_url}/messages/?session_id={self.session_id}"
            
            self.log(f"Tool call details:")
            self.log(f"  URL: {messages_url}")
            self.log(f"  Tool: add_memory")
            self.log(f"  Arguments: {json.dumps(tool_call_request['params']['arguments'], indent=2)}")
            
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
                # Store test memory info for later verification
                self.test_memories.append({
                    "name": test_name,
                    "content": test_content,
                    "group_id": group_id,
                    "timestamp": datetime.now().isoformat(),
                    "response": response.text
                })
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
            
    def wait_for_background_processing(self, wait_time: int = 30) -> None:
        """Wait for background processing to complete"""
        self.log(f"=== STEP 5: Waiting for Background Processing ({wait_time}s) ===")
        self.log("The Graphiti MCP server processes memories asynchronously.")
        self.log("We need to wait for the background worker to process the queued episodes.")
        
        for i in range(wait_time):
            remaining = wait_time - i
            self.log(f"Waiting for background processing... {remaining}s remaining")
            time.sleep(1)
            
        self.log("Background processing wait completed.")
        
    def verify_memory_in_neo4j(self, search_terms: List[str] = None) -> Dict[str, Any]:
        """Verify if memories were actually stored in Neo4j"""
        self.log("=== STEP 6: Verifying Memory Storage in Neo4j ===")
        
        if not search_terms:
            # Use test memory names as search terms
            search_terms = [memory["name"] for memory in self.test_memories]
            
        try:
            base_url = self.graphiti_url.replace('/sse', '')
            
            # Test Neo4j connectivity through Graphiti
            status_response = requests.get(f"{base_url}/status", timeout=10)
            self.log(f"Graphiti status check: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.json()
                self.log(f"Graphiti status: {status_data}")
            
            # Try to search for the memories we added
            for term in search_terms:
                self.log(f"Searching for memory: {term}")
                
                # Use the search_memory_nodes tool to find our memories
                search_request = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "tools/call",
                    "params": {
                        "name": "search_memory_nodes",
                        "arguments": {
                            "query": term,
                            "max_nodes": 10
                        }
                    }
                }
                
                if self.session_id:
                    messages_url = f"{base_url}/messages/?session_id={self.session_id}"
                    response = requests.post(messages_url, json=search_request, headers={"Content-Type": "application/json"}, timeout=30)
                    
                    self.log(f"Search response for '{term}': {response.status_code}")
                    if response.status_code == 200:
                        try:
                            search_data = response.json()
                            self.log(f"Search results for '{term}': {json.dumps(search_data, indent=2)}")
                        except json.JSONDecodeError:
                            self.log(f"Could not decode search response: {response.text}")
                    else:
                        self.log(f"Search failed for '{term}': {response.text}")
                        
        except Exception as e:
            self.log(f"Neo4j verification failed: {e}", "ERROR")
            return {"error": str(e)}
            
        return {"success": True, "message": "Verification completed"}
        
    def test_episode_retrieval(self) -> Dict[str, Any]:
        """Test retrieving episodes to see if they were stored"""
        self.log("=== STEP 7: Testing Episode Retrieval ===")
        
        try:
            if not self.session_id:
                return {"error": "No session ID"}
                
            base_url = self.graphiti_url.replace('/sse', '')
            messages_url = f"{base_url}/messages/?session_id={self.session_id}"
            
            # Try to get recent episodes
            get_episodes_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/call",
                "params": {
                    "name": "get_episodes",
                    "arguments": {
                        "last_n": 10
                    }
                }
            }
            
            response = requests.post(messages_url, json=get_episodes_request, headers={"Content-Type": "application/json"}, timeout=30)
            
            self.log(f"Get episodes response: {response.status_code}")
            if response.status_code == 200:
                try:
                    episodes_data = response.json()
                    self.log(f"Recent episodes: {json.dumps(episodes_data, indent=2)}")
                    
                    # Check if our test memories are in the episodes
                    if "result" in episodes_data:
                        episodes = episodes_data["result"]
                        self.log(f"Found {len(episodes)} recent episodes")
                        
                        for memory in self.test_memories:
                            found = False
                            for episode in episodes:
                                if episode.get("name") == memory["name"]:
                                    self.log(f"✅ Found test memory '{memory['name']}' in episodes")
                                    found = True
                                    break
                            if not found:
                                self.log(f"❌ Test memory '{memory['name']}' NOT found in episodes")
                                
                    return episodes_data
                except json.JSONDecodeError:
                    self.log(f"Could not decode episodes response: {response.text}")
                    return {"error": "Invalid JSON response"}
            else:
                self.log(f"Get episodes failed: {response.text}")
                return {"error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            self.log(f"Episode retrieval test failed: {e}", "ERROR")
            return {"error": str(e)}
            
    def run_enhanced_lifecycle_test(self, wait_time: int = 30):
        """Run the complete enhanced lifecycle test"""
        self.log("=== STARTING ENHANCED LIFECYCLE TEST ===")
        self.log("This test specifically addresses the asynchronous processing of the Graphiti MCP server.")
        
        # Step 1: Check LM Studio availability
        if not self.check_lmstudio_availability():
            self.log("LM Studio not available - stopping test", "ERROR")
            return
            
        # Step 2: Check Graphiti availability
        if not self.check_graphiti_availability():
            self.log("Graphiti server not available - stopping test", "ERROR")
            return
            
        # Step 3: Get session
        session_id = self.get_session()
        if not session_id:
            self.log("Failed to get session - stopping test", "ERROR")
            return
            
        # Step 4: Test multiple memory additions
        test_memories = [
            {
                "name": "test_memory_1",
                "content": "This is the first test memory for debugging the asynchronous processing.",
                "group_id": "debug_test"
            },
            {
                "name": "test_memory_2", 
                "content": "This is the second test memory to verify background processing works.",
                "group_id": "debug_test"
            }
        ]
        
        for memory in test_memories:
            result = self.test_direct_memory_addition(
                memory["name"], 
                memory["content"], 
                memory["group_id"]
            )
            self.log(f"Memory addition result: {result}")
            
        # Step 5: Wait for background processing
        self.wait_for_background_processing(wait_time)
        
        # Step 6: Verify memory storage
        self.verify_memory_in_neo4j()
        
        # Step 7: Test episode retrieval
        self.test_episode_retrieval()
        
        # Step 8: Summary
        self.log("=== ENHANCED LIFECYCLE TEST SUMMARY ===")
        self.log(f"Test memories created: {len(self.test_memories)}")
        for memory in self.test_memories:
            self.log(f"  - {memory['name']}: {memory['content'][:50]}...")
        
        self.log("=== ENHANCED LIFECYCLE TEST COMPLETE ===")
        self.save_debug_log()

def main():
    """Main function to run the enhanced lifecycle debugger"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced debug for LM Studio + Graphiti memory lifecycle")
    parser.add_argument('--lmstudio-url', default="http://127.0.0.1:1234/v1/chat/completions", 
                       help="LM Studio API URL")
    parser.add_argument('--graphiti-url', default="http://localhost:8000/sse", 
                       help="Graphiti server URL")
    parser.add_argument('--model', default="qwen3-32b", 
                       help="Model to use")
    parser.add_argument('--wait-time', type=int, default=30,
                       help="Time to wait for background processing (seconds)")
    
    args = parser.parse_args()
    
    debugger = EnhancedLifecycleDebugger(
        lmstudio_url=args.lmstudio_url,
        graphiti_url=args.graphiti_url,
        model=args.model
    )
    
    debugger.run_enhanced_lifecycle_test(args.wait_time)

if __name__ == "__main__":
    main() 