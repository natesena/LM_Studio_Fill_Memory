#!/usr/bin/env python3
"""
One-time check of Graphiti queue and processing status.
Shows what's currently being processed and what's waiting.
"""

import subprocess
import json

def check_status():
    """Check current queue and processing status."""
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
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        status_data = json.loads(result.stdout.strip() or "{}")
        
        print("🔍 Graphiti Queue & Processing Status")
        print("=" * 50)
        
        if not status_data:
            print("No active queues found")
            return
        
        for group_id, data in status_data.items():
            print(f"\n📁 Group: {group_id}")
            print("-" * 30)
            
            size = data.get('size', 0)
            items = data.get('items', [])
            worker_active = data.get('worker_active', False)
            currently_processing = data.get('currently_processing')
            
            # Currently processing
            if currently_processing:
                print(f"🔄 Currently Processing: {currently_processing}")
            else:
                print("🔄 Currently Processing: None")
            
            # Waiting items
            if size > 0:
                print(f"⏳ Waiting in queue: {size} items")
                if items:
                    print(f"   Next up: {items[0]}")
                    if len(items) > 1:
                        print(f"   Also waiting: {', '.join(items[1:3])}{'...' if len(items) > 4 else ''}")
            else:
                print("⏳ Waiting in queue: Empty")
            
            # Worker status
            worker_status = "ACTIVE" if worker_active else "INACTIVE"
            print(f"👷 Worker: {worker_status}")
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error checking status: {e}")
        print(f"Stderr: {e.stderr}")
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing response: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    check_status() 