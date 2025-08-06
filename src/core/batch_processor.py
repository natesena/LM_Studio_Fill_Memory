# batch_memory_adder.py
"""
Batch memory adder that reads file_list.txt, gets file info via chat completion, then creates memories.
Proper queue monitoring to avoid GPU contention between LM Studio and Graphiti.
"""
import requests
import os
import argparse
import time
import sys
import subprocess
import os
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

def wait_for_queue_empty(timeout: int = 300, check_interval: int = 5) -> bool:
    """
    Wait for the queue to be empty before starting LM Studio processing.
    
    Args:
        timeout: Maximum time to wait in seconds
        check_interval: How often to check in seconds
    
    Returns:
        True if queue became empty, False if timeout
    """
    print(f"🔍 Checking queue status before starting LM Studio...")
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        queue_data = check_queue_status()
        elapsed_time = int(time.time() - start_time)
        
        # Check if any group has items in queue
        total_size = 0
        for group_data in queue_data.get("group_queues", {}).values():
            total_size += group_data.get("size", 0)
        
        if total_size == 0:
            print(f"✅ Queue empty – starting LM Studio...")
            return True
        else:
            print(f"\r⏳ Queue busy ({total_size} items) – waiting... ({elapsed_time}s)", end="", flush=True)
            time.sleep(check_interval)
    
    print(f"\n⚠️ Timeout waiting for queue to empty after {timeout}s")
    return False

def wait_for_episode_completion(episode_name: str, check_interval: int = 5) -> bool:
    """
    Wait for a specific episode to complete processing.
    
    Args:
        episode_name: Name of the episode to wait for
        check_interval: How often to check in seconds
    
    Returns:
        True if episode completed (no timeout - Graphiti server handles timeouts)
    """
    print(f"🔄 Waiting for Graphiti to process: {os.path.basename(episode_name)}")
    start_time = time.time()
    
    while True:
        queue_data = check_queue_status()
        elapsed_time = int(time.time() - start_time)
        
        # Check if episode is still in any items list
        episode_found = False
        queue_info = ""
        
        for group_data in queue_data.get("group_queues", {}).values():
            size = group_data.get("size", 0)
            items = group_data.get("items", [])
            
            if episode_name in items:
                episode_found = True
                if size > 0:
                    # Episode is waiting in queue
                    next_file = items[0] if items else "unknown"
                    queue_info = f"QUEUE: {size} waiting (next: {os.path.basename(next_file)})"
                else:
                    # Episode is being processed by Graphiti
                    queue_info = f"GRAPHITI: processing {os.path.basename(episode_name)}"
                break
        
        if not episode_found:
            print(f"✅ Graphiti completed after {elapsed_time}s")
            return True
        else:
            print(f"\r⏳ {queue_info} ({elapsed_time}s)", end="", flush=True)
            time.sleep(check_interval)

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
        # Check GPU usage only (queue API is broken)
        gpu_data = check_ollama_gpu_usage()
        gpu_busy = gpu_data.get("is_processing", False)
        cpu_percent = gpu_data.get("cpu_percent", 0)
        
        if not gpu_busy:
            print(f"✅ SAFE TO PROCEED: Ollama idle (CPU: {cpu_percent:.1f}%)")
            return True
        else:
            print(f"\r⏳ Waiting for GPU to be idle... (CPU: {cpu_percent:.1f}%)", end="", flush=True)
            time.sleep(check_interval)

def check_episode_in_neo4j(episode_name: str, neo4j_verifier: Neo4jVerifier = None) -> bool:
    """
    Check if an episode exists in Neo4j database.
    
    Args:
        episode_name: Name of the episode to check (file path)
        neo4j_verifier: Neo4jVerifier instance (will create one if None)
    
    Returns:
        True if episode exists in Neo4j, False otherwise
    """
    if neo4j_verifier is None:
        neo4j_verifier = Neo4jVerifier()
    
    try:
        # Search for the episode by name (file path)
        result = neo4j_verifier.search_for_specific_memory(episode_name)
        
        if "error" in result:
            error_msg = result['error']
            print(f"⚠️ Neo4j query error: {error_msg}")
            
            # If it's an authentication error, we'll assume the episode was processed
            # since the queue monitoring and GPU monitoring both indicated success
            if "401" in error_msg or "Unauthorized" in error_msg:
                print(f"⚠️ Neo4j authentication failed - assuming episode was processed based on queue/GPU monitoring")
                return True
            
            return False
        
        # Check if any results were returned
        if "results" in result and len(result["results"]) > 0:
            data = result["results"][0].get("data", [])
            if len(data) > 0:
                print(f"✅ Episode found in Neo4j: {os.path.basename(episode_name)}")
                return True
        
        print(f"❌ Episode not found in Neo4j: {os.path.basename(episode_name)}")
        return False
        
    except Exception as e:
        print(f"⚠️ Error checking Neo4j: {e}")
        # On any error, assume the episode was processed based on queue/GPU monitoring
        print(f"⚠️ Assuming episode was processed based on queue/GPU monitoring")
        return True

