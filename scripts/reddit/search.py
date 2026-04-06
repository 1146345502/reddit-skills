"""Reddit search."""

from __future__ import annotations

import json
import logging
import time

from .bridge import BridgePage
from .errors import NoPostsError
from .human import sleep_random
from .selectors import SEARCH_RESULT
from .types import Post, SearchFilter
from .urls import make_search_url

logger = logging.getLogger(__name__)

_EXTRACT_SEARCH_JS = """
(() => {
    const posts = [];
    document.querySelectorAll('[data-testid="search-post-unit"]').forEach(el => {
        try {
            const titleEl = el.querySelector('a[data-testid="post-title-text"]');
            const title = titleEl ? titleEl.textContent.trim() : '';
            if (!title) return;
            const permalink = titleEl ? titleEl.getAttribute('href') || '' : '';

            const subEl = el.querySelector('a[href*="/r/"]');
            let subreddit = '';
            if (subEl) {
                const m = (subEl.getAttribute('href') || '').match(/\\/r\\/([^/]+)/);
                if (m) subreddit = m[1];
            }

            const statsEl = el.querySelector('[data-testid="search-counter-row"]');
            const statsText = statsEl ? statsEl.textContent : '';
            let score = 0;
            let numComments = 0;
            const voteMatch = statsText.match(/([\\.\\d]+)K?\\s*vote/i);
            if (voteMatch) {
                score = parseFloat(voteMatch[1]);
                if (statsText.includes('K vote')) score *= 1000;
                score = Math.round(score);
            }
            const commentMatch = statsText.match(/([\\.\\d]+)K?\\s*comment/i);
            if (commentMatch) {
                numComments = parseFloat(commentMatch[1]);
                if (statsText.includes('K comment')) numComments *= 1000;
                numComments = Math.round(numComments);
            }

            const postId = (permalink.match(/comments\\/([^/]+)/) || [])[1] || '';

            posts.push({
                id: postId,
                title: title,
                subreddit: subreddit,
                author: { name: '' },
                permalink: permalink,
                stats: { score: score, numComments: numComments },
            });
        } catch (e) {}
    });
    return JSON.stringify(posts);
})()
"""


def search_posts(
    page: BridgePage,
    query: str,
    filter_option: SearchFilter | None = None,
) -> list[Post]:
    """Search Reddit posts."""
    sort = "relevance"
    time_filter = "all"
    if filter_option:
        sort = filter_option.sort or "relevance"
        time_filter = filter_option.time or "all"

    url = make_search_url(query, sort=sort, time=time_filter)
    page.navigate(url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    _wait_for_results(page)

    result = page.evaluate(_EXTRACT_SEARCH_JS)
    if not result:
        raise NoPostsError()

    posts_data = json.loads(result)
    return [Post.from_dict(p) for p in posts_data]


def _wait_for_results(page: BridgePage, timeout: float = 15.0) -> None:
    """Wait for search results to appear."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        count = page.get_elements_count(SEARCH_RESULT)
        if count > 0:
            return
        time.sleep(0.5)
    logger.warning("Timeout waiting for search results")
