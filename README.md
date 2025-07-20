# LM Studio Memory Integration

## Overview

This project enables you to use LM Studio and a Graphiti server to analyze code files and add their summaries as "memories" to a remote memory graph. It supports both single-file and batch workflows, as well as a "drop folder" automation for easy drag-and-drop processing.

## Installation

1. **Clone the repository**
2. **(Recommended) Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ensure LM Studio is running locally and you have access to a Graphiti MCP server.**

## Project Structure

- `add_memory.py`: Adds a single memory via LM Studio and Graphiti.
- `batch_memory_adder.py`: Batch processes files listed in `file_list.txt`, summarizes them, and adds memories.
- `generate_file_list.py`: Scans a directory and writes all file paths to `file_list.txt`.
- `memory_saver/`: Utilities and advanced batch scripts for tool integration and LLM workflows.
  - `batch_llm_prompt_runner.py`: Advanced batch processor with tool discovery and JSONL output.
  - `lmstudio_add_memory_tool.py`, `lmstudio_tools.py`: Tool schemas and integration helpers.
  - `run_llm_batch_on_repo.py`: Orchestrates batch LLM operations across a repository.
  - `add_memory_legacy.py`: Legacy version of memory addition logic (not recommended for new workflows).

## Usage

### 1. Add a Single Memory

Run the main script to add a memory for a single file or prompt:

```python
from add_memory import add_memory_via_lmstudio
response = add_memory_via_lmstudio(
    prompt="Add a memory about Python best practices",
    lmstudio_url="http://localhost:1234/v1/chat/completions",
    graphiti_url="https://mcp.knollcroft.com/mcp"
)
print(response)
```

### 2. Batch Process Files

1. Generate a list of files:
   ```bash
   python generate_file_list.py  # Scans current directory by default
   # Or edit file_list.txt manually
   ```
2. Run the batch processor:
   ```bash
   python batch_memory_adder.py
   ```
   This will summarize each file and add it as a memory.

### 3. Drop Folder Automation (Recommended Design)

- (If implemented) Use a script like `memory_drop_folder_watcher.py` to watch a folder for new files and process them automatically.
- Drag and drop files into the folder; the script will add memories for each new file.

### 4. Advanced Batch Processing

- Use `memory_saver/batch_llm_prompt_runner.py` for advanced workflows, tool discovery, and JSONL output.

## Extending the Project

- Add new scripts to the `scripts/` or `memory_saver/` folder as needed.
- Use verb-first, action-oriented names for clarity (e.g., `memory_add_batch.py`).
- Update the README and add `--help` to scripts for discoverability.

## Troubleshooting & FAQ

- **LM Studio or Graphiti not running?** Ensure both services are up and URLs are correct.
- **File not found errors?** Check your paths in `file_list.txt` or when running scripts.
- **Want to process a different folder?** Edit `ROOT_DIR` in `generate_file_list.py` or pass as an argument if supported.

## TODO

- [ ] Implement logic to split large files into multiple chunks/memories instead of just truncating them. This will ensure that the entire content of large files can be processed and stored as memories, not just the first part.

## Example Workflow: Generating and Filtering a File List

Here’s how to generate a file list with absolute paths and filter out unwanted files (like node_modules, .git, .next, .env):

1. **Generate a file list with absolute paths:**

   ```bash
   python generate_file_list_from_path.py --root-dir /path/to/your/folder
   # This creates file_list.txt with absolute paths
   ```

2. **Filter out unwanted files and directories:**
   ```bash
   python filter_file_list.py --input file_list.txt --output file_list_filtered.txt
   mv file_list_filtered.txt file_list.txt
   # Now file_list.txt contains only the files you want to process
   ```

---

For more details, see comments in each script or ask for help!
