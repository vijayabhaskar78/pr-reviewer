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

import sys
import json

def severity_emoji(severity):
    """Return emoji for severity level"""
    emoji_map = {
        'CRITICAL': '🔴',
        'WARNING': '🟡',
        'SUGGESTION': '🟢',
        'INFO': '💡'
    }
    return emoji_map.get(severity.upper(), '💬')

def format_reviews(reviews):
    """Format reviews as markdown"""
    if not reviews:
        return "✅ No issues found! Code looks good."
    
    # Group by severity
    critical = [r for r in reviews if r.get('severity', '').upper() == 'CRITICAL']
    warnings = [r for r in reviews if r.get('severity', '').upper() == 'WARNING']
    suggestions = [r for r in reviews if r.get('severity', '').upper() == 'SUGGESTION']
    others = [r for r in reviews if r.get('severity', '').upper() not in ['CRITICAL', 'WARNING', 'SUGGESTION']]
    
    output = []
    
    # Summary
    output.append(f"## Summary")
    output.append(f"Found **{len(reviews)}** review items:")
    if critical:
        output.append(f"- 🔴 {len(critical)} Critical")
    if warnings:
        output.append(f"- 🟡 {len(warnings)} Warnings")
    if suggestions:
        output.append(f"- 🟢 {len(suggestions)} Suggestions")
    output.append("")
    
    # Details
    for category, items in [("Critical Issues", critical), ("Warnings", warnings), ("Suggestions", suggestions), ("Other", others)]:
        if not items:
            continue
        
        output.append(f"## {category}")
        output.append("")
        
        for i, review in enumerate(items, 1):
            emoji = severity_emoji(review.get('severity', 'INFO'))
            file = review.get('file', 'unknown')
            line = review.get('line', 0)
            message = review.get('message', '')
            suggestion = review.get('suggestion', '')
            
            output.append(f"### {i}. {emoji} {file}")
            if line > 0:
                output.append(f"**Line {line}**")
            output.append("")
            output.append(message)
            
            if suggestion:
                output.append("")
                output.append("**Suggested fix:**")
                output.append("```")
                output.append(suggestion)
                output.append("```")
            
            output.append("")
            output.append("---")
            output.append("")
    
    return "\n".join(output)

def main():
    try:
        reviews = json.load(sys.stdin)
        print(format_reviews(reviews))
    except json.JSONDecodeError as e:
        print(f"Error parsing review JSON: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
