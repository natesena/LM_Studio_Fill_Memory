#!/usr/bin/env python3
"""
Check which files from a batch file are already in Neo4j using Bolt protocol
"""

import sys
import os
import asyncio
import argparse
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.neo4j_bolt_verifier import Neo4jBoltVerifier

async def check_batch_files_bolt(batch_file):
    """Check which files from the specified batch file are in Neo4j using Bolt"""
    
    # Initialize Neo4j verifier with Bolt protocol
    neo4j_verifier = Neo4jBoltVerifier()
    
    try:
        with open(batch_file, 'r') as f:
            file_paths = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Batch file not found: {batch_file}")
        return
    
    print(f"🔍 Checking {len(file_paths)} files from {batch_file} using Bolt protocol...")
    print("=" * 60)
    
    found_files = []
    not_found_files = []
    
    for i, file_path in enumerate(file_paths, 1):
        filename = os.path.basename(file_path)
        print(f"[{i}/{len(file_paths)}] Checking: {filename}")
        print(f"  Full path: {file_path}")
        
        # Search for the memory in Neo4j using the FULL file path
        result = await neo4j_verifier.search_for_specific_memory(file_path)
        
        if result.get("success", False) and len(result.get("data", [])) > 0:
            print(f"  ✅ FOUND in Neo4j")
            found_files.append(file_path)
        else:
            print(f"  ❌ NOT FOUND in Neo4j")
            not_found_files.append(file_path)
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total files checked: {len(file_paths)}")
    print(f"Found in Neo4j: {len(found_files)}")
    print(f"Not found: {len(not_found_files)}")
    print()
    
    if found_files:
        print("✅ FOUND IN NEO4J (safe to remove from list):")
        print("-" * 40)
        for file_path in found_files:
            filename = os.path.basename(file_path)
            print(f"  {filename}")
        print()
    
    if not_found_files:
        print("❌ NOT FOUND (keep in list for re-processing):")
        print("-" * 40)
        for file_path in not_found_files:
            filename = os.path.basename(file_path)
            print(f"  {filename}")
        print()

def main():
    parser = argparse.ArgumentParser(description='Check which files from a batch are already in Neo4j')
    parser.add_argument('batch_file', help='Path to the batch file containing file paths')
    args = parser.parse_args()
    
    asyncio.run(check_batch_files_bolt(args.batch_file))

if __name__ == "__main__":
    main() 