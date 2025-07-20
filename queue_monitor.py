#!/usr/bin/env python3
"""
Proper Graphiti queue monitoring script.
Monitors the actual queue status and waits for processing completion.
"""

import requests
import json
import time
import argparse
import subprocess
import re
from typing import Dict, Any, Optional

class GraphitiQueueMonitor:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.sse_url = f"{base_url}/sse"
        
    def check_queue_status_via_logs(self) -> Dict[str, Any]:
        """
        Check queue status by monitoring Docker logs for processing messages.
        This is the most reliable way to see what's actually happening.
        """
        try:
            # Get recent logs from the Graphiti MCP container
            result = subprocess.run(
                ["docker", "logs", "--tail", "50", "graphiti-graphiti-mcp-1"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {"status": "error", "message": "Could not access Docker logs"}
            
            logs = result.stdout
            
            # Look for queue-related messages
            queue_patterns = {
                "processing": r"Processing queued episode '([^']+)' for group_id: ([^\s]+)",
                "completed": r"Episode '([^']+)' processed successfully",
                "worker_started": r"Starting episode queue worker for group_id: ([^\s]+)",
                "worker_stopped": r"Stopped episode queue worker for group_id: ([^\s]+)",
                "errors": r"Error processing queued episode for group_id ([^\s]+): ([^\n]+)"
            }
            
            status = {
                "status": "unknown",
                "message": "Queue status unclear",
                "processing": [],
                "completed": [],
                "workers": [],
                "errors": []
            }
            
            # Extract information from logs
            for pattern_name, pattern in queue_patterns.items():
                matches = re.findall(pattern, logs)
                if pattern_name == "processing":
                    status["processing"] = [{"name": m[0], "group_id": m[1]} for m in matches]
                elif pattern_name == "completed":
                    status["completed"] = [m for m in matches]
                elif pattern_name == "worker_started":
                    status["workers"].extend([{"group_id": m, "status": "running"} for m in matches])
                elif pattern_name == "worker_stopped":
                    status["workers"].extend([{"group_id": m, "status": "stopped"} for m in matches])
                elif pattern_name == "errors":
                    status["errors"] = [{"group_id": m[0], "error": m[1]} for m in matches]
            
            # Determine overall status
            if status["errors"]:
                status["status"] = "error"
                status["message"] = f"Found {len(status['errors'])} processing errors"
            elif status["processing"]:
                status["status"] = "processing"
                status["message"] = f"Processing {len(status['processing'])} episodes"
            elif status["workers"] and any(w["status"] == "running" for w in status["workers"]):
                status["status"] = "idle"
                status["message"] = "Queue worker running but no active processing"
            else:
                status["status"] = "unknown"
                status["message"] = "No queue activity detected"
            
            return status
            
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "Docker logs command timed out"}
        except FileNotFoundError:
            return {"status": "error", "message": "Docker not found or not accessible"}
        except Exception as e:
            return {"status": "error", "message": f"Error checking logs: {str(e)}"}
    
    def wait_for_queue_empty(self, timeout: int = 300, check_interval: int = 5) -> bool:
        """
        Wait for the queue to be empty (no active processing).
        
        Args:
            timeout: Maximum time to wait in seconds
            check_interval: How often to check in seconds
            
        Returns:
            bool: True if queue is empty, False if timeout reached
        """
        print(f"⏳ Waiting for queue to be empty (max {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.check_queue_status_via_logs()
            
            if status["status"] == "error":
                print(f"⚠️ Error checking queue: {status['message']}")
            elif status["status"] == "idle" or (status["status"] == "unknown" and not status["processing"]):
                print("✅ Queue appears to be empty")
                return True
            elif status["status"] == "processing":
                processing_count = len(status["processing"])
                remaining = timeout - (time.time() - start_time)
                print(f"⏳ {processing_count} episodes still processing... {remaining:.0f}s remaining")
            else:
                remaining = timeout - (time.time() - start_time)
                print(f"⏳ Queue status unclear... {remaining:.0f}s remaining")
            
            time.sleep(check_interval)
        
        print(f"⚠️ Timeout reached ({timeout}s), queue may still be processing")
        return False
    
    def wait_for_specific_episode(self, episode_name: str, timeout: int = 300, check_interval: int = 5) -> bool:
        """
        Wait for a specific episode to be processed.
        
        Args:
            episode_name: Name of the episode to wait for
            timeout: Maximum time to wait in seconds
            check_interval: How often to check in seconds
            
        Returns:
            bool: True if episode was processed, False if timeout reached
        """
        print(f"⏳ Waiting for episode to be processed: {episode_name}")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.check_queue_status_via_logs()
            
            # Check if episode was completed
            if episode_name in status["completed"]:
                print(f"✅ Episode processed successfully: {episode_name}")
                return True
            
            # Check if episode is still being processed
            if any(ep["name"] == episode_name for ep in status["processing"]):
                remaining = timeout - (time.time() - start_time)
                print(f"⏳ Episode still processing... {remaining:.0f}s remaining")
            else:
                remaining = timeout - (time.time() - start_time)
                print(f"⏳ Episode not found in processing queue... {remaining:.0f}s remaining")
            
            time.sleep(check_interval)
        
        print(f"⚠️ Timeout reached ({timeout}s), episode may not have been processed")
        return False
    
    def get_queue_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current queue status.
        """
        status = self.check_queue_status_via_logs()
        
        summary = {
            "overall_status": status["status"],
            "message": status["message"],
            "processing_count": len(status["processing"]),
            "completed_count": len(status["completed"]),
            "worker_count": len([w for w in status["workers"] if w["status"] == "running"]),
            "error_count": len(status["errors"]),
            "processing_episodes": status["processing"],
            "recent_errors": status["errors"][-3:] if status["errors"] else []
        }
        
        return summary

def main():
    parser = argparse.ArgumentParser(description="Monitor Graphiti queue status")
    parser.add_argument('--url', type=str, default='http://localhost:8000', 
                       help='Graphiti server URL (default: http://localhost:8000)')
    parser.add_argument('--wait-empty', action='store_true', 
                       help='Wait for queue to be empty')
    parser.add_argument('--wait-episode', type=str, 
                       help='Wait for a specific episode to be processed')
    parser.add_argument('--max-wait', type=int, default=300, 
                       help='Maximum time to wait in seconds (default: 300)')
    parser.add_argument('--interval', type=int, default=5, 
                       help='Check interval in seconds (default: 5)')
    parser.add_argument('--continuous', action='store_true', 
                       help='Continuously monitor queue status')
    parser.add_argument('--summary', action='store_true', 
                       help='Show queue summary')
    
    args = parser.parse_args()
    
    monitor = GraphitiQueueMonitor(args.url)
    
    if args.continuous:
        print("📊 Continuous queue monitoring mode (Ctrl+C to stop)")
        try:
            while True:
                status = monitor.check_queue_status_via_logs()
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] {status['status']}: {status['message']}")
                if status["processing"]:
                    print(f"  Processing: {[ep['name'] for ep in status['processing']]}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n⏹️ Monitoring stopped")
    
    elif args.wait_empty:
        success = monitor.wait_for_queue_empty(args.max_wait, args.interval)
        if success:
            print("✅ Queue is now empty!")
        else:
            print("⚠️ Queue may still be processing")
    
    elif args.wait_episode:
        success = monitor.wait_for_specific_episode(args.wait_episode, args.max_wait, args.interval)
        if success:
            print("✅ Episode processed successfully!")
        else:
            print("⚠️ Episode may not have been processed")
    
    elif args.summary:
        summary = monitor.get_queue_summary()
        print("📊 Queue Summary:")
        print(f"  Status: {summary['overall_status']}")
        print(f"  Message: {summary['message']}")
        print(f"  Processing: {summary['processing_count']} episodes")
        print(f"  Completed: {summary['completed_count']} episodes")
        print(f"  Workers: {summary['worker_count']} running")
        print(f"  Errors: {summary['error_count']}")
        
        if summary['processing_episodes']:
            print("  Currently Processing:")
            for ep in summary['processing_episodes']:
                print(f"    - {ep['name']} (group: {ep['group_id']})")
        
        if summary['recent_errors']:
            print("  Recent Errors:")
            for error in summary['recent_errors']:
                print(f"    - {error['group_id']}: {error['error']}")
    
    else:
        # Single status check
        status = monitor.check_queue_status_via_logs()
        print(f"📊 Queue Status: {json.dumps(status, indent=2)}")

if __name__ == "__main__":
    main() 