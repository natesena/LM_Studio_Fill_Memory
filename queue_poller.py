#!/usr/bin/env python3
"""
Poll the live Graphiti queue length every N seconds and log to stdout.
The queue length is read directly from `graphiti_mcp_server.episode_queues` inside the running container — no regex.
"""

import subprocess
import time
import json
import argparse
from datetime import datetime

def fetch_queue_lengths() -> dict[str, int]:
    """Return {group_id: qsize} by running a one-liner inside the MCP container."""
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        (
            "import json, graphiti_mcp_server as s; "
            "print(json.dumps({k: q.qsize() for k, q in s.episode_queues.items()}))"
        ),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to exec docker command")
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        raise RuntimeError("Unexpected output: " + result.stdout)

def poll(interval: int):
    print("Polling Graphiti queue length every", interval, "seconds… (Ctrl+C to stop)")
    while True:
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            qlens = fetch_queue_lengths()
            if qlens:
                print(f"[{ts}] Queue lengths: {qlens}")
            else:
                print(f"[{ts}] Queue empty")
        except Exception as e:
            print(f"[{ts}] Error fetching queue length: {e}")
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Poll Graphiti episode queue length")
    parser.add_argument("--interval", type=int, default=10, help="Polling interval in seconds (default 10)")
    args = parser.parse_args()
    poll(args.interval) 