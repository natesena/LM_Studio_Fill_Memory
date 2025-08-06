#!/usr/bin/env python3
import re

# Test the regex pattern from the queue monitor
log_line = "Processing queued episode '/Users/nathanielsena/Documents/code/Kismet/custom-chat-element/index.html' for group_id: default"
pattern = r"Processing queued episode '([^']+)' for group_id: ([^\s]+)"

print(f"Log line: {log_line}")
print(f"Pattern: {pattern}")

match = re.search(pattern, log_line)
if match:
    print(f"✅ Match found: {match.group()}")
    print(f"   Episode name: {match.group(1)}")
    print(f"   Group ID: {match.group(2)}")
else:
    print("❌ No match found")

# Test with the actual logs from Docker
print("\n--- Testing with actual Docker logs ---")
docker_logs = """
2025-07-20 16:37:36,790 - __main__ - INFO - Processing queued episode 'CLI_Memory' for group_id: default
2025-07-20 16:44:23,681 - __main__ - ERROR - Error processing episode 'CLI_Memory' for group_id default: list index out of range
2025-07-20 16:44:23,681 - __main__ - INFO - Processing queued episode '/Users/nathanielsena/Documents/code/Kismet/custom-chat-element/index.html' for group_id: default
"""

matches = re.findall(pattern, docker_logs)
print(f"Found {len(matches)} matches:")
for i, match in enumerate(matches, 1):
    print(f"  {i}. Episode: '{match[0]}', Group: {match[1]}") 