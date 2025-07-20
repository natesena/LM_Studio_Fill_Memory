# batch_memory_adder.py
"""
Batch memory adder that reads file_list.txt, gets file info via chat completion, then creates memories.
Proper queue monitoring to avoid GPU contention between LM Studio and Graphiti.
"""
import requests
import os
import argparse
import time
from ..core.memory_adder import add_memory_via_lmstudio
from ..queue.monitor import GraphitiQueueMonitor

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
                                                 lmstudio_delay: int = 5, graphiti_timeout: int = 300):
    """
    Process files with proper queue monitoring to avoid GPU contention.
    
    Args:
        file_list_path: Path to the file list (default: file_list.txt)
        max_chars: Maximum number of characters from each file to include in the prompt
        lmstudio_delay: Delay after LM Studio operations to let GPU cool down (default: 5 seconds)
        graphiti_timeout: Maximum time to wait for Graphiti processing (default: 300 seconds)
    """
    try:
        with open(file_list_path, 'r') as f:
            file_paths = [line.strip() for line in f if line.strip()]
        print(f"Found {len(file_paths)} files to process with proper queue monitoring")
        print(f"GPU contention prevention: {lmstudio_delay}s delay between operations")
        
        # Initialize queue monitor
        queue_monitor = GraphitiQueueMonitor()
        
        # Check initial queue status
        print("\n=== Checking initial queue status ===")
        initial_summary = queue_monitor.get_queue_summary()
        print(f"Initial queue status: {initial_summary['overall_status']} - {initial_summary['message']}")
        
        # Wait for queue to be empty before starting
        if initial_summary['processing_count'] > 0:
            print(f"⚠️ Queue has {initial_summary['processing_count']} episodes processing, waiting...")
            if not queue_monitor.wait_for_queue_empty(timeout=graphiti_timeout):
                print("⚠️ Queue may still be processing, proceeding anyway...")
        
        successful_count = 0
        error_count = 0
        
        for i, rel_file_path in enumerate(file_paths, 1):
            abs_file_path = os.path.abspath(rel_file_path)
            print(f"\n{'='*60}")
            print(f"Processing file {i}/{len(file_paths)}: {abs_file_path}")
            print(f"{'='*60}")
            
            try:
                # STEP 1: LM Studio Operation (GPU-intensive)
                print("🔄 STEP 1: Analyzing file with LM Studio...")
                file_info = get_file_info(abs_file_path, max_chars=max_chars)
                print(f"✅ File analysis complete: {file_info[:100]}...")
                
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
                    if queue_monitor.wait_for_specific_episode(abs_file_path, timeout=graphiti_timeout):
                        print(f"✅ Memory processed successfully: {abs_file_path}")
                        successful_count += 1
                    else:
                        print(f"⚠️ Memory processing timeout: {abs_file_path}")
                        error_count += 1
                else:
                    print(f"❌ Memory addition failed: {result}")
                    error_count += 1
                    
            except Exception as e:
                print(f"❌ Error processing {abs_file_path}: {e}")
                error_count += 1
            
            # Brief pause between files to ensure clean separation
            if i < len(file_paths):
                print(f"⏳ Brief pause before next file...")
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
        final_summary = queue_monitor.get_queue_summary()
        print(f"Final queue status: {final_summary['overall_status']} - {final_summary['message']}")
        
    except FileNotFoundError:
        print(f"File not found: {file_list_path}")
    except Exception as e:
        print(f"Error reading file list: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch memory adder with proper queue monitoring to avoid GPU contention.")
    parser.add_argument('--file-list', type=str, default='file_list.txt', help='Path to the file list (default: file_list.txt)')
    parser.add_argument('--max-chars', type=int, default=2000, help='Maximum number of characters from each file to include in the prompt (default: 2000)')
    parser.add_argument('--lmstudio-delay', type=int, default=5, help='Delay after LM Studio operations in seconds (default: 5)')
    parser.add_argument('--graphiti-timeout', type=int, default=300, help='Maximum time to wait for Graphiti processing in seconds (default: 300)')
    args = parser.parse_args()
    
    process_file_list_with_proper_queue_monitoring(
        file_list_path=args.file_list, 
        max_chars=args.max_chars,
        lmstudio_delay=args.lmstudio_delay,
        graphiti_timeout=args.graphiti_timeout
    ) 