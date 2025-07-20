#!/usr/bin/env python3
"""
Simple batch processor that processes one file at a time.
Ensures LM Studio and Graphiti don't use the GPU simultaneously.
"""

import requests
import os
import time
import subprocess
import re
from add_memory import add_memory_via_lmstudio

def analyze_file_with_lmstudio(file_path: str, max_chars: int = 1000) -> str:
    """
    Step 1: Analyze file with LM Studio (uses GPU)
    """
    print(f"📝 Analyzing file: {file_path}")
    
    try:
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create prompt for analysis
        prompt = f"""Analyze this file and provide a brief summary:

File: {file_path}
Content: {content[:max_chars]}

Provide a concise summary of what this file does."""

        # Send to LM Studio
        payload = {
            "model": "qwen3-32b",
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        response = requests.post(
            "http://127.0.0.1:1234/v1/chat/completions", 
            json=payload, 
            timeout=300
        )
        response.raise_for_status()
        
        analysis = response.json()["choices"][0]["message"]["content"]
        print(f"✅ Analysis complete: {analysis[:100]}...")
        return analysis
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return f"Error analyzing {file_path}: {str(e)}"

def add_memory_to_graphiti(file_path: str, analysis: str) -> bool:
    """
    Step 2: Add memory to Graphiti (uses GPU)
    """
    print(f"💾 Adding memory to Graphiti: {file_path}")
    
    try:
        # Create prompt for memory addition
        prompt = f"Add a memory with name '{file_path}' and content: {analysis}"
        
        # Add memory via LM Studio integration
        result = add_memory_via_lmstudio(prompt)
        
        if "Memory added successfully" in result or "Memory queued for processing" in result:
            print(f"✅ Memory queued successfully")
            return True
        else:
            print(f"❌ Memory addition failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Memory addition error: {e}")
        return False

# ======== Queue-length helpers ========

def fetch_queue_len() -> int:
    """Return total queued episodes across all group_ids by running a one-liner inside the MCP container."""
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        (
            "import graphiti_mcp_server as s, sys; "
            "print(sum(q.qsize() for q in s.episode_queues.values()))"
        ),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip().isdigit():
        # If something goes wrong treat as unknown (return -1)
        return -1
    return int(result.stdout.strip())


def wait_for_graphiti_to_finish(poll_interval: int = 15) -> bool:
    """
    After we queue a memory, poll the *real* queue length every `poll_interval`
    seconds and print it until it drops to zero (all queued work finished).
    """
    print("⏳ Polling Graphiti queue… (Ctrl+C to abort)")

    while True:
        qlen = fetch_queue_len()
        ts = time.strftime("%H:%M:%S")
        if qlen == -1:
            print(f"[{ts}] ❓ Unable to fetch queue length")
        else:
            print(f"[{ts}] Queue length = {qlen}")
            if qlen == 0:
                print("✅ Queue empty – processing complete")
                return True
        time.sleep(poll_interval)

def process_single_file(file_path: str, max_chars: int = 1000) -> bool:
    """
    Process a single file completely before moving to the next.
    """
    print(f"\n{'='*60}")
    print(f"Processing: {file_path}")
    print(f"{'='*60}")
    
    # Step 1: Analyze with LM Studio (uses GPU)
    analysis = analyze_file_with_lmstudio(file_path, max_chars)
    
    # Brief pause to ensure GPU is free
    print("⏳ Brief pause to ensure GPU is available...")
    time.sleep(3)
    
    # Step 2: Add to Graphiti (uses GPU)
    if not add_memory_to_graphiti(file_path, analysis):
        return False
    
    # Step 3: Wait for Graphiti queue to drain
    if not wait_for_graphiti_to_finish():
        return False
    
    print(f"✅ File completed successfully: {file_path}")
    return True

def process_file_list(file_list_path: str = "file_list.txt", max_chars: int = 1000):
    """
    Process all files in the list, one at a time.
    """
    try:
        # Read file list
        with open(file_list_path, 'r') as f:
            file_paths = [line.strip() for line in f if line.strip()]
        
        print(f"Found {len(file_paths)} files to process")
        print("Processing one file at a time to avoid GPU contention")
        print("Each file will wait for Graphiti to finish processing before moving to the next")
        
        successful = 0
        failed = 0
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n📁 File {i}/{len(file_paths)}")
            
            if process_single_file(file_path, max_chars):
                successful += 1
            else:
                failed += 1
            
            # Brief pause between files
            if i < len(file_paths):
                print("⏳ Pause before next file...")
                time.sleep(2)
        
        # Summary
        print(f"\n{'='*60}")
        print(f"PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Total files: {len(file_paths)}")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Success rate: {(successful/len(file_paths)*100):.1f}%")
        
    except FileNotFoundError:
        print(f"File not found: {file_list_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple batch processor - one file at a time, no timeouts")
    parser.add_argument('--file-list', default='file_list.txt', help='File list path')
    parser.add_argument('--max-chars', type=int, default=1000, help='Max characters per file')
    
    args = parser.parse_args()
    
    process_file_list(args.file_list, args.max_chars) 