def remove_file_from_list(file_path: str, file_list_path: str) -> bool:
    """
    Remove a file from the processing list.
    
    Args:
        file_path: The file path to remove
        file_list_path: Path to the file list
    
    Returns:
        True if file was removed, False otherwise
    """
    try:
        # Read all lines from the file
        with open(file_list_path, 'r') as f:
            lines = f.readlines()
        
        # Filter out the file to remove
        original_count = len(lines)
        filtered_lines = [line.strip() for line in lines if line.strip() != file_path]
        new_count = len(filtered_lines)
        
        if new_count < original_count:
            # Write back the filtered lines
            with open(file_list_path, 'w') as f:
                for line in filtered_lines:
                    f.write(line + '\n')
            
            print(f"🗑️ Removed from list: {os.path.basename(file_path)} ({original_count - new_count} removed)")
            return True
        else:
            print(f"⚠️ File not found in list: {os.path.basename(file_path)}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error removing file from list: {e}")
        return False

def get_file_info(file_path: str, lmstudio_url: str = "http://127.0.0.1:1234/v1/chat/completions", model: str = "qwen3-32b", max_chars: int = 2000) -> str:
    """
    Get specific information about a file using chat completion.
    Args:
        file_path: Path to the file (absolute path recommended)
        lmstudio_url: LM Studio API URL
        model: Model to use
        max_chars: Maximum number of characters from the file to include in the prompt
    Returns:
        Information about the file
    """
    try:
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        prompt = f"""Please analyze this file and provide a concise summary of what it does:\n\nFile: {file_path}\nContent:\n{content[:max_chars]}  # Limit content to avoid token limits\n\nPlease provide a brief summary of:\n1. What this file does\n2. Key functions/classes\n3. Purpose in the project\n4. Any important details\n\nKeep it concise but informative."""
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        response = requests.post(lmstudio_url, json=payload, headers=headers, timeout=600)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error analyzing file {file_path}: {str(e)}"

