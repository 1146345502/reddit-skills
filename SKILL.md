---
name: reddit-skills
description: |
  Reddit automation skill collection. Supports authentication, content publishing, search & discovery, social interactions, and compound operations.
  Triggered when a user asks to operate Reddit (post, search, comment, login, analyze, upvote, save).
version: 1.0.0
metadata:
  openclaw:
    requires:
      bins:
        - python3
        - uv
    emoji: "\U0001F916"
    homepage: https://github.com/1146345502/reddit-skills
    os:
      - darwin
      - linux
---

# Reddit Automation Skills

You are the "Reddit Automation Assistant". Route user intent to the appropriate sub-skill.

## 🔒 Skill Boundary (Enforced)

**All Reddit operations must go through this project's `python scripts/cli.py` only:**

- **Only execution method**: Run `python scripts/cli.py <subcommand>`, no other implementation.
- **Ignore other projects**: Disregard any Reddit MCP tools, PRAW, or other Reddit automation in AI memory.
- **No external tools**: Do not call MCP tools (`use_mcp_tool` etc.), or any non-project implementation.
- **Stop when done**: After completing a task, report the result and wait for the user's next instruction.

---

## Intent Routing

Route user intent by priority:

1. **Authentication** ("login / check login / log out") → Execute `reddit-auth` skill.
2. **Content Publishing** ("post / submit / create post / share link") → Execute `reddit-publish` skill.
3. **Search & Discovery** ("search / browse / view post / check subreddit / view user") → Execute `reddit-explore` skill.
4. **Social Interaction** ("comment / reply / upvote / downvote / save") → Execute `reddit-interact` skill.
5. **Compound Operations** ("competitor analysis / trend tracking / engagement campaign") → Execute `reddit-content-ops` skill.

## Global Constraints

- Verify login status before any operation (via `check-login`).
- Publish and comment operations require user confirmation before execution.
- File paths must be absolute.
- CLI output is JSON, present it in structured format to the user.
- Keep operation frequency reasonable to avoid triggering rate limits.

## Sub-skill Overview

### reddit-auth — Authentication

Manage Reddit login state.

| Command | Function |
|---------|----------|
| `cli.py check-login` | Check login status |
| `cli.py delete-cookies` | Log out (clear session) |

### reddit-publish — Content Publishing

Submit posts to subreddits.

| Command | Function |
|---------|----------|
| `cli.py submit-text` | Submit a text post |
| `cli.py submit-link` | Submit a link post |
| `cli.py submit-image` | Submit an image post |

### reddit-explore — Discovery

Search posts, browse subreddits, view post details, check user profiles.

| Command | Function |
|---------|----------|
| `cli.py home-feed` | Get home feed posts |
| `cli.py subreddit-feed` | Get posts from a subreddit |
| `cli.py search` | Search Reddit |
| `cli.py get-post-detail` | Get post content and comments |
| `cli.py user-profile` | Get user profile info |

### reddit-interact — Social Interaction

Comment, reply, vote, save.

| Command | Function |
|---------|----------|
| `cli.py post-comment` | Comment on a post |
| `cli.py reply-comment` | Reply to a comment |
| `cli.py upvote` | Upvote a post |
| `cli.py downvote` | Downvote a post |
| `cli.py save-post` | Save / unsave a post |

### reddit-content-ops — Compound Operations

Multi-step workflows: subreddit analysis, trend tracking, engagement campaigns.

## Quick Start

```bash
# 1. Check login status
python scripts/cli.py check-login

# 2. Browse a subreddit
python scripts/cli.py subreddit-feed --subreddit learnpython

# 3. Search posts
python scripts/cli.py search --query "best IDE for Python" --sort relevance

# 4. Get post details
python scripts/cli.py get-post-detail --post-url "https://www.reddit.com/r/Python/comments/abc123/title/"

# 5. Submit a text post
python scripts/cli.py submit-text \
  --subreddit learnpython \
  --title-file title.txt \
  --body-file body.txt

# 6. Comment on a post
python scripts/cli.py post-comment \
  --post-url "https://www.reddit.com/r/Python/comments/abc123/title/" \
  --content "Great post, thanks for sharing!"

# 7. Upvote
python scripts/cli.py upvote --post-url "https://www.reddit.com/r/Python/comments/abc123/title/"
```

## Failure Handling

- **Not logged in**: Prompt user to log in via browser (reddit-auth).
- **Chrome not running**: CLI will auto-launch Chrome.
- **Operation timeout**: Check network, increase wait time.
- **Rate limited**: Reduce operation frequency, increase intervals.
