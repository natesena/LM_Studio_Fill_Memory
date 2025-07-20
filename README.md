# LM Studio Memory Integration

## Overview

This project enables you to use LM Studio and a Graphiti server to analyze code files and add their summaries as "memories" to a remote memory graph. It supports both single-file and batch workflows, with proper queue monitoring to avoid GPU contention.

## 🏗️ Project Structure

```
LM_Studio_Fill_Memory/
├── src/                    # Main source code
│   ├── core/              # Core memory addition functionality
│   ├── queue/             # Queue monitoring and management
│   ├── utils/             # Utility functions
│   └── legacy/            # Legacy implementations
├── scripts/               # Command-line interface scripts
├── tests/                 # Testing and debugging
├── docs/                  # Documentation
├── data/                  # Data files and examples
└── config/                # Configuration files
```

## 🚀 Quick Start

### 1. Installation

1. **Clone the repository**
2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ensure LM Studio is running locally and you have access to a Graphiti MCP server.**

### 2. Add a Single Memory

```bash
# Add a simple text memory
python scripts/add_memory.py "Python is a programming language"

# Add a memory from a file
python scripts/add_memory.py --file path/to/file.txt

# Add with custom settings
python scripts/add_memory.py "Machine learning basics" \
  --lmstudio-url http://localhost:1234/v1/chat/completions \
  --model qwen3-32b \
  --rate-limit-delay 5
```

### 3. Batch Process Files

```bash
# Generate a file list from current directory
python scripts/generate_file_list.py

# Filter out unwanted files
python scripts/filter_file_list.py \
  --exclude-dirs "node_modules,.git,venv" \
  --exclude-patterns "*.log,*.tmp"

# Process all files with proper queue monitoring
python scripts/batch_process.py

# Process with custom settings
python scripts/batch_process.py \
  --file-list data/my_files.txt \
  --max-chars 3000 \
  --rate-limit-delay 3
```

## 📖 Detailed Usage

### Command-Line Scripts

#### `scripts/add_memory.py`

Add a single memory via LM Studio and Graphiti.

**Options:**

- `prompt` - The content to add as a memory
- `--file, -f` - Read content from a file instead
- `--lmstudio-url` - LM Studio API URL (default: http://127.0.0.1:1234/v1/chat/completions)
- `--model` - Model to use (default: qwen3-32b)
- `--rate-limit-delay` - Delay between operations (default: 2.0s)
- `--no-check-queue` - Skip queue status check

#### `scripts/batch_process.py`

Batch process files and add them as memories with proper queue monitoring.

**Options:**

- `--file-list` - Path to file list (default: data/file_list.txt)
- `--max-chars` - Maximum characters per memory (default: 2000)
- `--rate-limit-delay` - Delay between operations (default: 2.0s)
- `--graphiti-timeout` - Queue timeout (default: 300s)
- `--dry-run` - Show what would be processed without adding memories

#### `scripts/generate_file_list.py`

Generate a list of files from a directory.

**Options:**

- `--root-dir` - Directory to scan (default: current directory)
- `--output` - Output file path (default: data/file_list.txt)
- `--extensions` - File extensions to include (e.g., py,js,ts,md)
- `--exclude-dirs` - Directories to exclude (e.g., node_modules,.git,venv)
- `--relative-paths` - Use relative paths instead of absolute

#### `scripts/filter_file_list.py`

Filter a file list by removing unwanted files.

**Options:**

- `--input` - Input file list (default: data/file_list.txt)
- `--output` - Output file list (default: overwrites input)
- `--exclude-patterns` - File patterns to exclude (e.g., _.log,_.tmp)
- `--exclude-dirs` - Directory names to exclude
- `--exclude-extensions` - File extensions to exclude
- `--min-size` - Minimum file size in bytes
- `--max-size` - Maximum file size in bytes
- `--dry-run` - Show what would be filtered without writing

### Programmatic Usage

```python
# Import the core functionality
from src.core.memory_adder import add_memory_via_lmstudio
from src.core.batch_processor import process_file_list_with_proper_queue_monitoring

# Add a single memory
result = add_memory_via_lmstudio(
    prompt="Please add a memory with the name 'test' and content 'This is a test'",
    lmstudio_url="http://localhost:1234/v1/chat/completions",
    model="qwen3-32b"
)

# Batch process files
result = process_file_list_with_proper_queue_monitoring(
    file_list_path="data/file_list.txt",
    max_chars=2000,
    rate_limit_delay=2.0,
    graphiti_timeout=300
)
```

## 🔧 Configuration

### Environment Variables

- `LMSTUDIO_URL` - LM Studio API URL
- `GRAPHITI_URL` - Graphiti MCP server URL
- `DEFAULT_MODEL` - Default model to use

### Queue Monitoring

The project includes sophisticated queue monitoring to prevent GPU contention between LM Studio and Graphiti:

- **Automatic queue status checking** before adding memories
- **Sequential processing** to avoid race conditions
- **Timeout handling** for long-running operations
- **Real-time monitoring** of processing status

## 📚 Documentation

- [`docs/debugging_guide.md`](docs/debugging_guide.md) - Debugging and troubleshooting
- [`docs/fastmcp_solution.md`](docs/fastmcp_solution.md) - FastMCP integration details
- [`docs/graphiti_queue_overview.md`](docs/graphiti_queue_overview.md) - Queue architecture
- [`docs/reorganization_plan.md`](docs/reorganization_plan.md) - Project reorganization details

## 🧪 Testing

Run tests and debugging scripts:

```bash
# Test MCP session
python tests/test_mcp_session.py

# Debug lifecycle
python tests/debug_lifecycle.py

# Verify Neo4j memories
python tests/verify_memories.py
```

## 🔄 Migration from Old Structure

If you were using the old file structure:

- `add_memory.py` → `scripts/add_memory.py` or `src/core/memory_adder.py`
- `batch_memory_adder.py` → `scripts/batch_process.py` or `src/core/batch_processor.py`
- `generate_file_list_from_path.py` → `scripts/generate_file_list.py` or `src/utils/file_utils.py`
- `filter_file_list.py` → `scripts/filter_file_list.py` or `src/utils/filter_file_list.py`

## 🤝 Contributing

1. Follow the new directory structure
2. Add proper CLI interfaces to new scripts
3. Include help documentation
4. Add tests for new functionality
5. Update this README for any new features

## 🐛 Troubleshooting

- **LM Studio or Graphiti not running?** Ensure both services are up and URLs are correct
- **File not found errors?** Check your paths in file lists or when running scripts
- **Queue timeout errors?** Increase the `--graphiti-timeout` parameter
- **GPU contention?** Increase the `--rate-limit-delay` parameter

## 📋 TODO

- [ ] Implement logic to split large files into multiple chunks/memories
- [ ] Add configuration file support
- [ ] Implement drop folder automation
- [ ] Add progress bars for batch operations
- [ ] Create Docker container for easy deployment

---

For more details, see the documentation in the `docs/` directory or ask for help!
