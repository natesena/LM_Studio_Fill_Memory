import argparse
import os
import fnmatch
from typing import List, Optional

# Default patterns to filter out
DEFAULT_FILTER_PATTERNS = [
    'node_modules',
    '.git',
    '.next',
    '.env',
    '__pycache__',
    '.pytest_cache',
    '.DS_Store',
    '*.log',
    '*.tmp',
    '*.cache',
]

def filter_file_list(
    file_paths: List[str],
    exclude_patterns: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    exclude_extensions: Optional[List[str]] = None,
    min_size: Optional[int] = None,
    max_size: Optional[int] = None
) -> List[str]:
    """
    Filter a list of file paths based on various criteria.
    
    Args:
        file_paths: List of file paths to filter
        exclude_patterns: List of glob patterns to exclude (e.g., ['*.log', '*.tmp'])
        exclude_dirs: List of directory names to exclude (e.g., ['node_modules', '.git'])
        exclude_extensions: List of file extensions to exclude (e.g., ['log', 'tmp'])
        min_size: Minimum file size in bytes
        max_size: Maximum file size in bytes
    
    Returns:
        Filtered list of file paths
    """
    if exclude_patterns is None:
        exclude_patterns = []
    if exclude_dirs is None:
        exclude_dirs = []
    if exclude_extensions is None:
        exclude_extensions = []
    
    filtered_files = []
    
    for file_path in file_paths:
        # Skip empty lines
        if not file_path.strip():
            continue
            
        # Check file size if specified
        if min_size is not None or max_size is not None:
            try:
                file_size = os.path.getsize(file_path)
                if min_size is not None and file_size < min_size:
                    continue
                if max_size is not None and file_size > max_size:
                    continue
            except (OSError, FileNotFoundError):
                # Skip files that can't be accessed
                continue
        
        # Check exclude patterns (glob patterns)
        if exclude_patterns:
            filename = os.path.basename(file_path)
            if any(fnmatch.fnmatch(filename, pattern) for pattern in exclude_patterns):
                continue
        
        # Check exclude directories
        if exclude_dirs:
            path_parts = file_path.split(os.sep)
            if any(dir_name in path_parts for dir_name in exclude_dirs):
                continue
        
        # Check exclude extensions
        if exclude_extensions:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
            if file_ext in exclude_extensions:
                continue
        
        filtered_files.append(file_path)
    
    return filtered_files

def filter_file(input_file, output_file, patterns):
    """Legacy function for backward compatibility."""
    with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
        for line in infile:
            if not any(pattern in line for pattern in patterns):
                outfile.write(line)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove lines containing unwanted patterns from a text file.")
    parser.add_argument('--input', type=str, required=True, help='Input file (e.g., file_list.txt)')
    parser.add_argument('--output', type=str, required=True, help='Output file (filtered result)')
    args = parser.parse_args()
    filter_file(args.input, args.output, FILTER_PATTERNS)
    print(f"Filtered {args.input} and wrote result to {args.output}") 