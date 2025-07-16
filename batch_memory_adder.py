# batch_memory_adder.py
"""
Batch memory adder that reads file_list.txt, gets file info via chat completion, then creates memories.
"""
import requests
import os
from add_memory import add_memory_via_lmstudio

def get_file_info(file_path: str, lmstudio_url: str = "http://127.0.0.1:1234/v1/chat/completions", model: str = "qwen3-32b") -> str:
    """
    Get specific information about a file using chat completion.
    
    Args:
        file_path: Path to the file
        lmstudio_url: LM Studio API URL
        model: Model to use
    
    Returns:
        Information about the file
    """
    try:
        # Check if file exists
        if not os.path.exists(file_path):
            return f"File not found: {file_path}"
        
        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create prompt to analyze the file
        prompt = f"""Please analyze this file and provide a concise summary of what it does:

File: {file_path}
Content:
{content[:2000]}  # Limit content to avoid token limits

Please provide a brief summary of:
1. What this file does
2. Key functions/classes
3. Purpose in the project
4. Any important details

Keep it concise but informative."""

        # Send to LM Studio for analysis
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(lmstudio_url, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        data = response.json()
        return data["choices"][0]["message"]["content"]
        
    except Exception as e:
        return f"Error analyzing file {file_path}: {str(e)}"

def process_file_list(file_list_path: str = "file_list.txt"):
    """
    Read file_list.txt line by line, get file info, and add a memory for each file.
    
    Args:
        file_list_path: Path to the file list (default: file_list.txt)
    """
    try:
        with open(file_list_path, 'r') as f:
            file_paths = [line.strip() for line in f if line.strip()]
        
        print(f"Found {len(file_paths)} files to process")
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\nProcessing file {i}/{len(file_paths)}: {file_path}")
            
            # Get file information via chat completion
            print("  Getting file info...")
            file_info = get_file_info(file_path)
            print(f"  File info: {file_info[:100]}...")
            
            # Create memory about this specific file
            file_name = file_path.split('/')[-1]  # Get just the filename
            prompt = f"Please add a memory with the name '{file_name}' and the following content: '{file_info}'"
            
            try:
                result = add_memory_via_lmstudio(prompt)
                print(f"✅ Success: Memory added for {file_name}")
            except Exception as e:
                print(f"❌ Error processing {file_path}: {e}")
                
    except FileNotFoundError:
        print(f"File not found: {file_list_path}")
    except Exception as e:
        print(f"Error reading file list: {e}")

if __name__ == "__main__":
    process_file_list() 