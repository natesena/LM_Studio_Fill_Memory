# LM Studio + Graphiti Memory Integration Debugging Guide

This guide explains the complete lifecycle of memory addition and provides tools to debug issues.

## ⚠️ CRITICAL DISCOVERY: Asynchronous Processing

**The Graphiti MCP server processes memories asynchronously!** This is the key to understanding why you might not see memories in Neo4j immediately.

### How It Actually Works:

1. **Tool Call Received**: MCP server receives the `add_memory` tool call
2. **Immediate Response**: Returns 202 Accepted immediately with a success message
3. **Background Queue**: The memory is added to an `asyncio.Queue` for processing
4. **Background Worker**: A separate `process_episode_queue()` function processes episodes sequentially
5. **Neo4j Storage**: Only after background processing does the memory get stored in Neo4j

**This means:**

- ✅ 202 Accepted = Memory was queued successfully
- ❌ 202 Accepted ≠ Memory is stored in Neo4j yet
- ⏱️ You need to wait for background processing to complete

## Overview of the Memory Addition Lifecycle

The memory addition process involves several components working together:

```
1. LM Studio (LLM) → 2. Tool Call Request → 3. Graphiti Server → 4. Background Queue → 5. Neo4j Database
```

### Detailed Lifecycle Steps:

1. **LM Studio Processing**

   - User provides a prompt to LM Studio
   - LM Studio analyzes the prompt and decides to call the `add_memory` tool
   - LM Studio generates tool call arguments (name, episode_body)

2. **Session Initialization**

   - Connect to Graphiti server's `/sse` endpoint
   - Parse session ID from Server-Sent Events stream
   - Establish MCP protocol session

3. **Tool Discovery** (Optional)

   - Query available tools on the Graphiti server
   - Verify `add_memory` tool is available

4. **Tool Execution**

   - Send JSON-RPC tool call to Graphiti server
   - Server responds with 202 Accepted (queued) or error
   - **Tool call is queued for background processing**

5. **Background Processing** ⚠️ **NEW DISCOVERY**

   - Background worker processes the queue sequentially
   - Each episode is processed with entity extraction
   - LLM operations may be performed for processing
   - Only then is the memory stored in Neo4j

6. **Memory Storage**
   - Graphiti server processes the tool call
   - Creates memory nodes in Neo4j database
   - Establishes relationships between entities

## Debugging Tools

### 1. Enhanced Lifecycle Debugger (`enhanced_debug_lifecycle.py`) ⭐ **NEW**

This tool specifically addresses the asynchronous processing issue:

```bash
# Run enhanced lifecycle test with 30-second wait for background processing
python enhanced_debug_lifecycle.py --wait-time 30

# Use different URLs
python enhanced_debug_lifecycle.py --graphiti-url http://localhost:8000/sse --wait-time 60
```

**What it tests:**

- LM Studio availability and model list
- Graphiti server connectivity and status
- Session initialization
- Direct tool calls with tracking
- **Waits for background processing** ⭐
- Verifies memory storage in Neo4j
- Tests episode retrieval
- Provides comprehensive logging

**Key Features:**

- Tracks test memories for verification
- Waits for background processing to complete
- Uses Graphiti's own tools to verify storage
- Provides detailed timing information

### 2. Original Lifecycle Debugger (`debug_lifecycle.py`)

This tool maps out the complete lifecycle and provides detailed logging:

```bash
# Run full lifecycle test
python debug_lifecycle.py

# Test with specific file
python debug_lifecycle.py --test-file add_memory.py

# Use different URLs
python debug_lifecycle.py --lmstudio-url http://localhost:1234/v1/chat/completions --graphiti-url http://localhost:8000/sse
```

**What it tests:**

- LM Studio availability and model list
- Graphiti server connectivity
- Tool discovery and availability
- Session initialization
- Direct tool calls
- LM Studio tool calling
- Complete end-to-end workflow

**Output:**

- Timestamped logs for each step
- Detailed request/response information
- Error diagnosis
- Debug log file (`debug_lifecycle.log`)

### 3. Neo4j Verifier (`verify_neo4j_memories.py`)

