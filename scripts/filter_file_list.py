#!/usr/bin/env python3
"""
CLI script for filtering file lists.

This script provides a command-line interface to filter file lists by removing unwanted files.
"""

import argparse
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.filter_file_list import filter_file_list


def main():
    """Main CLI function for filtering file lists."""
    parser = argparse.ArgumentParser(
        description="Filter a file list by removing unwanted files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter default file list
  python scripts/filter_file_list.py

  # Filter custom file list
  python scripts/filter_file_list.py --input my_files.txt --output filtered_files.txt

  # Filter with custom patterns
  python scripts/filter_file_list.py \\
    --input my_files.txt \\
    --exclude-patterns "*.log,*.tmp,*.cache" \\
    --exclude-dirs "node_modules,.git,venv"

  # Show what would be filtered without actually filtering
  python scripts/filter_file_list.py --dry-run
        """
    )
    
    parser.add_argument(
        "--input",
        default="data/file_list.txt",
        help="Input file list path (default: data/file_list.txt)"
    )
    
    parser.add_argument(
        "--output",
        help="Output file list path (default: overwrites input file)"
    )
    
    parser.add_argument(
        "--exclude-patterns",
        help="Comma-separated list of file patterns to exclude (e.g., *.log,*.tmp,*.cache)"
    )
    
    parser.add_argument(
        "--exclude-dirs",
        help="Comma-separated list of directory names to exclude (e.g., node_modules,.git,venv)"
    )
    
    parser.add_argument(
        "--exclude-extensions",
        help="Comma-separated list of file extensions to exclude (e.g., log,tmp,cache)"
    )
    
    parser.add_argument(
        "--min-size",
        type=int,
        help="Minimum file size in bytes (files smaller than this will be excluded)"
    )
    
    parser.add_argument(
        "--max-size",
        type=int,
        help="Maximum file size in bytes (files larger than this will be excluded)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be filtered without actually writing the output file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    # Set default output to input if not specified
    if not args.output:
        args.output = args.input
    
    # Check if input file exists
    if not os.path.exists(args.input):
        print(f"❌ Error: Input file '{args.input}' not found")
        sys.exit(1)
    
    # Parse exclude patterns if provided
    exclude_patterns = None
    if args.exclude_patterns:
        exclude_patterns = [pattern.strip() for pattern in args.exclude_patterns.split(",")]
    
    # Parse exclude directories if provided
    exclude_dirs = None
    if args.exclude_dirs:
        exclude_dirs = [dir.strip() for dir in args.exclude_dirs.split(",")]
    
    # Parse exclude extensions if provided
    exclude_extensions = None
    if args.exclude_extensions:
        exclude_extensions = [ext.strip().lower() for ext in args.exclude_extensions.split(",")]
    
    print(f"🔄 Filtering file list...")
    print(f"   Input file: {args.input}")
    print(f"   Output file: {args.output}")
    print(f"   Exclude patterns: {exclude_patterns or 'none'}")
    print(f"   Exclude dirs: {exclude_dirs or 'none'}")
    print(f"   Exclude extensions: {exclude_extensions or 'none'}")
    print(f"   Min size: {args.min_size or 'none'}")
    print(f"   Max size: {args.max_size or 'none'}")
    print(f"   Dry run: {args.dry_run}")
    print()
    
    try:
        # Read input file
        with open(args.input, 'r') as f:
            original_files = [line.strip() for line in f if line.strip()]
        
        print(f"📋 Original file count: {len(original_files)}")
        
        # Filter the files
        filtered_files = filter_file_list(
            file_paths=original_files,
            exclude_patterns=exclude_patterns,
            exclude_dirs=exclude_dirs,
            exclude_extensions=exclude_extensions,
            min_size=args.min_size,
            max_size=args.max_size
        )
        
        removed_count = len(original_files) - len(filtered_files)
        
        print(f"✅ Filtering completed!")
        print(f"   Original files: {len(original_files)}")
        print(f"   Filtered files: {len(filtered_files)}")
        print(f"   Removed files: {removed_count}")
        
        if args.verbose and removed_count > 0:
            print(f"\n🗑️ Removed files:")
            removed_files = set(original_files) - set(filtered_files)
            for i, file_path in enumerate(list(removed_files)[:10], 1):
                print(f"   {i}. {file_path}")
            if len(removed_files) > 10:
                print(f"   ... and {len(removed_files) - 10} more files")
        
        if args.verbose and filtered_files:
            print(f"\n✅ Kept files (first 10):")
            for i, file_path in enumerate(filtered_files[:10], 1):
                print(f"   {i}. {file_path}")
            if len(filtered_files) > 10:
                print(f"   ... and {len(filtered_files) - 10} more files")
        
        if args.dry_run:
            print(f"\n🔍 DRY RUN - No files were written")
            print(f"   Would write {len(filtered_files)} files to {args.output}")
        else:
            # Write filtered files to output
            with open(args.output, 'w') as f:
                for file_path in filtered_files:
                    f.write(f"{file_path}\n")
            
            print(f"\n💾 Filtered file list written to: {args.output}")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Review the filtered list: cat {args.output}")
        print(f"   2. Process the files: python scripts/batch_process.py --file-list {args.output}")
        
    except Exception as e:
        print(f"❌ Error filtering file list: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 