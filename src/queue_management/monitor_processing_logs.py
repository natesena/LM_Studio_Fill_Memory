#!/usr/bin/env python3
"""
Monitor Graphiti processing logs in real-time to see episode processing lifecycle.
This shows the STARTING PROCESSING and FINISHED PROCESSING log messages.
"""

import subprocess
import time
import argparse
from datetime import datetime

def monitor_logs():
    """Monitor Graphiti container logs for processing messages."""
    cmd = [
        "docker", "logs", "-f", "--tail", "0", "graphiti-graphiti-mcp-1"
    ]
    
    print("🔍 Monitoring Graphiti processing logs... (Ctrl+C to stop)")
    print("=" * 60)
    print("Looking for: 🔄 STARTING PROCESSING and ✅ FINISHED PROCESSING messages")
    print("=" * 60)
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        for line in process.stdout:
            # Filter for processing-related messages
            if any(keyword in line for keyword in [
                "STARTING PROCESSING", 
                "FINISHED PROCESSING", 
                "Processing queued episode",
                "Episode processed successfully",
                "Error processing episode"
            ]):
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] {line.strip()}")
                
    except KeyboardInterrupt:
        print("\n🛑 Log monitoring stopped")
    except Exception as e:
        print(f"❌ Error monitoring logs: {e}")
    finally:
        if process:
            process.terminate()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Monitor Graphiti processing logs")
    args = parser.parse_args()
    monitor_logs() 