"""MCP server wrapper for reddit-skills.

Exposes all reddit-skills CLI commands as MCP tools over stdio transport,
enabling any MCP-compatible client to interact with Reddit through the
browser extension bridge.

Usage:
    python scripts/mcp_server.py                     # stdio (default)
    python scripts/mcp_server.py --transport http     # streamable HTTP

Environment:
    REDDIT_BRIDGE_URL  WebSocket URL for the bridge server (default: ws://localhost:9334)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "reddit-skills",
    instructions=(
        "Reddit automation via browser extension bridge. "
        "Search, browse, comment, vote, and publish on Reddit. "
        "Requires the reddit-skills Chrome extension and bridge server running locally."
    ),
)

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
_CLI = os.path.join(_SCRIPTS_DIR, "cli.py")
_BRIDGE_URL = os.environ.get("REDDIT_BRIDGE_URL", "ws://localhost:9334")


def _run(*args: str, timeout: int = 120) -> dict:
    """Execute a cli.py subcommand and return parsed JSON."""
    cmd = [sys.executable, _CLI, "--bridge-url", _BRIDGE_URL, *args]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=_SCRIPTS_DIR,
        timeout=timeout,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "success": False,
            "error": proc.stderr.strip() or proc.stdout.strip() or "No output from CLI",
            "exit_code": proc.returncode,
        }


# ── Authentication ────────────────────────────────────────────────


@mcp.tool()
def check_login() -> dict:
    """Check if the user is currently logged into Reddit via the browser extension."""
    return _run("check-login")


@mcp.tool()
def logout() -> dict:
    """Log out of Reddit by clearing browser cookies."""
    return _run("delete-cookies")


# ── Browsing ──────────────────────────────────────────────────────


@mcp.tool()
def home_feed() -> dict:
    """Get posts from the user's Reddit home feed."""
    return _run("home-feed")


@mcp.tool()
def subreddit_feed(subreddit: str, sort: str = "hot") -> dict:
    """Get posts from a specific subreddit.

    Args:
        subreddit: Subreddit name without the r/ prefix (e.g. "python")
        sort: Sort order — hot, new, top, or rising
    """
    return _run("subreddit-feed", "--subreddit", subreddit, "--sort", sort)


@mcp.tool()
def search(query: str, sort: str = "relevance", time_filter: str = "all") -> dict:
    """Search Reddit for posts matching a query.

    Args:
        query: Search query string
        sort: Sort results by — relevance, hot, top, new, or comments
        time_filter: Time window — hour, day, week, month, year, or all
    """
    return _run("search", "--query", query, "--sort", sort, "--time", time_filter)


@mcp.tool()
def get_post_detail(post_url: str, load_all_comments: bool = False) -> dict:
    """Get full details of a Reddit post including its comments.

    Args:
        post_url: Full Reddit post URL or permalink
        load_all_comments: If true, scroll to load every comment (slower)
    """
    args = ["get-post-detail", "--post-url", post_url]
    if load_all_comments:
        args.append("--load-all-comments")
    return _run(*args)


@mcp.tool()
def user_profile(username: str) -> dict:
    """Get a Reddit user's profile information.

    Args:
        username: Reddit username (without u/ prefix)
    """
    return _run("user-profile", "--username", username)


@mcp.tool()
def subreddit_rules(subreddit: str) -> dict:
    """Get a subreddit's posting rules and available flairs.

    Args:
        subreddit: Subreddit name without the r/ prefix
    """
    return _run("subreddit-rules", "--subreddit", subreddit)


# ── Interaction ───────────────────────────────────────────────────


@mcp.tool()
def post_comment(post_url: str, content: str) -> dict:
    """Post a top-level comment on a Reddit post.

    Args:
        post_url: Full Reddit post URL or permalink
        content: Comment text (Markdown supported)
    """
    return _run("post-comment", "--post-url", post_url, "--content", content)


