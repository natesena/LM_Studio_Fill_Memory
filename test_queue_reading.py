#!/usr/bin/env python3
"""
Test script to validate queue reading capabilities.
This script tests all the docker exec commands for reading queue state.
"""

import subprocess
import json
import time
from datetime import datetime

def run_docker_command(cmd):
    """Run a docker exec command and return the result."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return {"error": result.stderr.strip() or "Command failed"}
        return {"success": True, "output": result.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out"}
    except Exception as e:
        return {"error": str(e)}

def test_queue_size_reading():
    """Test reading queue sizes."""
    print("🔍 Testing queue size reading...")
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        "import json, graphiti_mcp_server as s; print(json.dumps({k: q.qsize() for k, q in s.episode_queues.items()}))"
    ]
    result = run_docker_command(cmd)
    if result.get("success"):
        try:
            queue_sizes = json.loads(result["output"])
            print(f"✅ Queue sizes: {queue_sizes}")
            return queue_sizes
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON: {result['output']}")
            return None
    else:
        print(f"❌ Failed to read queue sizes: {result['error']}")
        return None

def test_queue_names_reading():
    """Test reading queue names."""
    print("🔍 Testing queue names reading...")
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        "import json, graphiti_mcp_server as s; print(json.dumps({k: s.queue_names.get(k, []) for k in s.episode_queues.keys()}))"
    ]
    result = run_docker_command(cmd)
    if result.get("success"):
        try:
            queue_names = json.loads(result["output"])
            print(f"✅ Queue names: {queue_names}")
            return queue_names
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON: {result['output']}")
            return None
    else:
        print(f"❌ Failed to read queue names: {result['error']}")
        return None

def test_worker_status_reading():
    """Test reading worker status."""
    print("🔍 Testing worker status reading...")
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        "import json, graphiti_mcp_server as s; print(json.dumps({k: s.queue_workers.get(k, False) for k in s.episode_queues.keys()}))"
    ]
    result = run_docker_command(cmd)
    if result.get("success"):
        try:
            worker_status = json.loads(result["output"])
            print(f"✅ Worker status: {worker_status}")
            return worker_status
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON: {result['output']}")
            return None
    else:
        print(f"❌ Failed to read worker status: {result['error']}")
        return None

def test_comprehensive_reading():
    """Test reading all queue data at once."""
    print("🔍 Testing comprehensive queue reading...")
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        """import json, graphiti_mcp_server as s
result = {}
for k, q in s.episode_queues.items():
    result[k] = {
        'size': q.qsize(),
        'items': s.queue_names.get(k, []),
        'worker_active': s.queue_workers.get(k, False)
    }
print(json.dumps(result, indent=2))"""
    ]
    result = run_docker_command(cmd)
    if result.get("success"):
        try:
            comprehensive_data = json.loads(result["output"])
            print(f"✅ Comprehensive data: {json.dumps(comprehensive_data, indent=2)}")
            return comprehensive_data
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON: {result['output']}")
            return None
    else:
        print(f"❌ Failed to read comprehensive data: {result['error']}")
        return None

def test_edge_cases():
    """Test edge cases like empty queue, multiple groups, etc."""
    print("🔍 Testing edge cases...")
    
    # Test with no group_id (should work)
    cmd = [
        "docker", "exec", "graphiti-graphiti-mcp-1",
        "python", "-c",
        "import json, graphiti_mcp_server as s; print(json.dumps({'total_groups': len(s.episode_queues), 'all_group_ids': list(s.episode_queues.keys())}))"
    ]
    result = run_docker_command(cmd)
    if result.get("success"):
        try:
            edge_data = json.loads(result["output"])
            print(f"✅ Edge case data: {edge_data}")
            return edge_data
        except json.JSONDecodeError:
            print(f"❌ Failed to parse JSON: {result['output']}")
            return None
    else:
        print(f"❌ Failed to read edge case data: {result['error']}")
        return None

def main():
    """Run all tests."""
    print("=" * 60)
    print("QUEUE READING CAPABILITIES TEST")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test all reading capabilities
    queue_sizes = test_queue_size_reading()
    print()
    
    queue_names = test_queue_names_reading()
    print()
    
    worker_status = test_worker_status_reading()
    print()
    
    comprehensive_data = test_comprehensive_reading()
    print()
    
    edge_data = test_edge_cases()
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    all_tests_passed = all([
        queue_sizes is not None,
        queue_names is not None,
        worker_status is not None,
        comprehensive_data is not None,
        edge_data is not None
    ])
    
    if all_tests_passed:
        print("✅ ALL TESTS PASSED")
        print("✅ Queue reading capabilities are working correctly")
        print()
        print("📋 RELIABLE COMMANDS:")
        print("1. Queue sizes: docker exec graphiti-graphiti-mcp-1 python -c \"import json, graphiti_mcp_server as s; print(json.dumps({k: q.qsize() for k, q in s.episode_queues.items()}))\"")
        print("2. Queue names: docker exec graphiti-graphiti-mcp-1 python -c \"import json, graphiti_mcp_server as s; print(json.dumps({k: s.queue_names.get(k, []) for k in s.episode_queues.keys()}))\"")
        print("3. Worker status: docker exec graphiti-graphiti-mcp-1 python -c \"import json, graphiti_mcp_server as s; print(json.dumps({k: s.queue_workers.get(k, False) for k in s.episode_queues.keys()}))\"")
        print("4. Comprehensive: docker exec graphiti-graphiti-mcp-1 python -c \"import json, graphiti_mcp_server as s; result = {}; [result.update({k: {'size': q.qsize(), 'items': s.queue_names.get(k, []), 'worker_active': s.queue_workers.get(k, False)}}) for k, q in s.episode_queues.items()]; print(json.dumps(result, indent=2))\"")
    else:
        print("❌ SOME TESTS FAILED")
        print("❌ Queue reading capabilities need investigation")
    
    print()
    print("Current queue state:")
    if comprehensive_data:
        for group_id, data in comprehensive_data.items():
            print(f"  Group '{group_id}': {data['size']} items, {len(data['items'])} names, worker_active={data['worker_active']}")
    else:
        print("  Unable to read queue state")

if __name__ == "__main__":
    main() 