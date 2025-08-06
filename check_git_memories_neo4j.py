#!/usr/bin/env python3
"""
Check if Git commit memories were successfully added to Neo4j
"""

import sys
import os
import asyncio
import json
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.neo4j_bolt_verifier import Neo4jBoltVerifier

async def check_git_memories_neo4j(json_file):
    """Check if Git commit memories from the JSON file are in Neo4j"""
    
    # Initialize Neo4j verifier with Bolt protocol
    neo4j_verifier = Neo4jBoltVerifier()
    
    try:
        with open(json_file, 'r') as f:
            commits = json.load(f)
    except FileNotFoundError:
        print(f"❌ JSON file not found: {json_file}")
        return
    except json.JSONDecodeError:
        print(f"❌ Invalid JSON file: {json_file}")
        return
    
    print(f"🔍 Checking {len(commits)} Git commit memories from {json_file} using Bolt protocol...")
    print("=" * 80)
    
    found_memories = []
    not_found_memories = []
    
    for i, commit in enumerate(commits, 1):
        commit_hash = commit.get('hash', 'unknown')[:8]
        category = categorize_commit(commit.get('message', ''))
        memory_name = f"Git Commit: {commit_hash} - {category.replace('_', ' ').title()}"
        
        print(f"[{i}/{len(commits)}] Checking: {memory_name}")
        print(f"  Commit: {commit_hash}")
        print(f"  Date: {commit.get('date', 'unknown')}")
        print(f"  Files changed: {len(commit.get('files_changed', []))}")
        
        # Search for the memory in Neo4j using the memory name
        result = await neo4j_verifier.search_for_specific_memory(memory_name)
        
        if result.get("success", False) and len(result.get("data", [])) > 0:
            print(f"  ✅ FOUND in Neo4j")
            found_memories.append(memory_name)
        else:
            print(f"  ❌ NOT FOUND in Neo4j")
            not_found_memories.append(memory_name)
    
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    print(f"Total memories checked: {len(commits)}")
    print(f"Found in Neo4j: {len(found_memories)}")
    print(f"Not found: {len(not_found_memories)}")
    print()
    
    if found_memories:
        print("✅ FOUND IN NEO4J:")
        print("-" * 50)
        for memory_name in found_memories:
            print(f"  {memory_name}")
        print()
    
    if not_found_memories:
        print("❌ NOT FOUND IN NEO4J:")
        print("-" * 50)
        for memory_name in not_found_memories:
            print(f"  {memory_name}")
        print()

def categorize_commit(commit_message: str) -> str:
    """Categorize commit based on its message."""
    message_lower = commit_message.lower()
    
    if any(word in message_lower for word in ['fix', 'bug', 'resolve', 'correct']):
        return "bug_fix"
    elif any(word in message_lower for word in ['feat', 'add', 'implement', 'create']):
        return "feature"
    elif any(word in message_lower for word in ['docs', 'documentation']):
        return "documentation"
    elif any(word in message_lower for word in ['refactor', 'restructure']):
        return "refactoring"
    elif any(word in message_lower for word in ['cleanup', 'remove', 'delete']):
        return "cleanup"
    else:
        return "other"

def main():
    parser = argparse.ArgumentParser(description='Check if Git commit memories are in Neo4j')
    parser.add_argument('json_file', help='Path to the JSON file containing commit data')
    args = parser.parse_args()
    
    asyncio.run(check_git_memories_neo4j(args.json_file))

if __name__ == "__main__":
    main() 