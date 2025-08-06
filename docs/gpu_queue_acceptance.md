# GPU-Exclusive Processing & Queue Visibility – Acceptance Criteria

## Objective

Guarantee that **exactly one GPU-intensive task** (either LM Studio analysis **or** Graphiti episode processing) runs at any moment, and provide operators with a clear, real-time view of that hand-off.

---

## Functional Requirements

1. **Mutual Exclusion**

   - When LM Studio is running, _no_ Graphiti episode may begin processing.
   - When Graphiti is processing an episode, LM Studio must wait.
   - Enforcement may use a file-lock, Redis lock, or similar—but must be process-wide (covers multiple shells / scripts).

2. **Queue Gatekeeping**

   - Before LM Studio starts analysing the next file, the Graphiti container’s queue _must be empty_.
   - Definition of _empty_: no log lines matching
     `Processing queued episode '…' for group_id:` in the **last N seconds** and no worker currently active.

3. **Progress Signals** (operator-readable)

   - For every file `i / total` emit four concise lines:
     ```
     [HH:MM:SS] LM  ▶️  Start  i/total  <filename>
     [HH:MM:SS] LM  ✅  Done   i/total  <filename>
     [HH:MM:SS] GRA ▶️  Start  i/total  <filename>
     [HH:MM:SS] GRA ✅  Done   i/total  <filename>
     ```
   - If Graphiti does not finish within **10 minutes**:
     `GRA ⚠️  TIMEOUT  i/total  <filename>`

4. **Pre-File Queue Check & Wait**

   - Before starting LM Studio on _each_ file the script **must**:
     1. Query current queue length.
     2. If length > 0 → print `Queue busy (N) – waiting…` and poll until length is 0.
     3. Only then print `Queue empty – starting LM Studio …` and proceed.
   - During the wait loop the script prints an updated pending count every ≤ 10 s.
   - Ensures no file analysis starts while another episode is still processing.

5. **Operator Verification Tool**

   - A `queue_watch` utility (CLI or simple script) that refreshes every few seconds and shows:
     • current processing episode(s)
     • worker status (running / idle)
     • recent errors
   - Must work without reading code; plain console output is sufficient.

6. **Failure Handling**
   - If Graphiti returns an error for an episode, mark the file as **failed** and continue to the next after waiting 2 seconds.
   - Summary at the end lists processed / successful / failed counts.

---

## Non-Functional Requirements

• **Simplicity** – No heavy dashboards; plain text suited for SSH terminals.
• **No Code Review Needed** – Operators shouldn’t read Python to understand state.
• **Portability** – Works on macOS/Linux with `docker` and Python 3.8+.

---

## Acceptance Checklist

| #   | Criterion             | Pass Condition                                                                                                                                 |
| --- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | GPU mutex             | Running two batch scripts concurrently still results in strictly sequential LM/GRA lines (never interleaved).                                  |
| 2   | Queue empty check     | When Graphiti is already busy, batch script waits until `queue_watch` shows no processing episodes before LM Studio starts a new analysis.     |
| 3   | Progress visibility   | Operator sees the four milestone lines for every file without additional flags.                                                                |
| 4   | Timeout flag          | If Graphiti exceeds 10 min for a file, script prints `GRA ⚠️ TIMEOUT` and continues.                                                           |
| 5   | Summary               | End-of-run summary matches actual counts in Neo4j.                                                                                             |
| 6   | Pre-file queue gating | For every file the log first shows either `Queue empty – starting …` **or** a wait loop that counts down until queue length is 0, then starts. |

---

## Next Steps

1. Implement cross-process GPU lock.
2. Extend `queue_monitor.py` with `--tail` and `--follow`.
3. Integrate lock + monitor into batch pipeline.
4. Validate checklist with a 3-file test run.

---

### NEW TASK – Expose Queue via Diagnostics Service (Approach #2)

We discovered the SSE-only MCP transport does **not** surface arbitrary GET routes. Solution:

1. **Create a lightweight FastAPI diagnostics server** inside the same container (port 8001).
   • File `mcp_server/diagnostics.py` starts `FastAPI()` and shares process memory, so it can read `episode_queues` / `queue_names` directly.
   • Route `GET /queue/status` returns the live snapshot JSON.

2. **Container changes**
   • Update `Dockerfile` to launch both MCP and diagnostics (e.g. `uvicorn diagnostics:app --port 8001 & mcp ...`).

3. **Remove the unused attempt**
   • Delete the `add_api_route("/queue/status" …)` code added earlier in `graphiti_mcp_server.py` (it’s unreachable in SSE mode).

4. **Validation steps**
   1. Re-build and restart the container.
   2. Run `curl http://localhost:8001/queue/status` → should show queue JSON with correct `size`/`items`.
   3. While an episode is processing, confirm `size` > 0; after success, confirm it returns to 0.
   4. Batch script polls this endpoint and waits until `size` == 0 before starting LM Studio.

Add these steps to the overall checklist once implemented.
