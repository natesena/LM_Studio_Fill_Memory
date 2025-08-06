#!/usr/bin/env python3
"""
Enhanced Graphiti queue monitor that shows both waiting and currently processing episodes.
This provides visibility into the gap between add_episode() and task_done().
"""

import subprocess
import time
import json
import argparse
from datetime import datetime

def fetch_queue_status() -> dict:
    """Return comprehensive queue status including currently processing episodes."""
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        (
            "import json, graphiti_mcp_server as s; "
            "result = {}; "
            "[result.update({k: {'size': q.qsize(), 'items': s.queue_names.get(k, []), 'worker_active': s.queue_workers.get(k, False), 'currently_processing': s.currently_processing.get(k, None)}}) for k, q in s.episode_queues.items()]; "
            "print(json.dumps(result, indent=2))"
        ),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to exec docker command")
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        raise RuntimeError("Unexpected output: " + result.stdout)

def format_status(status_data: dict) -> str:
    """Format the status data into a readable string."""
    if not status_data:
        return "No active queues"
    
    lines = []
    for group_id, data in status_data.items():
        size = data.get('size', 0)
        items = data.get('items', [])
        worker_active = data.get('worker_active', False)
        currently_processing = data.get('currently_processing')
        
        status_parts = []
        
        # Show currently processing episode
        if currently_processing:
            status_parts.append(f"🔄 PROCESSING: {currently_processing}")
        
        # Show waiting items
        if size > 0:
            status_parts.append(f"⏳ WAITING: {size} items")
            if items:
                status_parts.append(f"   Next: {items[0]}")
        
        # Show worker status
        if worker_active:
            status_parts.append("👷 Worker: ACTIVE")
        else:
            status_parts.append("👷 Worker: INACTIVE")
        
        lines.append(f"Group '{group_id}': {' | '.join(status_parts)}")
    
    return "\n".join(lines)

def poll(interval: int):
    """Poll the queue status every interval seconds."""
    print(f"Enhanced Graphiti queue monitor - polling every {interval} seconds... (Ctrl+C to stop)")
    print("=" * 80)
    
    while True:
        ts = datetime.now().strftime("%H:%M:%S")
        try:
            status = fetch_queue_status()
            print(f"\n[{ts}] Queue Status:")
            print("-" * 40)
            print(format_status(status))
            print("-" * 40)
        except Exception as e:
            print(f"[{ts}] Error fetching queue status: {e}")
        
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Graphiti queue monitor")
    parser.add_argument("--interval", type=int, default=5, help="Polling interval in seconds (default 5)")
    args = parser.parse_args()
    poll(args.interval) 