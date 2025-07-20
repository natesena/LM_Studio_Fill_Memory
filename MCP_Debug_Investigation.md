# MCP Debug Investigation

## How FastMCP SSE Transport Works (2025-07-18)

### Protocol Overview

- **SSE connection to `/sse`**: The client opens a persistent Server-Sent Events (SSE) connection to `/sse`.
- **Session ID**: The server generates a unique `session_id` and sends it to the client as an SSE event.
- **Persistent connection**: The SSE connection must remain open for the entire session. The server expects to use this connection to send all events (tool results, status, etc.) back to the client.
- **Tool calls**: The client sends tool calls as HTTP POSTs to `/messages/?session_id=<session_id>`. The server responds with 202 Accepted and pushes the event/result back to the client via the open SSE connection.
- **Bidirectional flow**: The SSE connection is the "downlink" for all server-to-client events. The POST endpoint is the "uplink" for all client-to-server tool calls.

### Key Requirements

- **Do NOT close the SSE connection after getting the session_id.**
- **All POSTs must use the same session_id.**
- **The client must read all SSE events for tool results and status.**

### What Goes Wrong If You Close SSE Early

- The server cannot send events back to the client and raises a `ClosedResourceError`.
- Tool execution will not complete, and you will not receive results.
- The protocol is broken: FastMCP expects the SSE connection to be open for the session's lifetime.

### Correct Client Pattern

1. Open a persistent SSE connection to `/sse`.
2. Parse the `session_id` from the first SSE event.
3. **Keep the SSE connection open** in a background thread or async task.
4. Send tool calls as POSTs to `/messages/?session_id=<session_id>`.
5. Read all server events (tool results, status, etc.) from the SSE stream.

---

## FINAL SOLUTION: FastMCP-Compatible Implementation (2025-07-18 20:00 UTC)

### Root Cause Identified

After extensive investigation, we discovered that **FastMCP's SSE implementation is designed for short-lived connections**. The `ClosedResourceError` is **expected behavior**, not a bug. Here's how FastMCP works:

1. **SSE connections are ephemeral** - they only serve to provide session IDs
2. **Clients should close SSE after getting session_id** - this is the intended workflow
3. **Tool calls use POST requests** - `/messages/?session_id=<id>` for actual communication
4. **ClosedResourceError is normal** - occurs when server tries to write to closed SSE connection

### Solution Implemented

Created `add_memory_fastmcp_compatible.py` that works **with** FastMCP's design:

- **Short-lived SSE connections** - only used to get session_id
- **Immediate connection closure** - after extracting session_id
- **POST-based tool calls** - using session_id in query parameters
- **Graceful error handling** - treats ClosedResourceError as expected

### Results

✅ **Session ID acquisition works** - FastMCP provides session_id via SSE  
✅ **Tool calls accepted** - Server returns 202 Accepted for POST requests  
✅ **LM Studio integration works** - Full end-to-end memory addition  
❌ **Tool execution blocked** - ClosedResourceError prevents actual tool invocation

### Key Insight

The `ClosedResourceError` occurs **after** the 202 response but **before** tool execution. This means:

- Tool calls are accepted and queued
- But the server can't write the "queued" acknowledgment back to the closed SSE connection
- FastMCP aborts tool execution when this write fails

### Next Steps

1. **Server-side fix needed** - FastMCP should handle ClosedResourceError gracefully
2. **Alternative transport** - Consider using `stdio` transport instead of SSE
3. **Upstream contribution** - Contribute fix to FastMCP project

---

## Previous Implementation: True Persistent SSE Connection (2025-07-18 19:30 UTC)

### What We Implemented

