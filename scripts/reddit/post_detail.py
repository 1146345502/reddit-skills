"""Reddit post detail and comments."""

from __future__ import annotations

import json
import logging
import time

from .bridge import BridgePage
from .errors import NoPostDetailError, PostNotAccessibleError
from .human import INACCESSIBLE_KEYWORDS, sleep_random
from .selectors import COMMENT_CONTAINER, POST_DETAIL_TITLE
from .types import Author, Comment, Post, PostDetail
from .urls import make_post_detail_url

logger = logging.getLogger(__name__)

_EXTRACT_POST_DETAIL_JS = """
(() => {
    const result = {};
    const sp = document.querySelector('shreddit-post');
    if (sp) {
        result.title = sp.getAttribute('post-title') || '';
        result.subreddit = sp.getAttribute('subreddit-name') || '';
        result.authorName = sp.getAttribute('author') || '';
        result.permalink = sp.getAttribute('permalink') || window.location.pathname;
        result.score = parseInt(sp.getAttribute('score') || '0', 10) || 0;
        result.commentCount = parseInt(sp.getAttribute('comment-count') || '0', 10) || 0;
        result.postType = sp.getAttribute('post-type') || '';
    } else {
        result.title = '';
        result.permalink = window.location.pathname;
    }

    const contentEl = document.querySelector(
        '[slot="text-body"], ' +
        '[data-click-id="text"], ' +
        'div[data-testid="post-content"], ' +
        '.expando .usertext-body'
    );
    result.selftext = contentEl ? contentEl.innerText.trim() : '';

    return JSON.stringify(result);
})()
"""

_EXTRACT_COMMENTS_JS = """
(() => {
    const comments = [];
    document.querySelectorAll('shreddit-comment').forEach(el => {
        try {
            const author = el.getAttribute('author') || '';
            const score = parseInt(el.getAttribute('score') || '0', 10) || 0;
            const commentId = el.getAttribute('thingid') || el.id || '';
            const depth = parseInt(el.getAttribute('depth') || '0', 10) || 0;

            const bodyEl = el.querySelector('p, div[id*="richtext"], [slot="comment"]');
            const body = bodyEl ? bodyEl.innerText.trim() : '';

            if (body) {
                comments.push({
                    id: commentId,
                    author: { name: author },
                    body: body,
                    score: score,
                    depth: depth,
                });
            }
        } catch (e) {}
    });
    return JSON.stringify(comments);
})()
"""


def get_post_detail(
    page: BridgePage,
    post_url: str,
    load_all_comments: bool = False,
) -> PostDetail:
    """Get full post content and comments."""
    url = make_post_detail_url(post_url)
    page.navigate(url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    _check_accessibility(page)
    _wait_for_content(page)

    raw = page.evaluate(_EXTRACT_POST_DETAIL_JS)
    if not raw:
        raise NoPostDetailError()

    data = json.loads(raw)

    post = Post(
        title=data.get("title", ""),
        subreddit=data.get("subreddit", ""),
        permalink=data.get("permalink", ""),
        author=Author(name=data.get("authorName", "")),
    )

    if load_all_comments:
        _scroll_to_load_comments(page)

    raw_comments = page.evaluate(_EXTRACT_COMMENTS_JS)
    comments = []
    if raw_comments:
        comments_data = json.loads(raw_comments)
        comments = [Comment.from_dict(c) for c in comments_data]

    return PostDetail(
        post=post,
        selftext=data.get("selftext", ""),
        comments=comments,
    )


def _check_accessibility(page: BridgePage) -> None:
    """Check if the post page is accessible."""
    body_text = page.evaluate("document.body?.innerText?.substring(0, 500) || ''") or ""
    body_lower = body_text.lower()
    for keyword in INACCESSIBLE_KEYWORDS:
        if keyword in body_lower:
            raise PostNotAccessibleError(keyword)


def _wait_for_content(page: BridgePage, timeout: float = 15.0) -> None:
    """Wait for post content to load."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if page.has_element(POST_DETAIL_TITLE):
            return
        time.sleep(0.5)
    logger.warning("Timeout waiting for post content")


def _scroll_to_load_comments(page: BridgePage, max_scrolls: int = 20) -> None:
    """Scroll down to load more comments."""
    for _ in range(max_scrolls):
        prev_count = page.get_elements_count(COMMENT_CONTAINER)
        page.scroll_by(0, 600)
        sleep_random(800, 1500)
        new_count = page.get_elements_count(COMMENT_CONTAINER)
        if new_count == prev_count:
            break
