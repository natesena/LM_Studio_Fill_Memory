#!/usr/bin/env python3
"""
run_llm_batch_on_repo.py

This script finds the first .txt file in the current directory (repo),
and runs batch_llm_prompt_runner.py on it with default arguments.
No arguments are required from the user.
"""
import subprocess
import sys
from pathlib import Path

# Default values
API_BASE = "http://127.0.0.1:1234/v1/"
GRAPHITI_URL = "http://localhost:8000/add_memory"
OUTPUT = "results.jsonl"

# Find the first .txt file in the current directory (repo)
txt_files = list(Path(".").glob("*.txt"))
if not txt_files:
    print("No .txt file found in the current directory.")
    sys.exit(1)

file_list = txt_files[0]
print(f"Using file list: {file_list}")

# Build the command
target_script = Path(__file__).parent / "batch_llm_prompt_runner.py"
cmd = [
    sys.executable,
    str(target_script),
    str(file_list),
    "--api_base", API_BASE,
    "--graphiti_url", GRAPHITI_URL,
    "--output", OUTPUT,
]

print("Running:", " ".join(cmd))

# Run the command
subprocess.run(cmd, check=True) 