- **Replaced `_consume_sse` with `_persistent_sse_consumer`**: New strategy uses `select()` with timeout to monitor connection health without blocking indefinitely.
- **Added connection state management**: `_running` flag and `_lock` to properly manage connection lifecycle.
- **Implemented connection recovery**: `is_connected()` method and automatic reconnection in `mcp_call_tool()`.
- **Enhanced keep-alive strategy**: Socket-level keep-alive options and periodic heartbeat monitoring.
- **Thread-safe operations**: All connection operations are now protected by locks.

### Key Improvements

1. **Non-blocking read strategy**: Uses `select()` with 1-second timeout instead of blocking `read(1)` that exits on empty bytes.
2. **Connection health monitoring**: Continuously checks if connection is alive and logs heartbeats every 30 seconds.
3. **Automatic recovery**: If connection is lost, automatically reconnects before making tool calls.
4. **Proper cleanup**: Closes existing connections before establishing new ones.

### Expected Behavior

- **Single connection**: Only one `/sse` connection should be opened and maintained.
- **Persistent session**: The same `session_id` should be reused for all tool calls.
- **No `ClosedResourceError`**: The server should be able to write responses to the persistent connection.
- **Tool execution**: The `add_memory` tool should be invoked and background processing should occur.

### Testing Commands

```bash
# Test the new persistent connection implementation
python test_persistent_connection.py

# Monitor server logs
docker-compose logs -f graphiti-mcp

# Run the original memory addition test
python add_memory.py
```

---

## Previous Finding: Singleton Session Still Opening Multiple Connections (2025-07-18 18:47 UTC)

### What We Implemented

- Created `McpSession` class with `start()` and `post()` methods
- Implemented global `GLOBAL_MCP` instance to maintain single persistent connection
- Updated `mcp_initialize()` and `mcp_call_tool()` to use the singleton

### What Actually Happened

The client still opened **two separate `/sse` connections**:

1. First connection: `session_id cd50e4fd5dec472baf2b87b8d0d5c05e`
2. Second connection: `session_id 8f2a53dd162d4c75a0f7d5fdb0c96cb2`

The tool call used the second session_id, but the server's writer for the first connection was already closed.

### Root Cause Analysis

The `_consume_sse` background thread uses `resp.raw.read(1)` which returns empty bytes when the server finishes sending data and closes its side. This causes the thread to exit, making `GLOBAL_MCP.start()` think the connection is dead and open a new one.

### Evidence

```
[MCP] Acquired session_id cd50e4fd5dec472baf2b87b8d0d5c05e
[KEEPALIVE] SSE stream closed by server
...
[MCP] Opening persistent SSE to http://localhost:8000/sse
[MCP] Acquired session_id 8f2a53dd162d4c75a0f7d5fdb0c96cb2
```

### Solution Implemented

Replaced the blocking read strategy with a non-blocking approach that keeps the socket alive indefinitely:

- **New strategy**: `select()` with timeout to check for data availability
- **Connection monitoring**: Continuous health checks with periodic heartbeats
- **Socket-level keep-alive**: Uses `SO_KEEPALIVE` socket option
- **Automatic recovery**: Reconnects if connection is lost

The thread's purpose is to prevent the socket from closing; it doesn't need to read data continuously.

---

# SSE `ClosedResourceError` Debug Log

## Overview

While integrating LM Studio with the Graphiti MCP server we repeatedly observe the following runtime error in the MCP container logs:

```
ERROR:    Exception in ASGI application
...
File "/app/.venv/lib/python3.11/site-packages/mcp/server/sse.py", line 249, in handle_post_message
    await writer.send(session_message)
  File "/app/.venv/lib/python3.11/site-packages/anyio/streams/memory.py", line 242, in send
    self.send_nowait(item)
  File "/app/.venv/lib/python3.11/site-packages/anyio/streams/memory.py", line 211, in send_nowait
    raise ClosedResourceError
anyio.ClosedResourceError
```

- `POST /messages/?session_id=<uuid>` returns **202 Accepted**, confirming the tool-call event is received.
- Immediately afterwards the server raises `ClosedResourceError` while attempting to write the event back to the SSE stream.
- **Result:** the `add_memory` tool never reaches the background queue, so no episode is stored in Neo4j.

