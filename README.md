# LM Studio Memory Integration

This project demonstrates how to integrate LM Studio's tool-calling (function calling) API with a remote MCP/Graphiti server to enable LLMs to request memory additions via tool calls.

## Overview

The system allows an LLM hosted in LM Studio to:

1. Receive tool definitions for memory operations
2. Make tool calls to add memories to a remote Graphiti server
3. Process the results and continue the conversation

## Key Components

### `add_memory.py`

Main module containing the `add_memory_via_lmstudio` function that:

- Sends chat completion requests to LM Studio with tool definitions
- Parses tool call responses from the LLM
- Executes the actual memory addition to the Graphiti server
- Returns the final response

### `memory_saver/` Directory

Contains additional utilities and batch processing scripts:

- `lmstudio_add_memory_tool.py` - Tool schema and function definitions
- `lmstudio_tools.py` - LM Studio integration utilities
- `batch_llm_prompt_runner.py` - Batch processing capabilities
- `run_llm_batch_on_repo.py` - Repository-wide batch processing

## Usage

```python
from add_memory import add_memory_via_lmstudio

# Add a memory via LM Studio
response = add_memory_via_lmstudio(
    prompt="Add a memory about Python best practices",
    lmstudio_url="http://localhost:1234/v1/chat/completions",
    graphiti_url="https://mcp.knollcroft.com/mcp"
)
```

## Configuration

- **LM Studio URL**: Default is `http://localhost:1234/v1/chat/completions`
- **Graphiti Server**: Default is `https://mcp.knollcroft.com/mcp`
- **Model**: Default is `local-model` (configurable in LM Studio)

## Requirements

- Python 3.7+
- `requests` library
- LM Studio running locally
- Access to a Graphiti MCP server

## Installation

```bash
pip install requests
```

## Architecture

The system follows the MCP (Model Context Protocol) pattern:

1. LLM receives tool definitions in the chat completion request
2. LLM makes tool calls based on the conversation context
3. Tool calls are executed against the remote MCP server
4. Results are returned to the LLM for final response generation