@mcp.tool()
def reply_comment(post_url: str, content: str, comment_id: str = "") -> dict:
    """Reply to a specific comment on a Reddit post.

    Args:
        post_url: Full Reddit post URL or permalink
        content: Reply text (Markdown supported)
        comment_id: ID of the comment to reply to (from get_post_detail)
    """
    args = ["reply-comment", "--post-url", post_url, "--content", content]
    if comment_id:
        args.extend(["--comment-id", comment_id])
    return _run(*args)


@mcp.tool()
def upvote(post_url: str) -> dict:
    """Upvote a Reddit post.

    Args:
        post_url: Full Reddit post URL or permalink
    """
    return _run("upvote", "--post-url", post_url)


@mcp.tool()
def downvote(post_url: str) -> dict:
    """Downvote a Reddit post.

    Args:
        post_url: Full Reddit post URL or permalink
    """
    return _run("downvote", "--post-url", post_url)


@mcp.tool()
def save_post(post_url: str, unsave: bool = False) -> dict:
    """Save or unsave a Reddit post.

    Args:
        post_url: Full Reddit post URL or permalink
        unsave: If true, removes the post from saved items
    """
    args = ["save-post", "--post-url", post_url]
    if unsave:
        args.append("--unsave")
    return _run(*args)


# ── Publishing ────────────────────────────────────────────────────


@mcp.tool()
def submit_text_post(
    subreddit: str,
    title: str,
    body: str = "",
    flair: str = "",
    nsfw: bool = False,
    spoiler: bool = False,
) -> dict:
    """Submit a text post to a subreddit.

    Args:
        subreddit: Target subreddit without r/ prefix
        title: Post title
        body: Post body text (Markdown supported)
        flair: Flair text (matched by substring against available flairs)
        nsfw: Mark the post as NSFW
        spoiler: Mark the post as a spoiler
    """
    title_path = body_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(title)
            title_path = f.name

        args = ["submit-text", "--subreddit", subreddit, "--title-file", title_path]

        if body:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write(body)
                body_path = f.name
            args.extend(["--body-file", body_path])

        if flair:
            args.extend(["--flair", flair])
        if nsfw:
            args.append("--nsfw")
        if spoiler:
            args.append("--spoiler")

        return _run(*args)
    finally:
        if title_path:
            os.unlink(title_path)
        if body_path:
            os.unlink(body_path)


@mcp.tool()
def submit_link_post(
    subreddit: str,
    title: str,
    url: str,
    flair: str = "",
    nsfw: bool = False,
    spoiler: bool = False,
) -> dict:
    """Submit a link post to a subreddit.

    Args:
        subreddit: Target subreddit without r/ prefix
        title: Post title
        url: The URL to share
        flair: Flair text (matched by substring against available flairs)
        nsfw: Mark the post as NSFW
        spoiler: Mark the post as a spoiler
    """
    title_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(title)
            title_path = f.name

        args = [
            "submit-link", "--subreddit", subreddit,
            "--title-file", title_path, "--url", url,
        ]
        if flair:
            args.extend(["--flair", flair])
        if nsfw:
            args.append("--nsfw")
        if spoiler:
            args.append("--spoiler")

        return _run(*args)
    finally:
        if title_path:
            os.unlink(title_path)


@mcp.tool()
def submit_image_post(
    subreddit: str,
    title: str,
    images: list[str],
    flair: str = "",
    nsfw: bool = False,
    spoiler: bool = False,
) -> dict:
    """Submit an image post to a subreddit.

    Args:
        subreddit: Target subreddit without r/ prefix
        title: Post title
        images: List of local image file paths or URLs
        flair: Flair text (matched by substring against available flairs)
        nsfw: Mark the post as NSFW
        spoiler: Mark the post as a spoiler
    """
    title_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as f:
            f.write(title)
            title_path = f.name

        args = [
            "submit-image", "--subreddit", subreddit,
            "--title-file", title_path, "--images", *images,
        ]
        if flair:
            args.extend(["--flair", flair])
        if nsfw:
            args.append("--nsfw")
        if spoiler:
            args.append("--spoiler")

        return _run(*args)
    finally:
        if title_path:
            os.unlink(title_path)


if __name__ == "__main__":
    mcp.run(transport="stdio")
