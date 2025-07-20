#!/usr/bin/env python3
"""
CLI script for batch processing files and adding them as memories.

This script provides a command-line interface to the batch processing functionality.
"""

import argparse
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.batch_processor import process_file_list_with_proper_queue_monitoring


def main():
    """Main CLI function for batch processing."""
    parser = argparse.ArgumentParser(
        description="Batch process files and add them as memories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process files using default file_list.txt
  python scripts/batch_process.py

  # Process files with custom settings
  python scripts/batch_process.py \\
    --file-list custom_file_list.txt \\
    --max-chars 3000 \\
    --rate-limit-delay 3 \\
    --graphiti-timeout 600

  # Process files from a specific directory
  python scripts/batch_process.py \\
    --file-list data/my_files.txt \\
    --max-chars 1500
        """
    )
    
    parser.add_argument(
        "--file-list",
        default="data/file_list.txt",
        help="Path to file containing list of files to process (default: data/file_list.txt)"
    )
    
    parser.add_argument(
        "--max-chars",
        type=int,
        default=2000,
        help="Maximum characters per memory (default: 2000)"
    )
    
    parser.add_argument(
        "--rate-limit-delay",
        type=float,
        default=2.0,
        help="Delay between memory additions in seconds (default: 2.0)"
    )
    
    parser.add_argument(
        "--graphiti-timeout",
        type=int,
        default=300,
        help="Timeout for Graphiti queue operations in seconds (default: 300)"
    )
    
    parser.add_argument(
        "--lmstudio-url",
        default="http://127.0.0.1:1234/v1/chat/completions",
        help="LM Studio API URL (default: http://127.0.0.1:1234/v1/chat/completions)"
    )
    
    parser.add_argument(
        "--model",
        default="qwen3-32b",
        help="Model to use (default: qwen3-32b)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be processed without actually adding memories"
    )
    
    args = parser.parse_args()
    
    # Check if file list exists
    if not os.path.exists(args.file_list):
        print(f"❌ Error: File list '{args.file_list}' not found")
        print(f"   You can create one using: python scripts/generate_file_list.py")
        sys.exit(1)
    
    print(f"🔄 Starting batch processing...")
    print(f"   File list: {args.file_list}")
    print(f"   Max characters per memory: {args.max_chars}")
    print(f"   Rate limit delay: {args.rate_limit_delay}s")
    print(f"   Graphiti timeout: {args.graphiti_timeout}s")
    print(f"   LM Studio URL: {args.lmstudio_url}")
    print(f"   Model: {args.model}")
    print(f"   Dry run: {args.dry_run}")
    print()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No memories will be added")
        print()
    
    try:
        # Read file list to show what would be processed
        with open(args.file_list, 'r') as f:
            files = [line.strip() for line in f if line.strip()]
        
        print(f"📋 Found {len(files)} files to process:")
        for i, file_path in enumerate(files[:5], 1):
            print(f"   {i}. {file_path}")
        if len(files) > 5:
            print(f"   ... and {len(files) - 5} more files")
        print()
        
        if args.dry_run:
            print("✅ Dry run completed - no memories were added")
            return
        
        # Process the files
        result = process_file_list_with_proper_queue_monitoring(
            file_list_path=args.file_list,
            max_chars=args.max_chars,
            lmstudio_delay=args.rate_limit_delay,
            graphiti_timeout=args.graphiti_timeout
        )
        
        print(f"✅ Batch processing completed!")
        print(f"   Processed: {result.get('processed', 0)} files")
        print(f"   Successful: {result.get('successful', 0)} memories")
        print(f"   Failed: {result.get('failed', 0)} memories")
        
    except KeyboardInterrupt:
        print("\n⚠️ Batch processing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error during batch processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 