This tool verifies what's actually stored in Neo4j:

```bash
# Basic verification
python verify_neo4j_memories.py

# With custom Neo4j credentials
python verify_neo4j_memories.py --username neo4j --password your_password

# Search for specific terms
python verify_neo4j_memories.py --search-terms test memory lifecycle
```

**What it checks:**

- Neo4j connectivity
- Database information
- Node and relationship counts
- Memory-related nodes
- Recent nodes (last 24 hours)
- Specific memory searches

## Common Issues and Solutions

### Issue 1: "No server found with tool: add_memory"

**Symptoms:**

- Tool discovery fails
- Tool calls return errors

**Possible Causes:**

- Graphiti server not running
- MCP protocol not properly configured
- Tool not registered on server

**Debugging Steps:**

1. Run `debug_lifecycle.py` to check server availability
2. Check Graphiti server logs
3. Verify MCP configuration

### Issue 2: 202 Accepted but No Memory in Neo4j ⚠️ **UPDATED**

**Symptoms:**

- Tool calls succeed (202 status)
- No new nodes appear in Neo4j
- No error messages

**Root Cause:** ⭐ **Asynchronous Processing**

- The 202 status means the memory was queued, not stored
- Background processing may be failing or slow
- You need to wait for background processing to complete

**Debugging Steps:**

1. **Run `enhanced_debug_lifecycle.py`** - This specifically addresses this issue
2. Check Graphiti server logs for background worker errors
3. Verify Neo4j connectivity and credentials
4. Check for memory processing errors in server logs
5. **Wait longer** - Background processing can take time

**New Debugging Approach:**

```bash
# Test with longer wait time
python enhanced_debug_lifecycle.py --wait-time 60

# Check server logs for background processing
# Look for messages like:
# "Processing queued episode 'test_memory' for group_id: debug_test"
# "Episode 'test_memory' added successfully"
```

### Issue 3: LM Studio Timeouts

**Symptoms:**

- Requests to LM Studio timeout
- Long response times

**Possible Causes:**

- Large file content
- Model loading issues
- Insufficient resources

**Debugging Steps:**

1. Reduce `max_chars` parameter
2. Check LM Studio logs
3. Verify model is loaded
4. Increase timeout values

### Issue 4: Session Initialization Failures

**Symptoms:**

- Cannot get session ID
- SSE connection failures

**Possible Causes:**

- Graphiti server not running
- Incorrect URL
- Network connectivity issues

**Debugging Steps:**

1. Check Graphiti server status
2. Verify URL format
3. Test network connectivity
4. Check server logs

### Issue 5: Background Processing Failures ⭐ **NEW**

**Symptoms:**

- 202 Accepted but memories never appear
- No background processing logs
- Queue workers not running

**Possible Causes:**

- Background worker crashed
- Neo4j connection issues in background
- LLM processing failures
- Queue processing errors

**Debugging Steps:**

1. Check Graphiti server logs for background worker messages
2. Verify Neo4j connectivity from server
3. Check for LLM processing errors
4. Restart the Graphiti server
5. Use `enhanced_debug_lifecycle.py` to test with proper waiting

## Expected Lifecycle Flow

### Successful Memory Addition (Updated):

