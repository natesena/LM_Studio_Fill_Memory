#!/usr/bin/env python3
"""
Git Memory Processor with Graphiti Integration

This script processes Git commit data and creates individual memories for each commit
using the Graphiti MCP tool. Each commit becomes a discrete memory with its own
timestamp, allowing the knowledge graph to track the evolution of the codebase over time.
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Optional
import re

# Import the Graphiti MCP tool
# Note: In a real implementation, this would be the actual MCP tool call
def add_memory_to_graphiti(name: str, episode_body: str, source: str = "git_commit", 
                          source_description: str = "", group_id: Optional[str] = None, 
                          uuid: Optional[str] = None) -> Dict:
    """
    Add a memory to Graphiti knowledge graph using the MCP tool.
    
    This function would call the actual Graphiti MCP add_memory tool.
    For demonstration, we'll use the mcp_graphiti_add_memory function.
    """
    try:
        # This would be the actual MCP tool call
        # result = mcp_graphiti_add_memory(
        #     name=name,
        #     episode_body=episode_body,
        #     source=source,
        #     source_description=source_description,
        #     group_id=group_id,
        #     uuid=uuid
        # )
        
        # For now, we'll simulate the call
        print(f"Adding memory to Graphiti: {name}")
        print(f"Content: {episode_body[:200]}...")
        print("-" * 50)
        
        return {"result": {"message": f"Episode '{name}' queued for processing"}}
        
    except Exception as e:
        print(f"Error adding memory to Graphiti: {e}")
        return {"error": str(e)}

def get_git_log_data(repo_path: str, since: str = "1 week ago") -> str:
    """Get Git log data for the specified repository and time period."""
    try:
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--stat", "--format=fuller"],
            cwd=repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout
    except Exception as e:
        print(f"Error getting Git log: {e}")
        return ""

def parse_git_log(git_log_output: str) -> List[Dict]:
    """Parse Git log output into structured commit data."""
    commits = []
    current_commit = {}
    lines = git_log_output.strip().split('\n')
    
    for line in lines:
        if line.startswith('commit '):
            # Save previous commit if exists
            if current_commit:
                commits.append(current_commit)
            
            # Start new commit
            commit_hash = line.split()[1]
            current_commit = {
                'hash': commit_hash,
                'author': '',
                'date': '',
                'message': '',
                'files_changed': [],
                'insertions': 0,
                'deletions': 0
            }
        
        elif line.startswith('Author: '):
            current_commit['author'] = line.replace('Author: ', '').strip()
        
        elif line.startswith('Date: '):
            date_str = line.replace('Date: ', '').strip()
            try:
                # Parse date string like "Sun Aug 3 22:41:25 2025 -0400"
                dt = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
                current_commit['date'] = dt.isoformat()
            except:
                current_commit['date'] = date_str
        
        elif line.startswith('    ') and not line.startswith('    ' * 2):
            # This is part of the commit message
            current_commit['message'] += line.strip() + '\n'
        
        elif line and not line.startswith(' ') and '|' in line:
            # This is a file change line like "src/file.js | 10 +++++-----"
            parts = line.split('|')
            if len(parts) == 2:
                filename = parts[0].strip()
                change_info = parts[1].strip()
                
                # Parse change info like "10 +++++-----"
                change_match = re.match(r'(\d+)\s*(\+*)(-*)', change_info)
                if change_match:
                    insertions = len(change_match.group(2))
                    deletions = len(change_match.group(3))
                    current_commit['files_changed'].append({
                        'filename': filename,
                        'insertions': insertions,
                        'deletions': deletions
                    })
                    current_commit['insertions'] += insertions
                    current_commit['deletions'] += deletions
    
    # Add the last commit
    if current_commit:
        commits.append(current_commit)
    
    return commits

def categorize_commit(commit_message: str) -> str:
    """Categorize commit based on its message."""
    message_lower = commit_message.lower()
    
    if any(word in message_lower for word in ['fix', 'bug', 'resolve', 'correct']):
        return "bug_fix"
    elif any(word in message_lower for word in ['feat', 'add', 'implement', 'create']):
        return "feature"
    elif any(word in message_lower for word in ['docs', 'documentation']):
        return "documentation"
    elif any(word in message_lower for word in ['refactor', 'restructure']):
        return "refactoring"
    elif any(word in message_lower for word in ['cleanup', 'remove', 'delete']):
        return "cleanup"
    else:
        return "other"

def create_commit_memory(commit_data: Dict) -> Dict:
    """Create a memory entry for a single commit."""
    category = categorize_commit(commit_data['message'])
    
    # Create structured memory content
    memory_content = {
        "commit_hash": commit_data['hash'],
        "author": commit_data['author'],
        "date": commit_data['date'],
        "category": category,
        "message": commit_data['message'].strip(),
        "files_changed": commit_data['files_changed'],
        "total_insertions": commit_data['insertions'],
        "total_deletions": commit_data['deletions'],
        "impact_summary": f"Modified {len(commit_data['files_changed'])} files with {commit_data['insertions']} insertions and {commit_data['deletions']} deletions"
    }
    
    # Create memory name
    memory_name = f"Git Commit: {commit_data['hash'][:8]} - {category.replace('_', ' ').title()}"
    
    # Create episode body as JSON string
    episode_body = json.dumps(memory_content, indent=2)
    
    return {
        "name": memory_name,
        "episode_body": episode_body,
        "source": "git_commit",
        "source_description": f"Git commit from {commit_data['date']}",
        "group_id": "ai_message_development_timeline",
        "uuid": commit_data['hash']  # Use commit hash as UUID
    }

def process_git_commits_to_memories(repo_path: str, since: str = "1 week ago") -> List[Dict]:
    """Process Git commits and create memories for each one."""
    print(f"Processing Git commits from {repo_path} since {since}...")
    
    # Get Git log data
    git_log = get_git_log_data(repo_path, since)
    if not git_log:
        print("No Git log data found.")
        return []
    
    # Parse commits
    commits = parse_git_log(git_log)
    print(f"Found {len(commits)} commits to process.")
    
    # Create memories for each commit
    memories = []
    for i, commit in enumerate(commits, 1):
        print(f"\nProcessing commit {i}/{len(commits)}: {commit['hash'][:8]}")
        
        memory_data = create_commit_memory(commit)
        memories.append(memory_data)
        
        # Add to Graphiti using the MCP tool
        result = add_memory_to_graphiti(**memory_data)
        
        if "error" in result:
            print(f"Error adding memory for commit {commit['hash'][:8]}: {result['error']}")
        else:
            print(f"Successfully added memory for commit {commit['hash'][:8]}")
    
    print(f"\nCreated {len(memories)} memory entries.")
    return memories

def main():
    """Main function to process Git commits and create memories."""
    if len(sys.argv) < 2:
        print("Usage: python git_memory_processor_with_graphiti.py <repo_path> [since]")
        print("Example: python git_memory_processor_with_graphiti.py /path/to/repo '1 week ago'")
        sys.exit(1)
    
    repo_path = sys.argv[1]
    since = sys.argv[2] if len(sys.argv) > 2 else "1 week ago"
    
    try:
        memories = process_git_commits_to_memories(repo_path, since)
        
        # Save memories to file for reference
        output_file = f"git_memories_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(memories, f, indent=2)
        
        print(f"Memory data saved to {output_file}")
        
    except Exception as e:
        print(f"Error processing Git commits: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 