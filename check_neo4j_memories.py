#!/usr/bin/env python3
"""
Check what memories are actually stored in Neo4j
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.neo4j_utils import Neo4jVerifier

def check_neo4j_memories():
    """Check what memories are actually stored in Neo4j"""
    
    # Initialize Neo4j verifier with same credentials as batch processor
    neo4j_verifier = Neo4jVerifier(username="neo4j", password="demodemo")
    
    print("🔍 Checking what memories are actually in Neo4j...")
    print("=" * 60)
    
    # Get all memory nodes
    result = neo4j_verifier.get_memory_nodes()
    
    if "error" in result:
        print(f"❌ Neo4j query error: {result['error']}")
        return
    
    if "results" in result and len(result["results"]) > 0:
        data = result["results"][0].get("data", [])
        print(f"Found {len(data)} memory nodes:")
        print("-" * 40)
        
        for i, node_data in enumerate(data, 1):
            node = node_data.get("row", [{}])[0]
            name = node.get("name", "NO_NAME")
            print(f"{i}. {name}")
    else:
        print("No memory nodes found in Neo4j")
    
    print("\n" + "=" * 60)
    print("📊 Getting recent nodes...")
    print("=" * 60)
    
    # Get recent nodes
    recent_result = neo4j_verifier.get_recent_nodes(hours=24)
    
    if "error" in recent_result:
        print(f"❌ Neo4j query error: {recent_result['error']}")
        return
    
    if "results" in recent_result and len(recent_result["results"]) > 0:
        data = recent_result["results"][0].get("data", [])
        print(f"Found {len(data)} recent nodes:")
        print("-" * 40)
        
        for i, node_data in enumerate(data, 1):
            node = node_data.get("row", [{}])[0]
            name = node.get("name", "NO_NAME")
            created_at = node.get("created_at", "NO_DATE")
            print(f"{i}. {name} (created: {created_at})")
    else:
        print("No recent nodes found in Neo4j")

if __name__ == "__main__":
    check_neo4j_memories() 