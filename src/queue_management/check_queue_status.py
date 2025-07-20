#!/usr/bin/env python3
"""
Simple script to check the Graphiti MCP server queue status.
"""

import requests
import json
import time
import argparse
from add_memory import check_queue_status, wait_for_queue_clearance

def main():
    parser = argparse.ArgumentParser(description="Check Graphiti MCP server queue status")
    parser.add_argument('--url', type=str, default='http://localhost:8000', 
                       help='Graphiti server URL (default: http://localhost:8000)')
    parser.add_argument('--wait', action='store_true', 
                       help='Wait for queue to clear')
    parser.add_argument('--max-wait', type=int, default=300, 
                       help='Maximum time to wait in seconds (default: 300)')
    parser.add_argument('--interval', type=int, default=10, 
                       help='Check interval in seconds (default: 10)')
    parser.add_argument('--continuous', action='store_true', 
                       help='Continuously monitor queue status')
    
    args = parser.parse_args()
    
    print(f"🔍 Checking Graphiti MCP server at: {args.url}")
    
    if args.continuous:
        print("📊 Continuous monitoring mode (Ctrl+C to stop)")
        try:
            while True:
                status = check_queue_status(args.url)
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Status: {status}")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n⏹️ Monitoring stopped")
    
    elif args.wait:
        print(f"⏳ Waiting for queue to clear (max {args.max_wait}s)...")
        success = wait_for_queue_clearance(args.url, args.max_wait, args.interval)
        if success:
            print("✅ Queue cleared successfully!")
        else:
            print("⚠️ Timeout reached, queue may still be processing")
    
    else:
        # Single status check
        status = check_queue_status(args.url)
        print(f"📊 Current Status: {json.dumps(status, indent=2)}")
        
        if status.get("status") == "ok":
            print("✅ Server is healthy and ready to process memories")
        else:
            print("⚠️ Server may be experiencing issues")
            print("💡 Try running with --wait to wait for queue clearance")

if __name__ == "__main__":
    main() 