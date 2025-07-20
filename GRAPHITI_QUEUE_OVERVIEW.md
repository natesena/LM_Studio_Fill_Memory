# Graphiti Episode Queue – Architectural Overview

## 1. Purpose of the Queue

Graphiti processes _episodes_ (pieces of information that will be converted into graph data) in the background.  
To avoid race-conditions when multiple episodes target the **same graph (identified by `group_id`)**, Graphiti enforces **sequential processing per group** by placing every episode into an **`asyncio.Queue`**.

## 2. Where the Queue Lives in the Codebase

- **File:** `graphiti/mcp_server/graphiti_mcp_server.py`
- **Key symbols:**
  - `episode_queues: dict[str, asyncio.Queue]` – one queue per `group_id`.
  - `queue_workers: dict[str, bool]` – tracks whether a worker coroutine is active for the given `group_id`.
  - `async def process_episode_queue(group_id: str)` – long-lived worker that consumes a single queue.
  - `@mcp.tool() async def add_memory(...)` – enqueues a _process_episode_ coroutine and (if needed) spawns a worker.

```text
> enqueue → add_memory()                   # HTTP 202 returned to client
> └─ episode_queues[group_id].put(func)    # func is the actual processing coroutine
>    └─ if worker not running → asyncio.create_task(process_episode_queue(group_id))

process_episode_queue():
    while True:
        func = await episode_queues[group_id].get()  # blocks when queue empty
        await func()                                 # does the heavy work
        episode_queues[group_id].task_done()
```

## 3. Runtime Behaviour

1. **Client request** – `add_memory` returns immediately with a _"queued for processing"_ message (HTTP 202).
2. **Queue growth** – `episode_queues[group_id].qsize()` increases; one worker consumes tasks FIFO.
3. **Processing** – each task logs:  
   _Queued_ – `Episode '{name}' queued for processing (position: N)`  
   _Start_ – `Processing queued episode '{name}' for group_id: {gid}`  
   _Success_ – `Episode '{name}' processed successfully`  
   _Error_ – `Error processing queued episode for group_id {gid}: …`

## 4. What Is _Not_ Exposed Externally

- There is **no REST/SSE endpoint** that reveals queue length or worker status.
- The existing `get_status` resource only verifies Neo4j connectivity.

## 5. Current External Monitoring Work-arounds in `LM_Studio_Fill_Memory`

- **`queue_monitor.py`, `queue_status_checker.py`** – parse Docker logs for the log messages above to infer:
  - current item being processed
  - recently completed items
  - rough queue length (by counting "Processing queued episode…" occurrences)
- These scripts are brittle – they rely on log formats and cannot see _future_ queue length (`qsize()` after dequeue).

## 6. Recommendations for Robust External Monitoring

1. **Expose an official endpoint** (e.g. `GET /queue/status` via `@mcp.resource`) returning JSON like:
   ```json
   {
     "group_queues": {
       "default": { "size": 3, "worker_active": true },
       "analytics": { "size": 0, "worker_active": false }
     }
   }
   ```
2. **Emit SSE events** on enqueue/dequeue with the same information so clients can subscribe instead of polling.
3. **Prometheus metrics** – export `graphiti_episode_queue_size{group_id="…"}` and `graphiti_episode_worker_active` gauges.
4. **Graceful backlog control** – refuse new `add_memory` requests or respond with _429_ if the queue exceeds a threshold.

## 7. Quick Patch Outline (for future work)

```python
@mcp.resource("http://graphiti/queue/status")
async def get_queue_status() -> dict[str, Any]:
    return {
        "group_queues": {
            gid: {"size": q.qsize(), "worker_active": queue_workers.get(gid, False)}
            for gid, q in episode_queues.items()
        }
    }
```

This adds <10 lines of code, zero dependencies, and enables both human and programmatic monitoring.

---

_Document generated automatically – feel free to move or rename as needed._
