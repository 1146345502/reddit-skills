# reddit-skills

Reddit automation Skills — directly uses your logged-in browser and real account, operating Reddit as an ordinary user.

Supports OpenClaw and all AI Agent platforms compatible with the `SKILL.md` format (e.g. Claude Code).

> **⚠️ Usage advice**: Although this project uses your real browser and account, you should still **control operation frequency** and avoid mass actions in a short time. Aggressive automation may trigger Reddit's rate limits or account restrictions.

## Features

| Skill | Description | Core Capabilities |
|-------|-------------|-------------------|
| **reddit-auth** | Authentication | Login check, session management |
| **reddit-publish** | Content Publishing | Text / link / image post submission |
| **reddit-explore** | Discovery | Search, subreddit browsing, post details, user profiles |
| **reddit-interact** | Social Interaction | Comment, reply, upvote, downvote, save |
| **reddit-content-ops** | Compound Ops | Subreddit analysis, trend tracking, engagement campaigns |

Supports **chained operations** — you can give compound natural-language instructions and the Agent will automatically chain multiple skills. For example:

> "Search r/Python for the most upvoted posts about FastAPI this week, save the top one, and tell me what it's about"

The Agent will execute: search → filter by top/week → save → get detail → summarize.

## Installation

### Prerequisites

