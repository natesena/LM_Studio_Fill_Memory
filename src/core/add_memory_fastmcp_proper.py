import requests
import threading
import queue
import time
import uuid as uuidlib
import json

class FastMcpSession:
    def __init__(self, sse_url):
        self.sse_url = sse_url
        self.session_id = None
        self._sse_thread = None
        self._event_queue = queue.Queue()
        self._stop_event = threading.Event()
        self._sse_connection = None
        self._initialized = False

    def start(self):
        """Initialize the MCP session by getting session_id via SSE and keeping connection open"""
        self._sse_thread = threading.Thread(target=self._sse_listener, daemon=True)
        self._sse_thread.start()
        # Wait for session_id to be set
        for _ in range(30):
            if self.session_id:
                return
            time.sleep(0.1)
        raise RuntimeError("Failed to get session_id from SSE stream")

    def _sse_listener(self):
        """Keep SSE connection open and listen for events"""
        try:
            self._sse_connection = requests.get(self.sse_url, stream=True)
            event_type = None
            data_lines = []
            for line in self._sse_connection.iter_lines(decode_unicode=True):
                if self._stop_event.is_set():
                    break
                if line is None:
                    continue
                line = line.strip()
                if line == "":
                    # End of event
                    if event_type and data_lines:
                        data = "\n".join(data_lines)
                        if event_type == "endpoint":
                            # Parse session_id from endpoint URL
                            if "session_id=" in data:
                                self.session_id = data.split("session_id=")[-1]
                                print(f"[SSE] Got session_id: {self.session_id}")
                        else:
                            self._event_queue.put({"event": event_type, "data": data})
                            print(f"[SSE] Event: {{'event': '{event_type}', 'data': '{data}'}}")
                    # Reset for next event
                    event_type = None
                    data_lines = []
                    continue
                if line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].strip())
        except Exception as e:
            print(f"[SSE] Connection error: {e}")
        finally:
            if self._sse_connection:
                self._sse_connection.close()

    def stop(self):
        """Stop the SSE listener and close connection"""
        self._stop_event.set()
        if self._sse_connection:
            self._sse_connection.close()
        if self._sse_thread:
            self._sse_thread.join(timeout=2)

    def get_event(self, timeout=10):
        try:
            return self._event_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def initialize(self, base_url):
        """Send MCP initialize request and wait for response"""
        assert self.session_id, "Session not initialized"
        url = f"{base_url}/messages/?session_id={self.session_id}"
        
        # Send initialize request
        initialize_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "FastMcpClient",
                    "version": "1.0.0"
                }
            }
        }
        
        print(f"[INITIALIZE] Sending initialize request...")
        resp = requests.post(url, json=initialize_payload, timeout=30)
        print(f"[INITIALIZE] Status: {resp.status_code}, Body: {resp.text}")
        
        if resp.status_code == 202:
            # Wait for initialize response via SSE
            print(f"[INITIALIZE] Waiting for response via SSE...")
            for _ in range(30):
                event = self.get_event(timeout=1)
                if event and event.get("event") == "message":
                    try:
                        data = json.loads(event["data"])
                        if "result" in data and data.get("id") == 1:
                            print(f"✅ Initialize successful: {json.dumps(data['result'], indent=2)}")
                            
                            # Send initialized notification
                            initialized_payload = {
                                "jsonrpc": "2.0",
                                "method": "notifications/initialized"
                            }
                            init_resp = requests.post(url, json=initialized_payload, timeout=30)
                            print(f"[INITIALIZED] Status: {init_resp.status_code}")
                            
                            self._initialized = True
                            return True
                        elif "error" in data and data.get("id") == 1:
                            print(f"❌ Initialize failed: {data['error']}")
                            return False
                    except json.JSONDecodeError:
                        continue
                elif event:
                    print(f"[INITIALIZE] Received event: {event}")
            print("❌ No initialize response received")
            return False
        else:
            print(f"❌ Initialize request failed: {resp.status_code}")
            return False

    def list_tools(self, base_url):
        """List available tools on the MCP server"""
        assert self.session_id, "Session not initialized"
        assert self._initialized, "Session not initialized with MCP protocol"
        url = f"{base_url}/messages/?session_id={self.session_id}"
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuidlib.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        resp = requests.post(url, json=payload, timeout=30)
        print(f"[TOOLS/LIST] Status: {resp.status_code}, Body: {resp.text}")
        return resp

    def post_tool_call(self, base_url, tool_name, arguments):
        """Call a tool on the MCP server"""
        assert self.session_id, "Session not initialized"
        assert self._initialized, "Session not initialized with MCP protocol"
        url = f"{base_url}/messages/?session_id={self.session_id}"
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuidlib.uuid4()),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments}
        }
        resp = requests.post(url, json=payload, timeout=30)
        print(f"[TOOLS/CALL] Status: {resp.status_code}, Body: {resp.text}")
        return resp

