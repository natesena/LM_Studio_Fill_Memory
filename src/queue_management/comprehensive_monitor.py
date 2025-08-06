#!/usr/bin/env python3
"""
Comprehensive Graphiti monitoring script that shows:
1. Queue status (waiting items)
2. Currently processing episodes
3. Recent processing logs
4. Worker status

This provides complete visibility into the processing lifecycle.
"""

import subprocess
import json
import time
import argparse
from datetime import datetime
import os

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
        return {}
    try:
        return json.loads(result.stdout.strip() or "{}")
    except json.JSONDecodeError:
        return {}

def get_recent_logs(lines: int = 10) -> list[str]:
    """Get recent processing-related logs."""
    cmd = [
        "docker", "logs", "--tail", str(lines), "graphiti-graphiti-mcp-1"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        logs = result.stdout.strip().split('\n')
        
        # Filter for processing-related messages
        processing_logs = []
        for line in logs:
            if any(keyword in line for keyword in [
                "STARTING PROCESSING", 
                "FINISHED PROCESSING", 
                "Processing queued episode",
                "Episode processed successfully",
                "Error processing episode"
            ]):
                processing_logs.append(line.strip())
        
        return processing_logs[-5:]  # Return last 5 processing logs
    except:
        return []

def display_status():
    """Display comprehensive status information."""
    os.system('clear' if os.name == 'posix' else 'cls')
    
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"🔍 Graphiti Comprehensive Monitor - {ts}")
    print("=" * 80)
    
    # Get queue status
    status_data = fetch_queue_status()
    
    # Display queue and processing status
    print("\n📊 QUEUE & PROCESSING STATUS")
    print("-" * 40)
    
    if not status_data:
        print("No active queues found")
    else:
        for group_id, data in status_data.items():
            print(f"\n📁 Group: {group_id}")
            
            size = data.get('size', 0)
            items = data.get('items', [])
            worker_active = data.get('worker_active', False)
            currently_processing = data.get('currently_processing')
            
            # Currently processing
            if currently_processing:
                print(f"  🔄 Currently Processing: {currently_processing}")
            else:
                print(f"  🔄 Currently Processing: None")
            
            # Waiting items
            if size > 0:
                print(f"  ⏳ Waiting in queue: {size} items")
                if items:
                    print(f"     Next: {items[0]}")
            else:
                print(f"  ⏳ Waiting in queue: Empty")
            
            # Worker status
            worker_status = "🟢 ACTIVE" if worker_active else "🔴 INACTIVE"
            print(f"  👷 Worker: {worker_status}")
    
    # Display recent logs
    print("\n📝 RECENT PROCESSING LOGS")
    print("-" * 40)
    
    recent_logs = get_recent_logs(20)
    if recent_logs:
        for log in recent_logs:
            print(f"  {log}")
    else:
        print("  No recent processing logs found")
    
    print("\n" + "=" * 80)
    print("Press Ctrl+C to stop monitoring")

def monitor(interval: int):
    """Monitor continuously with the specified interval."""
    print(f"Starting comprehensive monitoring every {interval} seconds...")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            display_status()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Monitoring stopped")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Comprehensive Graphiti monitor")
    parser.add_argument("--interval", type=int, default=5, help="Update interval in seconds (default 5)")
    parser.add_argument("--once", action="store_true", help="Show status once and exit")
    args = parser.parse_args()
    
    if args.once:
        display_status()
    else:
        monitor(args.interval) 