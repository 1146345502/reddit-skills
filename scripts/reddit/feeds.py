"""Reddit home feed and subreddit feed."""

from __future__ import annotations

import json
import logging
import time

from .bridge import BridgePage
from .errors import NoPostsError
from .human import sleep_random
from .selectors import POST_CONTAINER
from .types import Post
from .urls import HOME_URL, make_subreddit_url

logger = logging.getLogger(__name__)

_EXTRACT_POSTS_JS = """
(() => {
    const posts = [];
    document.querySelectorAll('shreddit-post').forEach(el => {
        try {
            const title = el.getAttribute('post-title') || '';
            if (!title) return;
            const bodyEl = el.querySelector('[slot="text-body"]');
            const selftext = bodyEl ? bodyEl.innerText.trim() : '';
            posts.push({
                id: el.id || '',
                title: title,
                subreddit: el.getAttribute('subreddit-name') || '',
                author: { name: el.getAttribute('author') || '' },
                permalink: el.getAttribute('permalink') || '',
                postType: el.getAttribute('post-type') || '',
                selftext: selftext,
                stats: {
                    score: parseInt(el.getAttribute('score') || '0', 10) || 0,
                    numComments: parseInt(el.getAttribute('comment-count') || '0', 10) || 0,
                },
            });
        } catch (e) {}
    });
    return JSON.stringify(posts);
})()
"""


def home_feed(page: BridgePage) -> list[Post]:
    """Get posts from the home feed."""
    page.navigate(HOME_URL)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    return _extract_posts(page)


def subreddit_feed(
    page: BridgePage,
    subreddit: str,
    sort: str = "hot",
) -> list[Post]:
    """Get posts from a specific subreddit."""
    url = make_subreddit_url(subreddit, sort)
    page.navigate(url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    return _extract_posts(page)


def _extract_posts(page: BridgePage) -> list[Post]:
    """Extract post data from the current page."""
    _wait_for_posts(page)

    result = page.evaluate(_EXTRACT_POSTS_JS)
    if not result:
        raise NoPostsError()

    posts_data = json.loads(result)
    if not posts_data:
        raise NoPostsError()

    return [Post.from_dict(p) for p in posts_data]


def _wait_for_posts(page: BridgePage, timeout: float = 15.0) -> None:
    """Wait for posts to appear on the page."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = page.get_elements_count(POST_CONTAINER)
        if count > 0:
            return
        time.sleep(0.5)
    logger.warning("Timeout waiting for posts to load")
