import argparse

# List of patterns to filter out
FILTER_PATTERNS = [
    'node_modules',
    '.git',
    '.next',
    '.env',  # Remove .env files as well
]

def filter_file(input_file, output_file, patterns):
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