```
1. [INFO] === STEP 1: Checking LM Studio Availability ===
   [INFO] Testing connection to LM Studio at: http://127.0.0.1:1234/v1/chat/completions
   [INFO] LM Studio models endpoint response: 200
   [INFO] Available models: ['qwen3-32b']

2. [INFO] === STEP 2: Checking Graphiti Server Availability ===
   [INFO] Testing connection to Graphiti at: http://localhost:8000
   [INFO] Graphiti base endpoint response: 200
   [INFO] Graphiti SSE endpoint response: 200
   [INFO] Graphiti status: {'status': 'ok', 'message': 'Graphiti MCP server is running and connected to Neo4j'}

3. [INFO] === STEP 3: Getting MCP Session ===
   [INFO] Requesting session from: http://localhost:8000/sse
   [INFO] SSE connection established, parsing for session_id...
   [INFO] Found session line: b'data: /messages/?session_id=abc123...'
   [INFO] Extracted session_id: abc123...

4. [INFO] === STEP 4: Testing Direct Memory Addition ===
   [INFO] Tool call details:
   [INFO]   URL: http://localhost:8000/messages/?session_id=abc123...
   [INFO]   Tool: add_memory
   [INFO]   Arguments: {"name": "test_memory", "episode_body": "..."}
   [INFO] Tool call response:
   [INFO]   Status: 202
   [INFO]   Time: 0.15s
   [INFO] Server accepted the event (202). Memory addition is queued.

5. [INFO] === STEP 5: Waiting for Background Processing (30s) ===
   [INFO] The Graphiti MCP server processes memories asynchronously.
   [INFO] We need to wait for the background worker to process the queued episodes.
   [INFO] Waiting for background processing... 30s remaining
   [INFO] Waiting for background processing... 29s remaining
   ...
   [INFO] Background processing wait completed.

6. [INFO] === STEP 6: Verifying Memory Storage in Neo4j ===
   [INFO] Graphiti status check: 200
   [INFO] Graphiti status: {'status': 'ok', 'message': 'Graphiti MCP server is running and connected to Neo4j'}
   [INFO] Searching for memory: test_memory
   [INFO] Search response for 'test_memory': 200
   [INFO] Search results for 'test_memory': {"result": {"nodes": [...]}}

7. [INFO] === STEP 7: Testing Episode Retrieval ===
   [INFO] Get episodes response: 200
   [INFO] Found 5 recent episodes
   [INFO] ✅ Found test memory 'test_memory' in episodes
```

### Neo4j Verification (After Memory Addition):

```
[INFO] === STARTING NEO4J VERIFICATION ===
[INFO] === Testing Neo4j Connection ===
[INFO] Neo4j browser response: 200
[INFO] Neo4j REST API response: 200
[INFO] === Getting Node Count ===
[INFO] Node count: {"results": [{"data": [{"row": [8]}]}]}
[INFO] === Getting Memory Nodes ===
[INFO] Memory nodes: {"results": [{"data": [{"row": [{"name": "test_memory", "episode_body": "..."}]}]}]}
```

## Configuration Files

### Environment Variables:

```bash
export LMSTUDIO_URL="http://127.0.0.1:1234/v1/chat/completions"
export GRAPHITI_URL="http://localhost:8000/sse"
export NEO4J_URL="http://localhost:7474"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="password"
```

### Timeout Settings:

- LM Studio requests: 600 seconds (10 minutes)
- Graphiti tool calls: 30 seconds
- Neo4j queries: 10 seconds
- Connection tests: 5 seconds
- **Background processing wait: 30-60 seconds** ⭐

## Troubleshooting Checklist

When debugging memory addition issues:

- [ ] Is LM Studio running and accessible?
- [ ] Is Graphiti server running and accessible?
- [ ] Is Neo4j running and accessible?
- [ ] Are all URLs correct?
- [ ] Are credentials correct (if required)?
- [ ] Are there any server logs showing errors?
- [ ] **Are background workers processing the queued requests?** ⭐
- [ ] **Have you waited long enough for background processing?** ⭐
- [ ] Is the MCP protocol properly configured?
- [ ] Are tool calls being sent with correct format?
- [ ] Are sessions being established correctly?
- [ ] **Are there any background processing errors in server logs?** ⭐

## Next Steps

1. **Run `enhanced_debug_lifecycle.py`** to get a complete picture of the system state with proper waiting
2. Run `verify_neo4j_memories.py` to check what's actually stored
3. Check server logs for any error messages, especially background processing errors
4. Use the debugging output to identify the specific issue
5. Apply the appropriate solution from the troubleshooting guide

## Key Takeaways

1. **202 Accepted ≠ Stored**: The 202 status means queued, not stored
2. **Wait for Background Processing**: Memories are processed asynchronously
3. **Use Enhanced Debugger**: The enhanced debugger specifically addresses the async issue
4. **Check Server Logs**: Background processing errors may not appear in client responses
5. **Group IDs Matter**: Make sure you're using consistent group IDs for testing
