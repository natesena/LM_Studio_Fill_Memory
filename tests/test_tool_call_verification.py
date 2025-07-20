#!/usr/bin/env python3
"""
Test Tool Call Verification Script

This script tests whether the Graphiti MCP server is actually receiving and processing tool calls.
"""

import requests
import json
import uuid
import re
import time
from datetime import datetime

def log(message: str):
    """Log a message with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def get_session(graphiti_url: str = "http://localhost:8000/sse") -> str:
    """Get a session ID from Graphiti server"""
    log("Getting MCP session...")
    try:
        headers = {"Accept": "text/event-stream"}
        response = requests.get(graphiti_url, headers=headers, stream=True, timeout=10)
        
        if response.status_code != 200:
            raise Exception(f"Failed to connect to SSE endpoint: {response.status_code}")
        
        # Parse SSE stream for session_id
        for line in response.iter_lines():
            if b"session_id" in line:
                match = re.search(rb'session_id=([a-f0-9]+)', line)
                if match:
                    session_id = match.group(1).decode()
                    log(f"Session ID: {session_id}")
                    return session_id
        
        raise Exception("Could not find session_id in SSE stream")
        
    except Exception as e:
        log(f"Failed to get session: {e}")
        raise

def test_tool_call(session_id: str, graphiti_url: str = "http://localhost:8000/sse") -> dict:
    """Test a direct tool call to verify processing"""
    log("Testing direct tool call...")
    
    try:
        base_url = graphiti_url.replace('/sse', '')
        messages_url = f"{base_url}/messages/?session_id={session_id}"
        
        tool_call_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": "add_memory",
                "arguments": {
                    "name": "test_verification_memory",
                    "episode_body": "This is a test memory to verify tool call processing.",
                    "group_id": "test_group"
                }
            }
        }
        
        log(f"Sending tool call to: {messages_url}")
        log(f"Tool call payload: {json.dumps(tool_call_request, indent=2)}")
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(messages_url, json=tool_call_request, headers=headers, timeout=30)
        
        log(f"Response status: {response.status_code}")
        log(f"Response body: {response.text}")
        
        if response.status_code == 202:
            log("✅ Tool call accepted (202)")
            return {"success": True, "status": 202, "message": "Tool call accepted"}
        else:
            log(f"❌ Tool call failed: {response.status_code}")
            return {"success": False, "status": response.status_code, "message": response.text}
            
    except Exception as e:
        log(f"❌ Tool call error: {e}")
        return {"success": False, "error": str(e)}

def test_tool_listing(session_id: str, graphiti_url: str = "http://localhost:8000/sse") -> dict:
    """Test tool listing to verify server is responding"""
    log("Testing tool listing...")
    
    try:
        base_url = graphiti_url.replace('/sse', '')
        messages_url = f"{base_url}/messages/?session_id={session_id}"
        
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        
        log(f"Sending tool list request to: {messages_url}")
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(messages_url, json=list_tools_request, headers=headers, timeout=30)
        
        log(f"Tool list response status: {response.status_code}")
        log(f"Tool list response body: {response.text}")
        
        if response.status_code == 200:
            log("✅ Tool listing successful")
            return {"success": True, "status": 200, "data": response.json()}
        else:
            log(f"❌ Tool listing failed: {response.status_code}")
            return {"success": False, "status": response.status_code, "message": response.text}
            
    except Exception as e:
        log(f"❌ Tool listing error: {e}")
        return {"success": False, "error": str(e)}

def check_docker_logs():
    """Check Docker logs for tool call processing"""
    log("Checking Docker logs for tool call processing...")
    
    import subprocess
    
    try:
        # Get recent logs
        result = subprocess.run([
            "docker", "logs", "graphiti-graphiti-mcp-1", "--tail", "20"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logs = result.stdout
            log("Recent Docker logs:")
            print(logs)
            
            # Check for specific patterns
            if "CallToolRequest" in logs:
                log("✅ Found CallToolRequest in logs")
            else:
                log("❌ No CallToolRequest found in logs")
                
            if "add_memory" in logs:
                log("✅ Found add_memory in logs")
            else:
                log("❌ No add_memory found in logs")
                
            if "Processing queued episode" in logs:
                log("✅ Found background processing in logs")
            else:
                log("❌ No background processing found in logs")
                
        else:
            log(f"❌ Failed to get Docker logs: {result.stderr}")
            
    except Exception as e:
        log(f"❌ Error checking Docker logs: {e}")

def main():
    """Main test function"""
    log("=== TOOL CALL VERIFICATION TEST ===")
    
    try:
        # Step 1: Get session
        session_id = get_session()
        
        # Step 2: Test tool listing
        tool_list_result = test_tool_listing(session_id)
        
        # Step 3: Test tool call
        tool_call_result = test_tool_call(session_id)
        
        # Step 4: Wait a moment
        log("Waiting 5 seconds for processing...")
        time.sleep(5)
        
        # Step 5: Check Docker logs
        check_docker_logs()
        
        # Step 6: Summary
        log("=== TEST SUMMARY ===")
        log(f"Tool listing: {'✅ Success' if tool_list_result['success'] else '❌ Failed'}")
        log(f"Tool call: {'✅ Success' if tool_call_result['success'] else '❌ Failed'}")
        
        if tool_call_result.get('status') == 202:
            log("⚠️  Tool call returned 202 (accepted) but check Docker logs for actual processing")
        else:
            log("❌ Tool call did not return 202 - check server status")
            
    except Exception as e:
        log(f"❌ Test failed: {e}")

if __name__ == "__main__":
    main() 