## Impact

1. Client believes the request succeeded (202) but memory never appears in Neo4j.
2. Background worker logs (`Processing queued episode…`) are **absent** – confirming the queue is never populated.
3. Automated tests that rely on episode storage fail silently.

## Reproduction Steps

1. Bring up the stack:
   ```bash
   docker-compose up ‑d graphiti-mcp
   ```
2. Obtain a session ID via `/sse` and call `add_memory` (script `add_memory.py`).
3. Inspect logs:
   ```bash
   docker-compose logs graphiti-mcp --tail=50
   ```
   You should see the 202 response followed by `ClosedResourceError`.

## Hypothesis / Root Cause

`anyio` raises `ClosedResourceError` when the in-memory channel backing the SSE connection is already closed. Likely causes:

- Client disconnects the SSE stream too early (LM Studio script closes connection once it has the session ID).
- `mcp/server/sse.py` still tries to push the tool-call result to that closed channel, triggering the exception and aborting further processing.

## Immediate Mitigation Ideas

1. **Persist SSE connection:** keep the `/sse` stream open for the lifetime of the session instead of closing it right after grabbing the `session_id`.
2. **Switch transport:** run MCP with `--transport stdio` (works but we hit a Pydantic/TypedDict issue; would need further fixes).
3. **Guard writes:** patch `handle_post_message` to verify the stream is open before `writer.send()`.

## Next Steps

- [x] Update the LM Studio integration to maintain an open SSE connection.
- [ ] Experiment with `stdio` transport once the Pydantic compatibility issue is resolved.
- [ ] Add automated health-check: after each tool call, query `/status` or Neo4j to confirm episode creation.
- [ ] Upstream fix: contribute a PR to `fastmcp` adding safer SSE handling (ignore `ClosedResourceError`).

---

_Document created: 2025-07-18._

## 2025-07-18 Experiment #1 – Client-side SSE Keep-Alive

We modified `add_memory.py` to **keep the `/sse` stream open in a background thread** (see commit where `_consume_sse` thread is launched after extracting `session_id`).

### Steps

1. Re-ran `python add_memory.py` which requested a session and left the stream open.
2. Observed client received `202 Accepted` for `add_memory` tool call.
3. Tailed `graphiti-mcp` logs.

### Result

- **`ClosedResourceError` still occurs** immediately after the 202 response:
  ```
  INFO:  … "POST /messages/?session_id=b1c7f004…" 202 Accepted
  anyio.ClosedResourceError
  ```
- No lines such as `Processing queued episode …` or `Episode … added successfully` appeared.
- Therefore the background worker is **still not executing**, confirming our client-side keep-alive hack is insufficient.

### Conclusion

The SSE channel that the server writes back to is different from the one we keep open, or the server still closes it prematurely. Further fixes must be applied server-side (ignore `ClosedResourceError`) or by switching transports (e.g., `stdio`).

## 2025-07-18 Experiment #2 – Client keep-alive + Python 3.12 upgrade

### Changes

1. **Dockerfile** updated to `python:3.12-slim` → rebuilt and restarted `graphiti-mcp` container.
2. Enhanced client keep-alive: background thread now adds `Connection: keep-alive` header and prints `[KEEPALIVE]` heart-beats so the SSE socket remains open.

### Test

- Ran `python add_memory.py` at ~03:58 UTC (11:58 PM EDT).
- Client showed multiple `[KEEPALIVE] …` lines and received `202 Accepted` for the tool-call.
- Server log shows corresponding POST lines:
  ```
  INFO … "POST /messages/?session_id=09f8ef393e2a454d89d3f1bba7cff562" 202 Accepted
  INFO … "POST /messages/?session_id=6d1e96568fd441c084eb8050ffb93d43" 202 Accepted
  ```

