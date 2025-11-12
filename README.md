# Groq Code Review Action

This action uses Groq's fast language models to review code changes in a pull request with **inline comments, severity levels, and smart suggestions**.

## ✨ Features

- 🎯 **Inline Comments**: Comments on specific lines of code, not just general PR feedback
- 📊 **Severity Levels**: Issues categorized as Critical (🔴), Warning (🟡), or Suggestion (🟢)
- 💡 **Smart Suggestions**: Actionable code fixes for each issue
- ⚡ **Fast**: Powered by Groq's lightning-fast inference
- 🔧 **Customizable**: Adjust models, prompts, and review style

## Usage

To use this action, include it as a step in your workflow, after the checkout step.

```yaml

on: [pull_request]

jobs:
  code-review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      # This step checks out a copy of your repository.
      - uses: actions/checkout@v4
      # This step references the directory that contains the action.
      - uses: vijayabhaskar78/pr-reviewer@v1.0
        with:
          groq-key: ${{ secrets.GROQ_API_KEY }}
          # Optional parameters:
          # inline-comments: true  # Enable inline comments (default: true)
          # model: 'llama-3.1-70b-versatile'
          # max-length: 8000
          # prompt: 'Only suggest performance improvements for this code.'
          # post-if-error: false
          # review-title: '# My AI bot review'

```

The action will post inline review comments directly on the changed lines in your pull request.

### Requierements

To post comments in Pull Requests, the job requires additional permissions: `pull-requests: write`. However, since this permission implies "explicit deny," we also need to mention the default permission `contents: read`.

### Inputs

`github-token`: The token used to authenticate with the GitHub API (optional, will take a default `${{ github.token }}`).

`model`: The Groq language model to use for code review (optional, with a default `llama-3.1-70b-versatile`).

`groq-key`: The Groq API key used for authentication (**required**).

`prompt`: The prompt to use for the analysis (optional, with a default value).

`max-length`: The diff that is sent to Groq for review is cut off after 8000 characters by default. With this parameter you can adjust this limit.

`post-if-error`: Whether to post a comment if there was an error (optional, with a default `true`).

`review-title`: The title to use for the review comment (optional, with a default `Code Review by Groq`).

`inline-comments`: Enable inline comments on specific lines (optional, with a default `true`). Set to `false` for old-style single comment.

## How It Works

1. **Analysis**: The action fetches the git diff and sends it to Groq's AI
2. **Structured Review**: Groq returns a structured review with file paths, line numbers, severity levels, and suggestions
3. **Inline Comments**: The action posts comments directly on the relevant lines in your PR
4. **Severity Badges**: Each comment is tagged with 🔴 Critical, 🟡 Warning, or 🟢 Suggestion
5. **Interactive Mode**: Mention `@pr-reviewer` in any comment to ask questions and get instant help!

## 🤖 Interactive Features

You can have conversations with the AI reviewer! Just mention `@pr-reviewer` in any PR comment:

**Examples:**
- `@pr-reviewer why is this approach better?`
- `@pr-reviewer what's wrong with my error handling?`
- `@pr-reviewer how can I improve performance here?`

**Available Commands:**
- `/review` - Re-run the full review
- `/explain [topic]` - Explain a specific part of the code
- `/security` - Focus on security issues
- `/performance` - Focus on performance
- `/tests` - Suggest tests
- `/help` - Show all commands

To enable interactive mode, add this workflow to your repo as `.github/workflows/interactive-review.yml`:

```yaml
name: Interactive PR Review

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]

jobs:
  interactive-review:
    if: |
      (github.event.issue.pull_request || github.event.pull_request) && 
      (contains(github.event.comment.body, '@pr-reviewer') || 
       contains(github.event.comment.body, '@bot') ||
       startsWith(github.event.comment.body, '/'))
    
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      issues: write
    
    steps:
      - uses: actions/checkout@v4
        with:
          repository: vijayabhaskar78/pr-reviewer
          ref: main
          path: .pr-reviewer
      
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - run: pip install -r .pr-reviewer/requirements.txt
      
      - run: python .pr-reviewer/interactive_review.py
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
          GITHUB_REPOSITORY: ${{ github.repository }}
          PR_NUMBER: ${{ github.event.issue.number || github.event.pull_request.number }}
          COMMENT_ID: ${{ github.event.comment.id }}
          COMMENT_BODY: ${{ github.event.comment.body }}
          IS_REVIEW_COMMENT: ${{ github.event_name == 'pull_request_review_comment' }}
```

## Example Review Output

When a review is posted, you'll see:

```
🔴 CRITICAL

Potential SQL injection vulnerability. User input is directly interpolated into query.

Suggested fix:
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
```

### Limitations

Currently, only the first 8000 characters are sent. Later, we will send the text in chunks, and each part will be reviewed separately.

## Contributing

Contributions to this action are welcome! Please create an issue or pull request in the repository.

## Testing

You can run `./test.sh` that just verifies that the Python code is able to send something to Groq and get something out of it. (The model is kindly asked to tell "It works!").

The test expects you have Python 3.10 available as it is the one used in the action itself. There is an appropriate file `.python_version` for [pyenv](https://github.com/pyenv/pyenv).

## License

This action is licensed under the Apache 2.0 License. See the LICENSE file for details
