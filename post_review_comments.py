#!/usr/bin/env python3
# Copyright 2025 vijayabhaskar78
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import json
import requests
import re

def parse_diff_for_line_mapping(diff_text):
    """
    Parse git diff to map file paths to changed line numbers.
    Returns a dict: {file_path: [list of changed line numbers]}
    """
    file_lines = {}
    current_file = None
    current_line = 0
    
    for line in diff_text.split('\n'):
        # New file
        if line.startswith('diff --git'):
            current_file = None
        elif line.startswith('+++'):
            # Extract file path (remove +++ b/ prefix)
            match = re.match(r'\+\+\+ b/(.*)', line)
            if match:
                current_file = match.group(1)
                if current_file not in file_lines:
                    file_lines[current_file] = []
        elif line.startswith('@@'):
            # Parse hunk header: @@ -old_start,old_count +new_start,new_count @@
            match = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
            if match:
                current_line = int(match.group(1))
        elif current_file and line.startswith('+') and not line.startswith('+++'):
            # This is an added line
            file_lines[current_file].append(current_line)
            current_line += 1
        elif current_file and not line.startswith('-'):
            # Context line
            current_line += 1
    
    return file_lines

def severity_emoji(severity):
    """Return emoji for severity level"""
    emoji_map = {
        'CRITICAL': '🔴',
        'WARNING': '🟡',
        'SUGGESTION': '🟢',
        'INFO': '💡'
    }
    return emoji_map.get(severity.upper(), '💬')

def format_review_comment(review):
    """Format a review comment with severity and suggestion"""
    emoji = severity_emoji(review.get('severity', 'INFO'))
    severity = review.get('severity', 'INFO')
    message = review.get('message', '')
    suggestion = review.get('suggestion', '')
    
    comment = f"{emoji} **{severity}**\n\n{message}"
    
    if suggestion:
        comment += f"\n\n**Suggested fix:**\n```\n{suggestion}\n```"
    
    return comment

def post_review_comments(github_token, repo, pr_number, commit_sha, reviews, diff_text):
    """
    Post inline review comments to GitHub PR.
    Uses GitHub's Pull Request Review API.
    """
    # Parse diff to get line mappings
    file_lines = parse_diff_for_line_mapping(diff_text)
    
    # Prepare review comments
    comments = []
    general_comment_parts = []
    
    for review in reviews:
        file = review.get('file', '')
        line = review.get('line', 0)
        
        # Skip error entries
        if file in ['error', 'general'] or line == 0:
            general_comment_parts.append(format_review_comment(review))
            continue
        
        # Find the closest changed line
        if file in file_lines and file_lines[file]:
            # Find the nearest changed line
            changed_lines = file_lines[file]
            if changed_lines:
                # Use the closest changed line
                closest_line = min(changed_lines, key=lambda x: abs(x - line))
                
                comments.append({
                    'path': file,
                    'line': closest_line,
                    'body': format_review_comment(review)
                })
            else:
                general_comment_parts.append(f"**{file}:{line}**\n{format_review_comment(review)}")
        else:
            general_comment_parts.append(f"**{file}:{line}**\n{format_review_comment(review)}")
    
    # Create the review
    api_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/reviews"
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    review_data = {
        'commit_id': commit_sha,
        'event': 'COMMENT',
        'comments': comments
    }
    
    # Add general comment body if there are general issues
    if general_comment_parts:
        review_title = os.environ.get('REVIEW_TITLE', '# Code Review by Groq')
        review_data['body'] = f"{review_title}\n\n" + "\n\n---\n\n".join(general_comment_parts)
    
    # Only post if we have comments or a body
    if comments or general_comment_parts:
        try:
            response = requests.post(api_url, headers=headers, json=review_data)
            response.raise_for_status()
            print(f"✅ Posted review with {len(comments)} inline comments", file=sys.stderr)
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to post review: {e}", file=sys.stderr)
            if hasattr(e, 'response') and e.response is not None:
                print(f"Response: {e.response.text}", file=sys.stderr)
            return False
    else:
        print("✅ No issues found - PR looks good!", file=sys.stderr)
        return True

def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    pr_number = os.environ.get('PR_NUMBER')
    commit_sha = os.environ.get('COMMIT_SHA')
    
    if not all([github_token, repo, pr_number, commit_sha]):
        print("Missing required environment variables", file=sys.stderr)
        sys.exit(1)
    
    # Read reviews JSON from stdin
    try:
        reviews = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"Failed to parse reviews JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Read diff file
    diff_file = os.environ.get('DIFF_FILE', 'diff.txt')
    try:
        with open(diff_file, 'r') as f:
            diff_text = f.read()
    except FileNotFoundError:
        print(f"Diff file not found: {diff_file}", file=sys.stderr)
        diff_text = ""
    
    # Post comments
    success = post_review_comments(github_token, repo, pr_number, commit_sha, reviews, diff_text)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
