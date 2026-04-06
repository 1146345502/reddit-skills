"""Reddit user profile."""

from __future__ import annotations

import json
import logging
import time

from .bridge import BridgePage
from .human import sleep_random
from .types import Post, UserProfile
from .urls import make_user_profile_url

logger = logging.getLogger(__name__)

_EXTRACT_PROFILE_JS = """
(() => {
    const result = {};
    result.username = window.location.pathname.match(/\\/user\\/([^/]+)/)?.[1] || '';

    const nameEl = document.querySelector('h1, [data-testid="profile-username"]');
    result.displayName = nameEl ? nameEl.textContent.trim() : result.username;

    const karmaEl = document.querySelector('[data-testid="karma"], span[class*="karma"]');
    result.karma = karmaEl ? parseInt(karmaEl.textContent.replace(/[^0-9]/g, ''), 10) || 0 : 0;

    const descEl = document.querySelector(
        '[data-testid="profile-description"], ' +
        'div[class*="description"]'
    );
    result.description = descEl ? descEl.textContent.trim() : '';

    return JSON.stringify(result);
})()
"""

_EXTRACT_USER_POSTS_JS = """
(() => {
    const posts = [];
    document.querySelectorAll('shreddit-post').forEach(el => {
        try {
            const title = el.getAttribute('post-title') || '';
            if (!title) return;
            posts.push({
                id: el.id || '',
                title: title,
                subreddit: el.getAttribute('subreddit-name') || '',
                permalink: el.getAttribute('permalink') || '',
                postType: el.getAttribute('post-type') || '',
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

_EXTRACT_USER_COMMENTS_JS = """
(() => {
    const seen = new Set();
    const comments = [];
    document.querySelectorAll('.md').forEach(md => {
        const text = md.innerText.trim();
        if (!text || seen.has(text)) return;
        seen.add(text);

        let parent = md.parentElement;
        for (let i = 0; i < 10 && parent; i++) { parent = parent.parentElement; }
        const postLink = (parent || document)
            .querySelector('a[href*="/comments/"]');
        const subLink = (parent || document)
            .querySelector('a[href*="/r/"]');
        let subreddit = '';
        if (subLink) {
            const m = (subLink.getAttribute('href') || '').match(/\\/r\\/([^/]+)/);
            if (m) subreddit = m[1];
        }

        comments.push({
            body: text.substring(0, 500),
            subreddit: subreddit,
            postLink: postLink ? postLink.getAttribute('href').substring(0, 120) : '',
        });
    });
    return JSON.stringify(comments);
})()
"""


def get_user_profile(page: BridgePage, username: str) -> dict:
    """Get user profile information, recent posts, and comments."""
    base_url = make_user_profile_url(username)
    page.navigate(base_url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    raw = page.evaluate(_EXTRACT_PROFILE_JS)
    profile = UserProfile()
    if raw:
        data = json.loads(raw)
        profile = UserProfile(
            username=data.get("username", username),
            display_name=data.get("displayName", ""),
            karma=data.get("karma", 0),
            description=data.get("description", ""),
        )

    # Navigate to submitted (posts) tab
    posts_url = f"{base_url.rstrip('/')}/submitted/"
    page.navigate(posts_url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    _scroll_to_load(page, "shreddit-post")

    raw_posts = page.evaluate(_EXTRACT_USER_POSTS_JS)
    posts = []
    if raw_posts:
        posts_data = json.loads(raw_posts)
        posts = [Post.from_dict(p) for p in posts_data]

    # Navigate to comments tab
    comments_url = f"{base_url.rstrip('/')}/comments/"
    page.navigate(comments_url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    raw_comments = page.evaluate(_EXTRACT_USER_COMMENTS_JS)
    comments = []
    if raw_comments:
        comments = json.loads(raw_comments)

    return {
        "profile": profile.to_dict(),
        "posts": [p.to_dict() for p in posts],
        "comments": comments,
    }


def _scroll_to_load(page: BridgePage, selector: str, max_scrolls: int = 5) -> None:
    """Scroll to load more items on the page."""
    for _ in range(max_scrolls):
        prev = page.get_elements_count(selector)
        page.scroll_by(0, 800)
        time.sleep(1.2)
        if page.get_elements_count(selector) == prev:
            break