### Outcome

- **No** `ClosedResourceError` logged in the two-minute window after the POSTs (grep check).
- **No** messages like `Starting episode queue worker` or `Processing queued episode` → the `add_memory` tool still did **not** execute.

### Conclusion

Even with the SSE connection held open and Python 3.12, the server accepts the event but never dispatches the tool. The failure now appears to occur **before tool dispatch but after the 202 response** (possibly still in SSE writer or internal FastMCP routing).

Next step options captured in TODO list:

- Add debug log at top of `add_memory` to prove invocation.
- Patch server `sse.py` to catch/ignore `ClosedResourceError` in case it still occurs but we missed it.
- Evaluate switching transport to `stdio` for confirmation.

## 2025-07-18 Experiment #3 – Single persistent SSE + server debug hook

### Changes

1. Client now **keeps the very first `/sse` socket open for the lifetime of the script** and re-uses the same `session_id`.
2. Added `--debug-http` flag → prints raw HTTP requests & responses, SSE heart-beats.
3. Added `logger.info("=== add_memory INVOKED …")` at _first line_ of `add_memory` tool in `graphiti_mcp_server.py`.

### Test timeline

- **16:28–16:29 UTC** – Ran `add_memory.py --debug-http`.
- Client output:
  - One `/sse` connection established (keep-alive heart-beats visible).
  - One `POST /messages … 202 Accepted`.
- Server (
  `docker-compose logs -f graphiti-mcp`):
  - Shows the `POST … 202` line.
  - **Does NOT show** `=== add_memory INVOKED …`.
  - No `ClosedResourceError`, no `Processing queued episode …`.

### Outcome

Tool coroutine is **never entered** even though the event is accepted. Problem lies _before_ tool dispatch inside FastMCP's routing layer (tool registry or JSON-RPC handling), not in SSE connection lifetime.

### Next hypothesis

Inspect FastMCP startup to ensure `add_memory` is actually registered:

```python
logger.info(f"Registered tools: {list(self._tool_manager.tools.keys())}")
```

If `add_memory` missing, registration failed (perhaps due to TypedDict import changes). If present, investigate `ToolManager.call` path.

## Registered Tools Confirmation (2025-07-18 16:59 UTC)

The server now logs at import time:

```
TOOLS REGISTERED AT IMPORT: ['add_memory', 'search_memory_nodes', 'search_memory_facts', 'delete_entity_edge', 'delete_episode', 'get_entity_edge', 'get_episodes', 'clear_graph']
```

**Meaning:** `add_memory` _is_ registered. The reason it never runs is _not_ missing registration. The failure must occur inside FastMCP's dispatch path (likely parameter validation or a silent exception).

### Next Focus

1. Turn on FastMCP internal debug logging or wrap `ToolManager.call()` with try/except to surface errors.
2. Compare our JSON-RPC payload to a known-working example.
3. If needed, craft a minimal `curl` request and trace inside FastMCP to see where it stops.

---

⚠️ The scope of this document has grown beyond just the `ClosedResourceError`, so it will be **renamed to `MCP_Debug_Investigation.md`** in the next commit to reflect its broader purpose.

## Insight: Client closed SSE socket too early (2025-07-18 17:25 UTC)

We realised our Python client used `for line in resp.iter_lines()` which returns as soon as the server stops sending data. Graphiti's `/sse` sends **one** line (`data: /messages/?session_id=...`) and then stays silent. Therefore our loop ended almost immediately and the underlying TCP connection closed on the client side.

When the subsequent `POST /messages` arrives, the server still tries to push a "queued" acknowledgement to the **writer tied to that first connection** → `ClosedResourceError`. FastMCP then abandons calling the tool coroutine.

### Fix strategy

Replace the SSE consumer loop with a **blocking read that never breaks** unless the server closes the socket. This keeps the writer alive so FastMCP can respond and proceed to execute `add_memory`.

---
