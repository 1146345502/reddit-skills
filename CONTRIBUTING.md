# Contributing

Thanks for your interest in contributing to reddit-skills!

## Setup

```bash
git clone https://github.com/1146345502/reddit-skills.git
cd reddit-skills
uv sync
```

Install the Chrome extension for testing (see [README](README.md#step-2-install-the-browser-extension)).

## Development

```bash
uv run ruff check .    # Lint
uv run ruff format .   # Format
uv run pytest          # Test
```

## Code Standards

- Python 3.11+, type hints with `from __future__ import annotations`
- Line length max 100 characters (enforced by ruff)
- Exceptions inherit from `RedditError` in `scripts/reddit/errors.py`
- CLI output is JSON with `ensure_ascii=False`
- Exit codes: `0` success, `1` not logged in, `2` error

## Architecture

```
scripts/reddit/   Python automation library (one file per feature)
scripts/cli.py    Unified CLI, JSON output
extension/        Chrome MV3 extension (WebSocket bridge to Python CLI)
skills/           SKILL.md definitions for AI agent routing
```

The browser extension connects to a local WebSocket server (`bridge_server.py`) which relays commands between the CLI and Chrome. All Reddit interaction happens in the user's real browser session.

## Submitting Changes

1. Fork the repo and create a branch from `main`
2. Make your changes, ensuring `ruff check .` passes with no errors
3. Open a pull request with a clear description of what changed and why

## Updating Selectors

Reddit's frontend changes frequently. If a feature breaks, the most likely cause is a stale CSS selector in `scripts/reddit/selectors.py` or an inline selector in the JS evaluation strings. To debug:

1. Run the failing CLI command
2. Use `page.evaluate(...)` to inspect the current DOM structure
3. Update the selector to match the new markup