* Python >= 3.11
* [uv](https://docs.astral.sh/uv/) package manager
* Google Chrome browser

### Step 1: Install the project

**Option A: Download ZIP (recommended)**

Download from GitHub and extract to your Agent skills directory:

```
# OpenClaw
<openclaw-project>/skills/reddit-skills/

# Claude Code
<your-project>/.claude/skills/reddit-skills/
```

**Option B: Git Clone**

```bash
cd <your-agent-project>/skills/
git clone https://github.com/1146345502/reddit-skills.git
```

Then install Python dependencies:

```bash
cd reddit-skills
uv sync
```

### Step 2: Install the browser extension

The extension lets the AI operate Reddit in your browser using your real login session.

1. Open Chrome, navigate to `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**, select this project's `extension/` directory
4. Confirm the **Reddit Bridge** extension is enabled

Once installed, you're ready to go — all actions happen in your own browser, using your real account.

## Usage

### As an AI Agent skill (recommended)

After installing to a skills directory, just talk to the Agent in natural language. It will route your intent to the right skill automatically.

**Authentication:**

> "Check if I'm logged in to Reddit" / "Log out of Reddit"

**Search & Browse:**

> "Search Reddit for posts about machine learning" / "Show me the top posts on r/Python"

**Submit content:**

> "Submit a text post to r/learnpython with this title and body..."

**Interact:**

> "Upvote this post" / "Comment on this post: Great write-up!" / "Save this post"

**Compound operations:**

> "Analyze the top posts in r/startups this month and summarize the common themes"

### As an MCP server

reddit-skills includes a built-in [Model Context Protocol](https://modelcontextprotocol.io) server, making it compatible with any MCP client (Claude Desktop, Cursor, etc.).

**Start the server (stdio):**

```bash
cd reddit-skills
python scripts/mcp_server.py
```

**Configure in your MCP client** (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "reddit-skills": {
      "command": "python",
      "args": ["scripts/mcp_server.py"],
      "cwd": "/path/to/reddit-skills"
    }
  }
}
```

The server exposes 16 tools: `check_login`, `logout`, `home_feed`, `subreddit_feed`, `search`, `get_post_detail`, `user_profile`, `subreddit_rules`, `post_comment`, `reply_comment`, `upvote`, `downvote`, `save_post`, `submit_text_post`, `submit_link_post`, `submit_image_post`.

**Environment variables:**

| Variable | Default | Description |
|----------|---------|-------------|
| `REDDIT_BRIDGE_URL` | `ws://localhost:9334` | WebSocket URL for the bridge server |

### As a CLI tool

All features can be called directly from the command line, with JSON output for scripting.

```bash
# Check login status
python scripts/cli.py check-login

# Browse a subreddit
python scripts/cli.py subreddit-feed --subreddit python --sort hot

# Search posts
python scripts/cli.py search --query "FastAPI tutorial" --sort top --time month

# Get post details and comments
python scripts/cli.py get-post-detail \
  --post-url "https://www.reddit.com/r/Python/comments/abc123/title/"

# Submit a text post
python scripts/cli.py submit-text \
  --subreddit learnpython \
  --title-file title.txt \
  --body-file body.txt

# Submit a link post
python scripts/cli.py submit-link \
  --subreddit programming \
  --title-file title.txt \
  --url "https://example.com/article"

# Submit an image post
python scripts/cli.py submit-image \
  --subreddit pics \
  --title-file title.txt \
  --images "/abs/path/image.jpg"

# Comment on a post
python scripts/cli.py post-comment \
  --post-url "https://www.reddit.com/r/Python/comments/abc123/title/" \
  --content "Thanks for sharing!"

# Upvote / Downvote / Save
python scripts/cli.py upvote --post-url "https://www.reddit.com/r/..."
python scripts/cli.py downvote --post-url "https://www.reddit.com/r/..."
python scripts/cli.py save-post --post-url "https://www.reddit.com/r/..."

# View user profile
python scripts/cli.py user-profile --username spez
```

> On first run, if Chrome is not open, the CLI will auto-launch it.

## CLI Command Reference

| Subcommand | Description |
|------------|-------------|
| `check-login` | Check login status, return username if logged in |
| `delete-cookies` | Log out (UI-based logout) |
| `home-feed` | Get home feed posts |
| `subreddit-feed` | Get posts from a subreddit (supports sort: hot/new/top/rising) |
| `search` | Search posts (supports sort and time filters) |
| `get-post-detail` | Get full post content and comments |
| `user-profile` | Get user profile and recent posts |
| `post-comment` | Comment on a post |
| `reply-comment` | Reply to a specific comment |
| `upvote` | Upvote a post |
| `downvote` | Downvote a post |
| `save-post` | Save / unsave a post |
| `submit-text` | Submit a text (self) post |
| `submit-link` | Submit a link post |
| `submit-image` | Submit an image post |

Exit codes: `0` success · `1` not logged in · `2` error

## Project Structure

```
reddit-skills/
├── extension/                  # Chrome Extension (MV3)
│   ├── manifest.json
│   └── background.js
├── scripts/                    # Python automation engine
│   ├── reddit/                 # Core automation library
│   │   ├── bridge.py           # Extension bridge client
│   │   ├── selectors.py        # CSS selectors (centralized)
│   │   ├── login.py            # Login check + logout
│   │   ├── feeds.py            # Home feed + subreddit feed
│   │   ├── search.py           # Search + filters
│   │   ├── post_detail.py      # Post detail + comment loading
│   │   ├── user_profile.py     # User profile
│   │   ├── comment.py          # Comment, reply
│   │   ├── vote.py             # Upvote, downvote, save
│   │   ├── publish.py          # Post submission
│   │   ├── types.py            # Data types
│   │   ├── errors.py           # Exception hierarchy
│   │   ├── urls.py             # URL constants
│   │   └── human.py            # Behavior simulation
│   ├── cli.py                  # Unified CLI entry point
│   ├── mcp_server.py           # MCP server wrapper (stdio/HTTP)
│   ├── bridge_server.py        # Local WebSocket bridge
│   └── image_downloader.py     # Image download with local cache
├── skills/                     # AI Agent skill definitions
│   ├── reddit-auth/SKILL.md
│   ├── reddit-publish/SKILL.md
│   ├── reddit-explore/SKILL.md
│   ├── reddit-interact/SKILL.md
│   └── reddit-content-ops/SKILL.md
├── SKILL.md                    # Skill router (routes to sub-skills)
├── CONTRIBUTING.md             # Contributor guide
├── Dockerfile                  # Container build for MCP deployment
├── pyproject.toml
└── README.md
```

## Development

```bash
uv sync                    # Install dependencies
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run pytest              # Run tests
```

## License

MIT
