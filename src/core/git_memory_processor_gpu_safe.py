#!/usr/bin/env python3
"""
Git Memory Processor with GPU Queue Management

This script processes Git commit data and creates individual memories for each commit
using the Graphiti MCP tool, with proper GPU queue monitoring to avoid contention.
Each commit becomes a discrete memory with its own timestamp, allowing the knowledge 
graph to track the evolution of the codebase over time.

This integrates with the existing batch processing infrastructure to ensure only
one GPU process at a time.
"""

import json
import subprocess
import sys
import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
import re

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
from core.memory_adder import add_memory_via_lmstudio
from utils.neo4j_utils import Neo4jVerifier

def check_queue_status() -> dict:
    """
    Check queue status using the new HTTP endpoint.
    Returns dict with queue information.
    """
    try:
        response = requests.get("http://localhost:8100/queue/status", timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️ Error checking queue status: {e}")
        return {"group_queues": {}}

def check_ollama_gpu_usage() -> dict:
    """
    Check if Ollama is currently using GPU resources by monitoring docker stats.
    
    Returns:
        Dictionary with GPU usage information
    """
    try:
        # Get Ollama container stats
        result = subprocess.run([
            "docker", "stats", "--no-stream", "--format", 
            "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {"error": f"Docker stats failed: {result.stderr}", "is_processing": False}
        
        # Parse the output to find Ollama container
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if 'graphiti-ollama-1' in line:
                # Split by multiple spaces and filter out empty strings
                parts = [part for part in line.split('  ') if part.strip()]
                if len(parts) >= 3:
                    container_name = parts[0].strip()
                    cpu_percent = parts[1].strip().replace('%', '')
                    mem_usage = parts[2].strip()
                    
                    # Convert CPU percentage to float
                    try:
                        cpu_float = float(cpu_percent)
                        # Consider "processing" if CPU > 1% (above idle threshold)
                        is_processing = cpu_float > 1.0
                        
                        return {
                            "container": container_name,
                            "cpu_percent": cpu_float,
                            "memory_usage": mem_usage,
                            "is_processing": is_processing,
                            "error": None
                        }
                    except ValueError:
                        return {"error": f"Invalid CPU value: {cpu_percent}", "is_processing": False}
        
        return {"error": "Ollama container not found", "is_processing": False}
        
    except subprocess.TimeoutExpired:
        return {"error": "Docker stats timeout", "is_processing": False}
    except Exception as e:
        return {"error": f"Error checking GPU usage: {str(e)}", "is_processing": False}

def wait_for_ollama_idle(timeout: int = 300, check_interval: int = 5) -> bool:
    """
    Wait for Ollama to become idle (not using GPU) before starting new processing.
    
    Args:
        timeout: Maximum time to wait in seconds
        check_interval: How often to check in seconds
    
    Returns:
        True if Ollama became idle, False if timeout
    """
    print("🔍 Checking Ollama GPU usage...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        gpu_data = check_ollama_gpu_usage()
        
        if gpu_data.get("error"):
            print(f"⚠️ GPU monitoring error: {gpu_data['error']}")
            # If we can't check GPU usage, assume it's safe to proceed
            print("✅ Proceeding anyway (GPU monitoring unavailable)...")
            return True
        
        if not gpu_data.get("is_processing", False):
            cpu_percent = gpu_data.get("cpu_percent", 0)
            print(f"✅ Ollama idle (CPU: {cpu_percent:.1f}%)")
            return True
        else:
            elapsed = int(time.time() - start_time)
            cpu_percent = gpu_data.get("cpu_percent", 0)
            print(f"\r⏳ Ollama processing (CPU: {cpu_percent:.1f}%) – waiting... ({elapsed}s)", end="", flush=True)
            time.sleep(check_interval)
    
    print(f"\n⚠️ Ollama GPU timeout after {timeout}s")
    return False

def wait_for_safe_processing(check_interval: int = 5) -> bool:
    """
    Simplified approach: Wait for Ollama to be idle (GPU monitoring only).
    Since queue status API is broken, we rely on GPU monitoring.
    No artificial timeout - let natural system timeouts handle it.
    
    Args:
        check_interval: How often to check in seconds
    
    Returns:
        True when GPU is idle, False if interrupted
    """
    print("🔍 GPU MONITORING: Waiting for Ollama to be idle...")
    
    while True:
        gpu_data = check_ollama_gpu_usage()
        
        if gpu_data.get("error"):
            print(f"⚠️ GPU monitoring error: {gpu_data['error']}")
            print("✅ Proceeding anyway (GPU monitoring unavailable)...")
            return True
        
        if not gpu_data.get("is_processing", False):
            cpu_percent = gpu_data.get("cpu_percent", 0)
            print(f"✅ GPU available (CPU: {cpu_percent:.1f}%)")
            return True
        else:
            cpu_percent = gpu_data.get("cpu_percent", 0)
            print(f"\r⏳ GPU busy (CPU: {cpu_percent:.1f}%) – waiting...", end="", flush=True)
            time.sleep(check_interval)

def get_git_log_data(repo_path: str, since: str = "1 week ago") -> str:
    """Get Git log data for the specified repository and time period."""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--stat", "--format=fuller"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error getting Git log: {e}")
        return ""

def parse_git_log(git_log_output: str) -> List[Dict]:
    """Parse Git log output into structured commit data."""
    commits = []
    current_commit = {}
    lines = git_log_output.strip().split('\n')
    
    for line in lines:
        if line.startswith('commit '):
            # Save previous commit if exists
            if current_commit:
                commits.append(current_commit)
            
            # Start new commit
            commit_hash = line.split()[1]
            current_commit = {
                'hash': commit_hash,
                'author': '',
                'date': '',
                'message': '',
                'files_changed': [],
                'insertions': 0,
                'deletions': 0
            }
        
        elif line.startswith('Author: '):
            current_commit['author'] = line.replace('Author: ', '').strip()
        
        elif line.startswith('Date: '):
            date_str = line.replace('Date: ', '').strip()
            try:
                # Parse date string like "Sun Aug 3 22:41:25 2025 -0400"
                dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
                current_commit['date'] = dt.isoformat()
            except:
                current_commit['date'] = date_str
        
        elif line.startswith('    ') and not line.startswith('    ' * 2):
            # This is part of the commit message
            current_commit['message'] += line.strip() + '\n'
        
        elif line and not line.startswith(' ') and '|' in line:
            # This is a file change line like "src/file.js | 10 +++++-----"
            parts = line.split('|')
            if len(parts) == 2:
                filename = parts[0].strip()
                change_info = parts[1].strip()
                
                # Parse change info like "10 +++++-----"
                change_match = re.match(r'(\d+)\s*(\+*)(-*)', change_info)
                if change_match:
                    insertions = len(change_match.group(2))
                    deletions = len(change_match.group(3))
                    current_commit['files_changed'].append({
                        'filename': filename,
                        'insertions': insertions,
                        'deletions': deletions
                    })
                    current_commit['insertions'] += insertions
                    current_commit['deletions'] += deletions
    
    # Add the last commit
    if current_commit:
        commits.append(current_commit)
    
    return commits

def categorize_commit(commit_message: str) -> str:
    """Categorize commit based on its message."""
    message_lower = commit_message.lower()
    
    if any(word in message_lower for word in ['fix', 'bug', 'resolve', 'correct']):
        return "bug_fix"
    elif any(word in message_lower for word in ['feat', 'add', 'implement', 'create']):
        return "feature"
    elif any(word in message_lower for word in ['docs', 'documentation']):
        return "documentation"
    elif any(word in message_lower for word in ['refactor', 'restructure']):
        return "refactoring"
    elif any(word in message_lower for word in ['cleanup', 'remove', 'delete']):
        return "cleanup"
    else:
        return "other"

def create_commit_memory_content(commit_data: Dict) -> str:
    """Create structured memory content for a single commit."""
    category = categorize_commit(commit_data['message'])
    
    # Create structured memory content
    memory_content = {
        "commit_hash": commit_data['hash'],
        "author": commit_data['author'],
        "date": commit_data['date'],
        "category": category,
        "message": commit_data['message'].strip(),
        "files_changed": commit_data['files_changed'],
        "total_insertions": commit_data['insertions'],
        "total_deletions": commit_data['deletions'],
        "impact_summary": f"Modified {len(commit_data['files_changed'])} files with {commit_data['insertions']} insertions and {commit_data['deletions']} deletions"
    }
    
    return json.dumps(memory_content, indent=2)

def add_commit_to_graphiti_with_gpu_monitoring(commit_data: Dict, lmstudio_delay: int = 5) -> bool:
    """Add a single commit to Graphiti using GPU monitoring."""
    try:
        category = categorize_commit(commit_data['message'])
        memory_name = f"Git Commit: {commit_data['hash'][:8]} - {category.replace('_', ' ').title()}"
        episode_body = create_commit_memory_content(commit_data)
        
        print(f"Adding memory to Graphiti: {memory_name}")
        print(f"Commit: {commit_data['hash'][:8]}")
        print(f"Date: {commit_data['date']}")
        print(f"Category: {category}")
        print(f"Files changed: {len(commit_data['files_changed'])}")
        
        # Wait for safe processing conditions (GPU idle)
        if not wait_for_safe_processing():
            print(f"⚠️ Skipping commit {commit_data['hash'][:8]} - GPU busy")
            return False
        
        # Add memory using the existing infrastructure
        prompt = f"Please add a memory with the name '{memory_name}' and the following content: '{episode_body}'"
        
        result = add_memory_via_lmstudio(
            prompt, 
            rate_limit_delay=0,  # No additional delay since we're controlling timing
            check_queue=False    # We're doing manual queue monitoring
        )
        
        if "Memory added successfully" in result or "Memory queued for processing" in result:
            print(f"✅ Memory queued: {memory_name}")
            
            # Wait for GPU to be available for next operation
            print(f"⏳ Waiting {lmstudio_delay}s for GPU to be available...")
            time.sleep(lmstudio_delay)
            
            return True
        else:
            print(f"❌ Failed to add memory: {memory_name}")
            return False
        
    except Exception as e:
        print(f"Error adding commit {commit_data['hash'][:8]} to Graphiti: {e}")
        return False

def process_git_commits_with_gpu_monitoring(repo_path: str, since: str = "1 week ago", lmstudio_delay: int = 5) -> List[Dict]:
    """Process Git commits and add each one to Graphiti with GPU monitoring."""
    print(f"Processing Git commits from {repo_path} since {since}...")
    print(f"GPU contention prevention: {lmstudio_delay}s delay between operations")
    
    # Get Git log data
    git_log = get_git_log_data(repo_path, since)
    if not git_log:
        print("No Git log data found.")
        return []
    
    # Parse commits
    commits = parse_git_log(git_log)
    print(f"Found {len(commits)} commits to process.")
    
    # Wait for safe processing before starting
    print("\n=== Checking initial GPU status ===")
    if not wait_for_safe_processing():
        print("⚠️ System may still be processing, proceeding anyway...")
    
    # Add each commit to Graphiti with GPU monitoring
    successful_memories = []
    for i, commit in enumerate(commits, 1):
        print(f"\n=== Processing commit {i}/{len(commits)}: {commit['hash'][:8]} ===")
        
        if add_commit_to_graphiti_with_gpu_monitoring(commit, lmstudio_delay):
            successful_memories.append(commit)
            print(f"✅ Successfully added memory for commit {commit['hash'][:8]}")
        else:
            print(f"❌ Failed to add memory for commit {commit['hash'][:8]}")
    
    print(f"\nSuccessfully created {len(successful_memories)} memory entries.")
    return successful_memories

def main():
    """Main function to process Git commits with GPU monitoring."""
    if len(sys.argv) < 2:
        print("Usage: python git_memory_processor_gpu_safe.py <repo_path> [since] [delay]")
        print("Example: python git_memory_processor_gpu_safe.py /path/to/repo '1 week ago' 5")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    since = sys.argv[2] if len(sys.argv) > 2 else "1 week ago"
    lmstudio_delay = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    
    try:
        successful_memories = process_git_commits_with_gpu_monitoring(repo_path, since, lmstudio_delay)
        
        # Save successful memories to file for reference
        output_file = f"git_memories_gpu_safe_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(successful_memories, f, indent=2)
        
        print(f"Git memory data saved to {output_file}")
        
    except Exception as e:
        print(f"Error processing Git commits: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 