#!/usr/bin/env python3
"""
CLI script for generating file lists from directories.

This script provides a command-line interface to generate lists of files for processing.
"""

import argparse
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.file_utils import generate_file_list_from_path


def main():
    """Main CLI function for generating file lists."""
    parser = argparse.ArgumentParser(
        description="Generate a list of files from a directory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate file list from current directory
  python scripts/generate_file_list.py

  # Generate file list from specific directory
  python scripts/generate_file_list.py --root-dir /path/to/your/project

  # Generate file list with custom output file
  python scripts/generate_file_list.py \\
    --root-dir /path/to/your/project \\
    --output custom_file_list.txt

  # Generate file list with specific file extensions
  python scripts/generate_file_list.py \\
    --root-dir /path/to/your/project \\
    --extensions py,js,ts,md
        """
    )
    
    parser.add_argument(
        "--root-dir",
        default=".",
        help="Root directory to scan for files (default: current directory)"
    )
    
    parser.add_argument(
        "--output",
        default="data/file_list.txt",
        help="Output file path (default: data/file_list.txt)"
    )
    
    parser.add_argument(
        "--extensions",
        help="Comma-separated list of file extensions to include (e.g., py,js,ts,md)"
    )
    
    parser.add_argument(
        "--exclude-dirs",
        help="Comma-separated list of directories to exclude (e.g., node_modules,.git,venv)"
    )
    
    parser.add_argument(
        "--absolute-paths",
        action="store_true",
        default=True,
        help="Use absolute paths in the output (default: True)"
    )
    
    parser.add_argument(
        "--relative-paths",
        dest="absolute_paths",
        action="store_false",
        help="Use relative paths in the output"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output"
    )
    
    args = parser.parse_args()
    
    # Parse extensions if provided
    extensions = None
    if args.extensions:
        extensions = [ext.strip().lower() for ext in args.extensions.split(",")]
    
    # Parse exclude directories if provided
    exclude_dirs = None
    if args.exclude_dirs:
        exclude_dirs = [dir.strip() for dir in args.exclude_dirs.split(",")]
    
    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    print(f"🔄 Generating file list...")
    print(f"   Root directory: {os.path.abspath(args.root_dir)}")
    print(f"   Output file: {args.output}")
    print(f"   Extensions: {extensions or 'all'}")
    print(f"   Exclude dirs: {exclude_dirs or 'none'}")
    print(f"   Path type: {'absolute' if args.absolute_paths else 'relative'}")
    print()
    
    try:
        # Generate the file list
        file_paths = generate_file_list_from_path(
            root_dir=args.root_dir,
            extensions=extensions,
            exclude_dirs=exclude_dirs,
            absolute_paths=args.absolute_paths
        )
        
        # Write to output file
        with open(args.output, 'w') as f:
            for file_path in file_paths:
                f.write(f"{file_path}\n")
        
        print(f"✅ File list generated successfully!")
        print(f"   Total files: {len(file_paths)}")
        print(f"   Output file: {args.output}")
        
        if args.verbose and file_paths:
            print(f"\n📋 First 10 files:")
            for i, file_path in enumerate(file_paths[:10], 1):
                print(f"   {i}. {file_path}")
            if len(file_paths) > 10:
                print(f"   ... and {len(file_paths) - 10} more files")
        
        print(f"\n💡 Next steps:")
        print(f"   1. Review the file list: cat {args.output}")
        print(f"   2. Filter unwanted files: python scripts/filter_file_list.py --input {args.output}")
        print(f"   3. Process the files: python scripts/batch_process.py --file-list {args.output}")
        
    except Exception as e:
        print(f"❌ Error generating file list: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 