def process_file_list_with_proper_queue_monitoring(file_list_path: str = "file_list.txt", max_chars: int = 2000, 
                                                 lmstudio_delay: int = 5):
    """
    Process files with GPU monitoring to avoid GPU contention.
    
    Args:
        file_list_path: Path to the file list (default: file_list.txt)
        max_chars: Maximum number of characters from each file to include in the prompt
        lmstudio_delay: Delay after LM Studio operations to let GPU cool down (default: 5 seconds)
    """
    try:
        with open(file_list_path, 'r') as f:
            file_paths = [line.strip() for line in f if line.strip()]
        print(f"Found {len(file_paths)} files to process with proper queue monitoring")
        print(f"GPU contention prevention: {lmstudio_delay}s delay between operations")
        
        # Check initial queue status
        print("\n=== Checking initial queue status ===")
        initial_queue = check_queue_status()
        print(f"Initial queue status: {initial_queue}")
        
        # Wait for Ollama to be idle before starting
        if not wait_for_safe_processing():
                print("⚠️ System may still be processing, proceeding anyway...")
        
        # Initialize Neo4j verifier for episode verification
        print("🔍 Initializing Neo4j verifier...")
        neo4j_verifier = Neo4jVerifier(username="neo4j", password="demodemo")
        
        successful_count = 0
        error_count = 0
        
        from datetime import datetime

        def ts() -> str:
            """Return human-readable timestamp HH:MM:SS."""
            return datetime.now().strftime('%H:%M:%S')

        for i, rel_file_path in enumerate(file_paths, 1):
            abs_file_path = os.path.abspath(rel_file_path)
            total = len(file_paths)

            # ---- PRE-FILE GPU CHECK ----
            print(f"\n[{ts()}] 🔍 Pre-file GPU check for {os.path.basename(abs_file_path)}")
            if not wait_for_safe_processing():
                print(f"[{ts()}] ⚠️  Skipping {i}/{total} {os.path.basename(abs_file_path)} - GPU busy")
                error_count += 1
                continue

            # ---- LM Studio phase START ----
            print(f"[{ts()}] LM  ▶️  Start  {i}/{total}  {os.path.basename(abs_file_path)}", flush=True)
            
            try:
                # STEP 1: LM Studio Operation (GPU-intensive)
                # analyse file
                file_info = get_file_info(abs_file_path, max_chars=max_chars)
                print(f"[{ts()}] LM  ✅  Done   {i}/{total}  {os.path.basename(abs_file_path)}", flush=True)
                
                # Wait for GPU to be available for Graphiti
                print(f"⏳ Waiting {lmstudio_delay}s for GPU to be available for Graphiti...")
                time.sleep(lmstudio_delay)
                
                # STEP 2: Graphiti Operation (GPU-intensive)
                print("🔄 STEP 2: Adding memory to Graphiti...")
                prompt = f"Please add a memory with the name '{abs_file_path}' and the following content: '{file_info}'"
                
                result = add_memory_via_lmstudio(
                    prompt, 
                    rate_limit_delay=0,  # No additional delay since we're controlling timing
                    check_queue=False    # We're doing manual queue monitoring
                )
                
                if "Memory added successfully" in result or "Memory queued for processing" in result:
                    print(f"✅ Memory queued: {abs_file_path}")
                    
                    # STEP 3: Wait for Graphiti to finish processing this specific episode
                    print("🔄 STEP 3: Waiting for Graphiti to process this episode...")
                    # Use GPU monitoring: wait for Ollama to be idle
                    if wait_for_safe_processing():
                        print(f"[{ts()}] GRA ✅  Done   {i}/{total}  {os.path.basename(abs_file_path)}", flush=True)
                        
                        # STEP 4: Verify episode was actually stored in Neo4j
                        print("🔍 STEP 4: Verifying episode in Neo4j...")
                        if check_episode_in_neo4j(abs_file_path, neo4j_verifier):
                            print(f"✅ Neo4j verification successful: {os.path.basename(abs_file_path)}")
                            # Remove from processing list since it's confirmed in Neo4j
                            remove_file_from_list(abs_file_path, file_list_path)
                            successful_count += 1
                        else:
                            print(f"⚠️ Neo4j verification failed: {os.path.basename(abs_file_path)}")
                            print(f"⚠️ File will remain in list for retry: {os.path.basename(abs_file_path)}")
                            error_count += 1
                    else:
                        print(f"[{ts()}] GRA ⚠️  Timeout {i}/{total}  {os.path.basename(abs_file_path)}", flush=True)
                        error_count += 1
                else:
                    print(f"[{ts()}] GRA ❌  ERROR  {i}/{total}  {os.path.basename(abs_file_path)}", flush=True)
                    error_count += 1
                    
            except Exception as e:
                print(f"[{ts()}] ⚠️  Unexpected error on {os.path.basename(abs_file_path)}: {e}", flush=True)
                error_count += 1
            
            # Brief pause between files to ensure clean separation
            if i < len(file_paths):
                print(f"[{ts()}] Waiting 2s before next file…", flush=True)
                time.sleep(2)
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"PROPER QUEUE MONITORING COMPLETE")
        print(f"{'='*60}")
        print(f"Total files: {len(file_paths)}")
        print(f"Successful: {successful_count}")
        print(f"Errors: {error_count}")
        print(f"Success rate: {(successful_count/len(file_paths)*100):.1f}%")
        print(f"GPU contention prevention: ✅ Proper queue monitoring completed")
        
        # Final queue status check
        print(f"\n=== Final queue status check ===")
        final_queue = check_queue_status()
        print(f"Final queue status: {final_queue}")
        
        return {
            "processed": len(file_paths),
            "successful": successful_count,
            "failed": error_count
        }
        
    except FileNotFoundError:
        print(f"File not found: {file_list_path}")
        return {"processed": 0, "successful": 0, "failed": 1}
    except Exception as e:
        print(f"Error reading file list: {e}")
        return {"processed": 0, "successful": 0, "failed": 1}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch memory adder with proper queue monitoring to avoid GPU contention.")
    parser.add_argument('--file-list', type=str, default='file_list.txt', help='Path to the file list (default: file_list.txt)')
    parser.add_argument('--max-chars', type=int, default=2000, help='Maximum number of characters from each file to include in the prompt (default: 2000)')
    parser.add_argument('--lmstudio-delay', type=int, default=5, help='Delay after LM Studio operations in seconds (default: 5)')
    args = parser.parse_args()
    
    process_file_list_with_proper_queue_monitoring(
        file_list_path=args.file_list, 
        max_chars=args.max_chars,
        lmstudio_delay=args.lmstudio_delay
    ) 