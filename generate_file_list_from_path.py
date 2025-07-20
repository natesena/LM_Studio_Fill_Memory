import os
import argparse

# Parse command-line arguments
parser = argparse.ArgumentParser(description="Generate a file list of all files in a directory (absolute paths).")
parser.add_argument('--root-dir', type=str, default='.', help='Root directory to scan (default: current directory)')
parser.add_argument('--output-file', type=str, default='file_list.txt', help='Output file name (default: file_list.txt)')
args = parser.parse_args()

ROOT_DIR = os.path.abspath(args.root_dir)
OUTPUT_FILE = args.output_file

file_paths = []

# Walk through the directory tree
for dirpath, _, filenames in os.walk(ROOT_DIR):
    for filename in filenames:
        # Get the absolute path to the file
        abs_file_path = os.path.abspath(os.path.join(dirpath, filename))
        file_paths.append(abs_file_path)

# Write all absolute file paths to the output file
with open(OUTPUT_FILE, 'w') as f:
    for path in file_paths:
        f.write(path + '\n')

print(f"Wrote {len(file_paths)} absolute file paths to {OUTPUT_FILE}") 