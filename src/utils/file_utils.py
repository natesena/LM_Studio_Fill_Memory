import os
import argparse
from typing import List, Optional

def generate_file_list_from_path(
    root_dir: str = ".",
    extensions: Optional[List[str]] = None,
    exclude_dirs: Optional[List[str]] = None,
    absolute_paths: bool = True
) -> List[str]:
    """
    Generate a list of file paths from a directory tree.
    
    Args:
        root_dir: Root directory to scan (default: current directory)
        extensions: List of file extensions to include (e.g., ['py', 'js', 'md'])
        exclude_dirs: List of directory names to exclude (e.g., ['node_modules', '.git'])
        absolute_paths: Whether to return absolute paths (default: True)
    
    Returns:
        List of file paths
    """
    if exclude_dirs is None:
        exclude_dirs = []
    
    root_dir = os.path.abspath(root_dir)
    file_paths = []
    
    # Walk through the directory tree
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Filter out excluded directories
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]
        
        for filename in filenames:
            # Check file extension if specified
            if extensions:
                file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
                if file_ext not in extensions:
                    continue
            
            # Get the file path
            file_path = os.path.join(dirpath, filename)
            
            # Convert to absolute path if requested
            if absolute_paths:
                file_path = os.path.abspath(file_path)
            
            file_paths.append(file_path)
    
    return file_paths

def main():
    """Legacy main function for backward compatibility."""
    parser = argparse.ArgumentParser(description="Generate a file list of all files in a directory (absolute paths).")
    parser.add_argument('--root-dir', type=str, default='.', help='Root directory to scan (default: current directory)')
    parser.add_argument('--output-file', type=str, default='file_list.txt', help='Output file name (default: file_list.txt)')
    args = parser.parse_args()

    file_paths = generate_file_list_from_path(root_dir=args.root_dir)
    
    # Write all file paths to the output file
    with open(args.output_file, 'w') as f:
        for path in file_paths:
            f.write(path + '\n')

    print(f"Wrote {len(file_paths)} file paths to {args.output_file}")

if __name__ == "__main__":
    main() 