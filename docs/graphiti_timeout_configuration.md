# Graphiti Timeout Configuration for Ollama Calls

## Overview

Graphiti uses a unified timeout configuration system that affects all LLM client calls, including Ollama calls. The timeout is controlled through the `OPENAI_TIMEOUT` environment variable, which defaults to 30 minutes (1800 seconds).

## How It Works

### Environment Variable Configuration

Graphiti uses the `OPENAI_TIMEOUT` environment variable across multiple client components:

```python
DEFAULT_TIMEOUT = int(os.environ.get('OPENAI_TIMEOUT', '1800'))  # 30 minutes default
```

This configuration is found in:

- `graphiti/graphiti_core/llm_client/openai_client.py`
- `graphiti/graphiti_core/llm_client/openai_generic_client.py`
- `graphiti/graphiti_core/llm_client/azure_openai_client.py`
- `graphiti/graphiti_core/llm_client/groq_client.py`
- `graphiti/graphiti_core/cross_encoder/openai_reranker_client.py`

### Ollama Integration

When Graphiti makes calls to Ollama (through LM Studio or direct Ollama API), it uses the same timeout configuration. The timeout affects:

1. **LLM Response Generation**: How long to wait for Ollama to generate responses
2. **Embedding Generation**: Timeout for embedding model calls
3. **Cross-encoder Operations**: Timeout for reranking operations
4. **Entity Extraction**: Timeout for entity and relationship extraction

## Setting the Timeout

### Method 1: Environment Variable (Recommended)

Set the timeout before starting your Graphiti services:

```bash
# Set timeout to 30 minutes (default)
export OPENAI_TIMEOUT=1800

# Set timeout to 1 hour
export OPENAI_TIMEOUT=3600

# Set timeout to 15 minutes
export OPENAI_TIMEOUT=900

# Set timeout to 2 hours
export OPENAI_TIMEOUT=7200
```

### Method 2: Docker Environment Variable

If running Graphiti in Docker, add to your docker-compose.yml:

```yaml
services:
  graphiti-mcp:
    environment:
      - OPENAI_TIMEOUT=1800 # 30 minutes
```

### Method 3: .env File

Create a `.env` file in your Graphiti directory:

```env
OPENAI_TIMEOUT=1800
```

## Timeout Values Reference

| Duration   | Seconds | Use Case                          |
| ---------- | ------- | --------------------------------- |
| 5 minutes  | 300     | Quick operations, small datasets  |
| 10 minutes | 600     | Medium operations                 |
| 15 minutes | 900     | Standard operations               |
| 30 minutes | 1800    | **Default** - Most operations     |
| 1 hour     | 3600    | Large datasets, complex reasoning |
| 2 hours    | 7200    | Very large operations             |
| 4 hours    | 14400   | Massive operations                |

## Verification

### Check Current Timeout

```bash
# Check if timeout is set
echo $OPENAI_TIMEOUT

# If not set, it defaults to 1800 (30 minutes)
```

### Test Timeout Configuration

You can verify the timeout is working by monitoring Graphiti logs:

```bash
# Monitor Graphiti logs for timeout messages
docker logs -f graphiti-graphiti-mcp-1 | grep -i timeout
```

## Common Scenarios

### Large Memory Processing

For processing large amounts of text or complex reasoning tasks:

```bash
export OPENAI_TIMEOUT=3600  # 1 hour
```

### GPU-Intensive Operations

When using GPU models that might take longer:

```bash
export OPENAI_TIMEOUT=7200  # 2 hours
```

### Quick Operations

For simple operations or small datasets:

```bash
export OPENAI_TIMEOUT=600  # 10 minutes
```

## Troubleshooting

### Timeout Errors

If you see timeout errors in Graphiti logs:

1. **Increase the timeout**:

   ```bash
   export OPENAI_TIMEOUT=3600  # Try 1 hour
   ```

2. **Check Ollama performance**:

   ```bash
   # Monitor Ollama GPU usage
   nvidia-smi

   # Check Ollama logs
   docker logs -f ollama
   ```

3. **Verify network connectivity**:
   ```bash
   # Test connection to Ollama
   curl http://localhost:11434/api/tags
   ```

### Performance Optimization

If timeouts are frequent:

1. **Reduce batch sizes** in your processing scripts
2. **Increase Ollama resources** (more GPU memory, CPU cores)
3. **Use smaller models** for faster inference
4. **Implement retry logic** in your processing scripts

## Integration with LM Studio Fill Memory

In your LM Studio Fill Memory project, the timeout affects:

- **Batch processing scripts** (`scripts/batch_process.py`)
- **Git memory processing** (`src/core/git_memory_processor_gpu_safe.py`)
- **Memory addition operations** (`src/core/add_memory_fastmcp_compatible.py`)

### Example: Batch Processing with Custom Timeout

```bash
# Set timeout for batch processing
export OPENAI_TIMEOUT=3600

# Run batch processing
python scripts/batch_process.py \
  --file-list data/file_list.txt \
  --max-chars 2000 \
  --rate-limit-delay 2
```

## Best Practices

1. **Start with default** (30 minutes) for most operations
2. **Monitor performance** and adjust based on your specific use case
3. **Use longer timeouts** for GPU-intensive operations
4. **Test with smaller datasets** first to find optimal timeout values
5. **Document your timeout settings** for team consistency

## Related Configuration

The timeout works in conjunction with other Graphiti settings:

- **`SEMAPHORE_LIMIT`**: Controls concurrent operations
- **`USE_PARALLEL_RUNTIME`**: Enables parallel processing
- **`MAX_REFLEXION_ITERATIONS`**: Controls reasoning iterations

## Summary

The `OPENAI_TIMEOUT` environment variable provides a unified way to control timeout behavior across all Graphiti LLM operations, including Ollama calls. The default 30-minute timeout is suitable for most operations, but can be adjusted based on your specific requirements and hardware capabilities.
