"""Reddit voting (upvote/downvote) and saving."""

from __future__ import annotations

import logging

from .bridge import BridgePage
from .human import sleep_random
from .types import ActionResult
from .urls import make_post_detail_url

logger = logging.getLogger(__name__)

_CLICK_VOTE_JS = """
(() => {{
    const sp = document.querySelector('shreddit-post');
    if (!sp || !sp.shadowRoot) return false;
    const btn = [...sp.shadowRoot.querySelectorAll('button')]
        .find(b => b.textContent.trim() === '{label}');
    if (btn) {{ btn.click(); return true; }}
    return false;
}})()
"""


def _navigate_to_post(page: BridgePage, post_url: str) -> None:
    url = make_post_detail_url(post_url)
    page.navigate(url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)


def upvote_post(page: BridgePage, post_url: str) -> ActionResult:
    """Upvote a Reddit post."""
    _navigate_to_post(page, post_url)
    try:
        clicked = page.evaluate(_CLICK_VOTE_JS.format(label="Upvote"))
        sleep_random(300, 600)
        if clicked:
            logger.info("Post upvoted")
            return ActionResult(post_id=post_url, success=True, message="Upvoted")
        return ActionResult(
            post_id=post_url, success=False, message="Upvote button not found"
        )
    except Exception as e:
        logger.error("Upvote failed: %s", e)
        return ActionResult(post_id=post_url, success=False, message=str(e))


def downvote_post(page: BridgePage, post_url: str) -> ActionResult:
    """Downvote a Reddit post."""
    _navigate_to_post(page, post_url)
    try:
        clicked = page.evaluate(_CLICK_VOTE_JS.format(label="Downvote"))
        sleep_random(300, 600)
        if clicked:
            logger.info("Post downvoted")
            return ActionResult(post_id=post_url, success=True, message="Downvoted")
        return ActionResult(
            post_id=post_url, success=False, message="Downvote button not found"
        )
    except Exception as e:
        logger.error("Downvote failed: %s", e)
        return ActionResult(post_id=post_url, success=False, message=str(e))


def save_post(page: BridgePage, post_url: str, unsave: bool = False) -> ActionResult:
    """Save or unsave a Reddit post via the overflow menu."""
    _navigate_to_post(page, post_url)
    try:
        saved = page.evaluate(
            """
            (() => {
                const sp = document.querySelector('shreddit-post');
                if (!sp) return false;

                // Try overflow / "more options" menu in shadow root
                const shadow = sp.shadowRoot;
                if (shadow) {
                    const moreBtn = shadow.querySelector(
                        'shreddit-post-overflow-menu, button[aria-label*="more"]'
                    );
                    if (moreBtn) { moreBtn.click(); return 'menu_opened'; }
                }

                // Fallback: look for Save button in light DOM
                const saveBtn = document.querySelector(
                    'button[aria-label*="Save"], button[data-click-id="save"]'
                );
                if (saveBtn) { saveBtn.click(); return true; }
                return false;
            })()
        """
        )
        sleep_random(300, 600)

        if saved == "menu_opened":
            sleep_random(400, 700)
            page.evaluate(
                """
                (() => {
                    const items = document.querySelectorAll(
                        '[role="menuitem"], [role="option"], li'
                    );
                    for (const item of items) {
                        if (item.textContent.trim().toLowerCase().includes('save')) {
                            item.click();
                            return true;
                        }
                    }
                    return false;
                })()
            """
            )
            sleep_random(300, 500)

        action = "Unsaved" if unsave else "Saved"
        logger.info("Post %s", action.lower())
        return ActionResult(post_id=post_url, success=True, message=action)
    except Exception as e:
        logger.error("Save/unsave failed: %s", e)
        return ActionResult(post_id=post_url, success=False, message=str(e))
