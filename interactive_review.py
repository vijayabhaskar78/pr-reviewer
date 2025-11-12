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
from groq import Groq

def get_pr_context(github_token, repo, pr_number):
    """Fetch PR details and recent comments"""
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    # Get PR details
    pr_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    pr_response = requests.get(pr_url, headers=headers)
    pr_data = pr_response.json()
    
    # Get PR diff
    diff_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    diff_headers = headers.copy()
    diff_headers['Accept'] = 'application/vnd.github.v3.diff'
    diff_response = requests.get(diff_url, headers=diff_headers)
    
    # Get comments
    comments_url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    comments_response = requests.get(comments_url, headers=headers)
    comments = comments_response.json()
    
    # Get review comments (inline)
    review_comments_url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/comments"
    review_comments_response = requests.get(review_comments_url, headers=headers)
    review_comments = review_comments_response.json()
    
    return {
        'pr': pr_data,
        'diff': diff_response.text,
        'comments': comments,
        'review_comments': review_comments
    }

def get_comment_thread(comments, comment_id):
    """Get the conversation thread for a specific comment"""
    thread = []
    for comment in comments:
        if comment.get('id') == comment_id or comment.get('in_reply_to_id') == comment_id:
            thread.append({
                'user': comment['user']['login'],
                'body': comment['body'],
                'created_at': comment['created_at']
            })
    return thread

def parse_bot_mention(comment_body):
    """Extract the question/command after @pr-reviewer mention"""
    # Remove @pr-reviewer or @bot mention
    text = comment_body.replace('@pr-reviewer', '').replace('@bot', '').strip()
    
    # Check for commands
    if text.startswith('/'):
        parts = text.split(' ', 1)
        command = parts[0][1:]  # Remove the /
        args = parts[1] if len(parts) > 1 else ""
        return {'type': 'command', 'command': command, 'args': args}
    else:
        return {'type': 'question', 'question': text}

def handle_interactive_response(groq_client, model, context, user_query, comment_context=None):
    """Generate an interactive response using Groq"""
    
    # Build conversation context
    pr_title = context['pr']['title']
    pr_body = context['pr'].get('body', '')
    diff = context['diff'][:4000]  # Limit diff size
    
    # Build the prompt
    system_prompt = """You are an expert code reviewer and programming assistant. 
You're having a conversation with a developer about their pull request. 
Be helpful, concise, and provide actionable advice. 
Use code examples when relevant.
Be friendly but professional."""
    
    conversation_history = []
    
    # Add PR context
    conversation_history.append({
        'role': 'system',
        'content': f"""PR Context:
Title: {pr_title}
Description: {pr_body}

Recent diff (partial):
```
{diff}
```"""
    })
    
    # Add thread context if replying to a specific comment
    if comment_context:
        conversation_history.append({
            'role': 'assistant',
            'content': f"Previous context: {comment_context}"
        })
    
    # Add user's question
    conversation_history.append({
        'role': 'user',
        'content': user_query
    })
    
    # Call Groq
    try:
        response = groq_client.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': system_prompt}
            ] + conversation_history,
            temperature=0.7,
            max_tokens=1024
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Sorry, I encountered an error: {e}"

def handle_command(command, args, context, groq_client, model):
    """Handle special commands"""
    if command == 'review':
        return "🔄 Starting a fresh review of the current PR state..."
    elif command == 'explain':
        query = f"Please explain this code change in detail: {args}"
        return handle_interactive_response(groq_client, model, context, query)
    elif command == 'security':
        query = "Review this PR specifically for security vulnerabilities"
        return handle_interactive_response(groq_client, model, context, query)
    elif command == 'performance':
        query = "Review this PR specifically for performance issues"
        return handle_interactive_response(groq_client, model, context, query)
    elif command == 'tests':
        query = "What tests should be added for this PR?"
        return handle_interactive_response(groq_client, model, context, query)
    elif command == 'help':
        return """**Available Commands:**
- `/review` - Re-run the full review
- `/explain [topic]` - Explain a specific part of the code
- `/security` - Focus on security issues
- `/performance` - Focus on performance
- `/tests` - Suggest tests
- `/help` - Show this help

You can also just ask me questions directly by mentioning @pr-reviewer!

**Examples:**
- "@pr-reviewer why is this approach better?"
- "@pr-reviewer /explain the async implementation"
- "@pr-reviewer what's wrong with my error handling?"
"""
    else:
        return f"Unknown command: `/{command}`. Type `/help` for available commands."

def post_reply(github_token, repo, comment_id, body, is_review_comment=False):
    """Post a reply to a comment"""
    headers = {
        'Authorization': f'Bearer {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    if is_review_comment:
        # Reply to review comment (inline comment)
        url = f"https://api.github.com/repos/{repo}/pulls/comments/{comment_id}/replies"
    else:
        # Reply to issue comment
        url = f"https://api.github.com/repos/{repo}/issues/comments"
    
    data = {'body': body}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Failed to post reply: {e}", file=sys.stderr)
        return False

def main():
    # Get environment variables
    github_token = os.environ.get('GITHUB_TOKEN')
    repo = os.environ.get('GITHUB_REPOSITORY')
    pr_number = os.environ.get('PR_NUMBER')
    comment_id = os.environ.get('COMMENT_ID')
    comment_body = os.environ.get('COMMENT_BODY')
    is_review_comment = os.environ.get('IS_REVIEW_COMMENT', 'false') == 'true'
    groq_api_key = os.environ.get('GROQ_API_KEY')
    model = os.environ.get('MODEL', 'llama-3.1-70b-versatile')
    
    if not all([github_token, repo, pr_number, comment_id, comment_body, groq_api_key]):
        print("Missing required environment variables", file=sys.stderr)
        sys.exit(1)
    
    # Initialize Groq client
    groq_client = Groq(api_key=groq_api_key)
    
    # Get PR context
    print("📥 Fetching PR context...", file=sys.stderr)
    context = get_pr_context(github_token, repo, pr_number)
    
    # Parse the mention
    parsed = parse_bot_mention(comment_body)
    
    # Generate response
    print(f"🤖 Processing {parsed['type']}...", file=sys.stderr)
    
    if parsed['type'] == 'command':
        response = handle_command(
            parsed['command'],
            parsed['args'],
            context,
            groq_client,
            model
        )
    else:
        response = handle_interactive_response(
            groq_client,
            model,
            context,
            parsed['question']
        )
    
    # Post the response
    print("💬 Posting response...", file=sys.stderr)
    
    # Format the response with a bot signature
    formatted_response = f"{response}\n\n---\n*🤖 Powered by Groq | Reply with @pr-reviewer to continue the conversation*"
    
    success = post_reply(github_token, repo, comment_id, formatted_response, is_review_comment)
    
    if success:
        print("✅ Response posted successfully!", file=sys.stderr)
    else:
        print("❌ Failed to post response", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
