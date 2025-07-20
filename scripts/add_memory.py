#!/usr/bin/env python3
"""
CLI script for adding a single memory via LM Studio and Graphiti.

This script provides a command-line interface to the memory addition functionality.
"""

import argparse
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.memory_adder import add_memory_via_lmstudio


def main():
    """Main CLI function for adding memories."""
    parser = argparse.ArgumentParser(
        description="Add a memory using LM Studio and Graphiti",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add a simple text memory
  python scripts/add_memory.py "Python is a programming language"

  # Add a memory with custom settings
  python scripts/add_memory.py "Machine learning basics" \\
    --lmstudio-url http://localhost:1234/v1/chat/completions \\
    --model qwen3-32b \\
    --rate-limit-delay 5

  # Add a memory from a file
  python scripts/add_memory.py --file path/to/file.txt
        """
    )
    
    parser.add_argument(
        "prompt",
        nargs="?",
        help="The prompt or content to add as a memory"
    )
    
    parser.add_argument(
        "--file", "-f",
        help="Read memory content from a file instead of using prompt argument"
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
        "--rate-limit-delay",
        type=float,
        default=2.0,
        help="Delay between memory additions in seconds (default: 2.0)"
    )
    
    parser.add_argument(
        "--check-queue",
        action="store_true",
        default=True,
        help="Check queue status before adding memory (default: True)"
    )
    
    parser.add_argument(
        "--no-check-queue",
        dest="check_queue",
        action="store_false",
        help="Skip queue status check"
    )
    
    args = parser.parse_args()
    
    # Validate input
    if not args.prompt and not args.file:
        parser.error("Either a prompt or --file must be provided")
    
    if args.prompt and args.file:
        parser.error("Cannot specify both prompt and --file")
    
    # Get the content to add
    if args.file:
        try:
            with open(args.file, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            print(f"❌ Error: File '{args.file}' not found")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading file '{args.file}': {e}")
            sys.exit(1)
    else:
        content = args.prompt
    
    # Format the prompt for the memory adder
    prompt = f"Please add a memory with the name '{os.path.basename(args.file) if args.file else 'CLI_Memory'}' and the following content: '{content}'"
    
    print(f"🔄 Adding memory...")
    print(f"   Content length: {len(content)} characters")
    print(f"   LM Studio URL: {args.lmstudio_url}")
    print(f"   Model: {args.model}")
    print(f"   Rate limit delay: {args.rate_limit_delay}s")
    print(f"   Check queue: {args.check_queue}")
    print()
    
    try:
        result = add_memory_via_lmstudio(
            prompt=prompt,
            lmstudio_url=args.lmstudio_url,
            model=args.model,
            rate_limit_delay=args.rate_limit_delay,
            check_queue=args.check_queue
        )
        
        if "successfully" in result.lower() or "queued" in result.lower():
            print(f"✅ {result}")
        else:
            print(f"❌ {result}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error adding memory: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 