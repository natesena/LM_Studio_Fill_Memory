#!/usr/bin/env python3
"""
Test script to verify persistent SSE connection functionality.
This script tests that we maintain a single persistent connection
and can make multiple tool calls without opening new connections.
"""

import time
import json
import uuid
from add_memory import GLOBAL_MCP, mcp_initialize, mcp_call_tool

def test_persistent_connection():
    """Test that we maintain a single persistent SSE connection."""
    print("=== Testing Persistent SSE Connection ===")
    
    # Step 1: Initialize the connection
    print("\n1. Initializing MCP connection...")
    session_id = mcp_initialize("http://localhost:8000/sse")
    print(f"   Session ID: {session_id}")
    
    # Step 2: Verify connection is alive
    print("\n2. Verifying connection status...")
    is_connected = GLOBAL_MCP.is_connected()
    print(f"   Connection alive: {is_connected}")
    
    # Step 3: Wait a bit to see if connection stays alive
    print("\n3. Waiting 10 seconds to verify connection persistence...")
    for i in range(10):
        time.sleep(1)
        if GLOBAL_MCP.is_connected():
            print(f"   {i+1}/10: Connection still alive")
        else:
            print(f"   {i+1}/10: Connection lost!")
            break
    
    # Step 4: Make a test tool call
    print("\n4. Making test tool call...")
    test_args = {
        "name": "Persistent Connection Test",
        "episode_body": "This is a test memory to verify that the persistent SSE connection works correctly. The connection should remain open throughout multiple tool calls."
    }
    
    try:
        result = mcp_call_tool("http://localhost:8000/sse", session_id, "add_memory", test_args)
        print(f"   Tool call result: {result}")
    except Exception as e:
        print(f"   Tool call failed: {e}")
    
    # Step 5: Verify connection is still alive after tool call
    print("\n5. Verifying connection after tool call...")
    is_connected = GLOBAL_MCP.is_connected()
    print(f"   Connection alive: {is_connected}")
    
    # Step 6: Make another tool call to test reusability
    print("\n6. Making second tool call to test connection reuse...")
    test_args2 = {
        "name": "Second Test Call",
        "episode_body": "This is a second test memory to verify that the same connection can be reused for multiple tool calls without opening new SSE connections."
    }
    
    try:
        result2 = mcp_call_tool("http://localhost:8000/sse", session_id, "add_memory", test_args2)
        print(f"   Second tool call result: {result2}")
    except Exception as e:
        print(f"   Second tool call failed: {e}")
    
    # Step 7: Final connection check
    print("\n7. Final connection verification...")
    is_connected = GLOBAL_MCP.is_connected()
    print(f"   Final connection alive: {is_connected}")
    
    print("\n=== Test Complete ===")
    return is_connected

def test_connection_recovery():
    """Test that the connection can recover if it gets disconnected."""
    print("\n=== Testing Connection Recovery ===")
    
    # Force a reconnection by closing the current connection
    if GLOBAL_MCP._resp and not GLOBAL_MCP._resp.raw.closed:
        print("1. Forcing connection close to test recovery...")
        GLOBAL_MCP._resp.close()
        GLOBAL_MCP._running = False
    
    # Try to make a tool call - should automatically reconnect
    print("2. Attempting tool call after forced disconnect...")
    session_id = mcp_initialize("http://localhost:8000/sse")
    
    test_args = {
        "name": "Recovery Test",
        "episode_body": "This memory tests the connection recovery mechanism. The connection should automatically reconnect if it gets disconnected."
    }
    
    try:
        result = mcp_call_tool("http://localhost:8000/sse", session_id, "add_memory", test_args)
        print(f"   Recovery test result: {result}")
        print("   ✓ Connection recovery successful!")
    except Exception as e:
        print(f"   ✗ Connection recovery failed: {e}")

if __name__ == "__main__":
    print("Starting persistent connection tests...")
    
    # Test basic persistence
    success = test_persistent_connection()
    
    if success:
        # Test recovery if basic test passed
        test_connection_recovery()
    
    print("\nAll tests completed!") 