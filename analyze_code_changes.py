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
from groq import Groq

# Set up Groq credentials
if not os.environ.get("GROQ_API_KEY"):
    print("No Groq API key found")
    sys.exit(1)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

model_engine = os.environ["MODEL"]
commit_title = os.environ["COMMIT_TITLE"]
commit_message = os.environ["COMMIT_BODY"]
max_length = int(os.environ["MAX_LENGTH"])

# Analyze the code changes
code = sys.stdin.read()
header = (f"Commit title is '{commit_title}'\n"
          f"and commit message is '{commit_message}'\n")

# Enhanced prompt for structured output
enhanced_prompt = f"""You are an expert code reviewer. Review the following git diff and provide structured feedback.

For each issue you find, provide:
1. The file path
2. The approximate line number in the diff (if applicable)
3. Severity level: CRITICAL (security/bugs), WARNING (performance/code smell), or SUGGESTION (style/best practices)
4. A clear description of the issue
5. An optional code suggestion to fix it

Format your response as a JSON array like this:
[
  {{
    "file": "path/to/file.py",
    "line": 42,
    "severity": "CRITICAL",
    "message": "Potential SQL injection vulnerability",
    "suggestion": "Use parameterized queries instead"
  }}
]

If there are no issues, return an empty array: []

Git diff to review:
```
{code}
```

Commit context:
- Title: {commit_title}
- Message: {commit_message}

Return ONLY the JSON array, no other text."""

if len(enhanced_prompt) > max_length:
    print(f"Prompt too long: {len(enhanced_prompt)} characters, "
          f"sending only first {max_length} characters", file=sys.stderr)
    enhanced_prompt = enhanced_prompt[:max_length]

kwargs = {'model': model_engine}
kwargs['temperature'] = 0.3  # Lower for more consistent JSON
kwargs['max_tokens'] = 2048  # More tokens for detailed reviews
kwargs['messages'] = [
    {"role": "system",
     "content": "You are an expert code reviewer. Always respond with valid JSON."},
    {"role": "user", "content": enhanced_prompt},
]

try:
    response = client.chat.completions.create(**kwargs)
    if response.choices:
        review_text = response.choices[0].message.content.strip()
        
        # Try to parse as JSON
        try:
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in review_text:
                review_text = review_text.split("```json")[1].split("```")[0].strip()
            elif "```" in review_text:
                review_text = review_text.split("```")[1].split("```")[0].strip()
            
            reviews = json.loads(review_text)
            
            # Output structured JSON for processing
            print(json.dumps(reviews, indent=2))
            
        except json.JSONDecodeError:
            # Fallback: treat as plain text review
            print(json.dumps([{
                "file": "general",
                "line": 0,
                "severity": "SUGGESTION",
                "message": review_text,
                "suggestion": ""
            }], indent=2))
    else:
        print(json.dumps([{
            "file": "error",
            "line": 0,
            "severity": "CRITICAL",
            "message": f"No response from Groq: {response}",
            "suggestion": ""
        }], indent=2))
except Exception as e:
    print(json.dumps([{
        "file": "error",
        "line": 0,
        "severity": "CRITICAL",
        "message": f"Groq API error: {e}",
        "suggestion": ""
    }], indent=2))
