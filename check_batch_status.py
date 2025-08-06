#!/usr/bin/env python3
"""
Check which files from batch_30_files.txt are already in Neo4j
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.neo4j_utils import Neo4jVerifier

def check_batch_files():
    """Check which files from batch_30_files.txt are in Neo4j"""
    
    # Initialize Neo4j verifier with same credentials as batch processor
    neo4j_verifier = Neo4jVerifier(username="neo4j", password="demodemo")
    
    # Read the batch file
    batch_file = "data/batch_30_files_new.txt"
    
    try:
        with open(batch_file, 'r') as f:
            file_paths = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"❌ Batch file not found: {batch_file}")
        return
    
    print(f"🔍 Checking {len(file_paths)} files from batch...")
    print("=" * 60)
    
    found_in_neo4j = []
    not_found = []
    
    for i, file_path in enumerate(file_paths, 1):
        print(f"[{i}/{len(file_paths)}] Checking: {os.path.basename(file_path)}")
        
        # Search for the file in Neo4j (same logic as batch processor)
        result = neo4j_verifier.search_for_specific_memory(file_path)
        
        if "error" in result:
            print(f"  ⚠️ Neo4j query error: {result['error']}")
            not_found.append(file_path)
            continue
        
        # Check if any results were returned
        if "results" in result and len(result["results"]) > 0:
            data = result["results"][0].get("data", [])
            if len(data) > 0:
                print(f"  ✅ FOUND in Neo4j")
                found_in_neo4j.append(file_path)
            else:
                print(f"  ❌ NOT FOUND in Neo4j")
                not_found.append(file_path)
        else:
            print(f"  ❌ NOT FOUND in Neo4j")
            not_found.append(file_path)
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"Total files checked: {len(file_paths)}")
    print(f"Found in Neo4j: {len(found_in_neo4j)}")
    print(f"Not found: {len(not_found)}")
    
    if found_in_neo4j:
        print(f"\n✅ FOUND IN NEO4J (safe to remove from list):")
        print("-" * 40)
        for file_path in found_in_neo4j:
            print(f"  {os.path.basename(file_path)}")
    
    if not_found:
        print(f"\n❌ NOT FOUND (keep in list for re-processing):")
        print("-" * 40)
        for file_path in not_found:
            print(f"  {os.path.basename(file_path)}")
    
    # Create updated batch file with only missing files
    if not_found:
        updated_batch_file = "data/batch_30_files_new_remaining.txt"
        with open(updated_batch_file, 'w') as f:
            for file_path in not_found:
                f.write(file_path + '\n')
        print(f"\n📝 Created updated batch file: {updated_batch_file}")
        print(f"   Contains {len(not_found)} files that still need processing")

if __name__ == "__main__":
    check_batch_files() 