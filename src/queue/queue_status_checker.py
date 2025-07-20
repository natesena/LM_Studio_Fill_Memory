#!/usr/bin/env python3
"""
Show exactly what the Graphiti queue looks like by parsing Docker logs.
"""

import subprocess
import re
from datetime import datetime

def get_queue_status():
    """
    Get the current queue status by parsing Docker logs.
    """
    try:
        # Get recent logs
        result = subprocess.run(
            ["docker", "logs", "--tail", "200", "graphiti-graphiti-mcp-1"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {"error": "Could not access Docker logs"}
        
        logs = result.stdout
        
        # Parse queue information
        queue_info = {
            "currently_processing": None,
            "recently_completed": [],
            "recent_errors": [],
            "queue_length": 0,
            "last_activity": None
        }
        
        # Find currently processing episode
        processing_matches = re.findall(r"Processing queued episode '([^']+)' for group_id: ([^\s]+)", logs)
        if processing_matches:
            queue_info["currently_processing"] = {
                "name": processing_matches[-1][0],  # Most recent
                "group_id": processing_matches[-1][1]
            }
        
        # Find recently completed episodes
        completed_matches = re.findall(r"Episode '([^']+)' processed successfully", logs)
        queue_info["recently_completed"] = completed_matches[-5:]  # Last 5
        
        # Find recent errors
        error_matches = re.findall(r"Error processing episode '([^']+)' for group_id ([^\s]+): ([^\n]+)", logs)
        queue_info["recent_errors"] = [
            {"name": m[0], "group_id": m[1], "error": m[2]} 
            for m in error_matches[-5:]  # Last 5
        ]
        
        # Estimate queue length by counting "Processing queued episode" messages
        # and subtracting completed/error ones
        total_processed = len(processing_matches)
        total_completed = len(completed_matches)
        total_errors = len(error_matches)
        
        # Rough estimate: if we're currently processing something, queue might have more
        if queue_info["currently_processing"]:
            queue_info["queue_length"] = "Unknown (processing in progress)"
        else:
            queue_info["queue_length"] = "0 (no active processing)"
        
        # Get last activity timestamp
        timestamp_matches = re.findall(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", logs)
        if timestamp_matches:
            queue_info["last_activity"] = timestamp_matches[-1]
        
        return queue_info
        
    except Exception as e:
        return {"error": f"Error checking queue: {str(e)}"}

def print_queue_status():
    """
    Print a clear view of the queue status.
    """
    print("=" * 60)
    print("GRAPHITI QUEUE STATUS")
    print("=" * 60)
    
    status = get_queue_status()
    
    if "error" in status:
        print(f"❌ Error: {status['error']}")
        return
    
    # Currently processing
    if status["currently_processing"]:
        current = status["currently_processing"]
        print(f"🔄 Currently Processing:")
        print(f"   Name: {current['name']}")
        print(f"   Group: {current['group_id']}")
    else:
        print("✅ No active processing")
    
    print()
    
    # Queue length
    print(f"📊 Queue Status: {status['queue_length']}")
    
    print()
    
    # Recently completed
    if status["recently_completed"]:
        print("✅ Recently Completed:")
        for episode in status["recently_completed"]:
            print(f"   - {episode}")
    else:
        print("❌ No recently completed episodes")
    
    print()
    
    # Recent errors
    if status["recent_errors"]:
        print("❌ Recent Errors:")
        for error in status["recent_errors"]:
            print(f"   - {error['name']}: {error['error']}")
    else:
        print("✅ No recent errors")
    
    print()
    
    # Last activity
    if status["last_activity"]:
        print(f"🕐 Last Activity: {status['last_activity']}")
    
    print("=" * 60)

if __name__ == "__main__":
    print_queue_status() 