if __name__ == "__main__":
    # 1. Initialize MCP session and keep SSE connection open
    print("=== STEP 1: Initializing MCP Session ===")
    sse_url = "http://localhost:8000/sse"
    base_url = "http://localhost:8000"
    session = FastMcpSession(sse_url)
    session.start()
    print("✅ SSE connection established and session_id obtained")
    print("✅ SSE connection kept open for server responses")

    # 2. Perform MCP protocol initialization
    print("\n=== STEP 2: MCP Protocol Initialization ===")
    if not session.initialize(base_url):
        print("❌ MCP initialization failed, exiting")
        session.stop()
        exit(1)
    print("✅ MCP protocol initialization complete")

    # 3. List available tools
    print("\n=== STEP 3: Listing Available Tools ===")
    tools_response = session.list_tools(base_url)
    if tools_response.status_code == 202:
        print("✅ Tools list request accepted (202)")
        # Wait for tools list response via SSE
        print("Waiting for tools list response via SSE...")
        for _ in range(30):
            event = session.get_event(timeout=1)
            if event and event.get("event") == "message":
                try:
                    data = json.loads(event["data"])
                    if "result" in data and "tools" in data["result"]:
                        tools = data["result"]["tools"]
                        print(f"✅ Tools listed successfully: {len(tools)} tools found")
                        for tool in tools:
                            print(f"  - {tool.get('name', 'unknown')}: {tool.get('description', 'no description')}")
                        break
                    elif "error" in data:
                        print(f"❌ Tools list failed: {data['error']}")
                        break
                except json.JSONDecodeError:
                    continue
            elif event:
                print(f"[TOOLS/LIST] Received event: {event}")
    else:
        print(f"❌ Tool listing failed: {tools_response.status_code}")

    # 4. Make a tool call
    print("\n=== STEP 4: Calling add_memory Tool ===")
    tool_name = "add_memory"
    arguments = {
        "name": "Proper MCP Lifecycle Test",
        "episode_body": "This is a test using the complete MCP lifecycle with proper initialization."
    }
    tool_response = session.post_tool_call(base_url, tool_name, arguments)

    # 5. Wait for result events (SSE connection should stay open)
    print("\n=== STEP 5: Waiting for Tool Result Events ===")
    print("Waiting for tool result events from SSE (connection kept open)...")
    for i in range(30):
        event = session.get_event(timeout=1)
        if event:
            print(f"[RESULT {i+1}] Received event: {event}")
            # Check if this is a success or error response
            try:
                if "data" in event:
                    data = json.loads(event["data"])
                    if "result" in data:
                        print(f"✅ Tool call successful: {data['result']}")
                        break
                    elif "error" in data:
                        print(f"❌ Tool call failed: {data['error']}")
                        break
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse event data as JSON")
        else:
            print(f"No event yet, waiting... ({i+1}/30)")

    session.stop()
    print("\n=== SESSION COMPLETE ===")
    print("Session closed.") 