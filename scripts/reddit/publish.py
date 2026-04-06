"""Reddit post submission."""

from __future__ import annotations

import json
import logging
import time

from .bridge import BridgePage
from .errors import PublishError, TitleTooLongError
from .human import sleep_random
from .selectors import FILE_INPUT, SUBMIT_URL_INPUT
from .types import SubmitImageContent, SubmitLinkContent, SubmitTextContent
from .urls import make_submit_url

logger = logging.getLogger(__name__)

REDDIT_TITLE_MAX_LENGTH = 300


def submit_text_post(page: BridgePage, content: SubmitTextContent) -> None:
    """Submit a text post to a subreddit."""
    _validate_title(content.title)
    _navigate_to_submit(page, content.subreddit)

    _fill_title_shadow(page, content.title)

    if content.body:
        _fill_body_composer(page, content.body)

    _click_submit_shadow(page)
    logger.info("Text post submitted to r/%s", content.subreddit)


def submit_link_post(page: BridgePage, content: SubmitLinkContent) -> None:
    """Submit a link post to a subreddit."""
    _validate_title(content.title)
    _navigate_to_submit(page, content.subreddit, post_type="LINK")

    _fill_title_shadow(page, content.title)

    page.wait_for_element(SUBMIT_URL_INPUT, timeout=10.0)
    page.click_element(SUBMIT_URL_INPUT)
    sleep_random(200, 400)
    page.input_text(SUBMIT_URL_INPUT, content.url)
    sleep_random(300, 500)

    _click_submit_shadow(page)
    logger.info("Link post submitted to r/%s", content.subreddit)


def submit_image_post(page: BridgePage, content: SubmitImageContent) -> None:
    """Submit an image post to a subreddit."""
    _validate_title(content.title)
    _navigate_to_submit(page, content.subreddit, post_type="IMAGE")

    _fill_title_shadow(page, content.title)

    page.wait_for_element(FILE_INPUT, timeout=10.0)
    page.set_file_input(FILE_INPUT, content.image_paths)
    sleep_random(2000, 4000)

    _click_submit_shadow(page)
    logger.info("Image post submitted to r/%s", content.subreddit)


# ─── Internal helpers ────────────────────────────────────────────


def _validate_title(title: str) -> None:
    if len(title) > REDDIT_TITLE_MAX_LENGTH:
        raise TitleTooLongError(len(title), REDDIT_TITLE_MAX_LENGTH)


def _navigate_to_submit(
    page: BridgePage, subreddit: str, post_type: str = "TEXT"
) -> None:
    url = make_submit_url(subreddit)
    page.navigate(f"{url}?type={post_type}")
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)


def _fill_title_shadow(page: BridgePage, title: str) -> None:
    """Fill the title via the shadow DOM textarea inside faceplate-textarea-input."""
    title_js = json.dumps(title)
    result = page.evaluate(
        f"""
        (() => {{
            const fti = document.querySelector('faceplate-textarea-input[name="title"]');
            if (!fti || !fti.shadowRoot)
                return JSON.stringify({{ok: false, error: "no title element"}});
            const ta = fti.shadowRoot.querySelector('textarea');
            if (!ta) return JSON.stringify({{ok: false, error: "no textarea in shadow"}});
            ta.focus();
            ta.value = {title_js};
            ta.dispatchEvent(new Event('input', {{bubbles: true}}));
            ta.dispatchEvent(new Event('change', {{bubbles: true}}));
            return JSON.stringify({{ok: true}});
        }})()
    """
    )

    data = json.loads(result or "{}")
    if not data.get("ok"):
        raise PublishError(f"Failed to fill title: {data.get('error', 'unknown')}")
    sleep_random(300, 500)


def _fill_body_composer(page: BridgePage, body: str) -> None:
    """Fill the body via contenteditable inside shreddit-composer."""
    body_js = json.dumps(body)
    result = page.evaluate(
        f"""
        (async () => {{
            const composer = document.querySelector('shreddit-composer[name="body"]');
            if (!composer) return JSON.stringify({{ok: false, error: "no body composer"}});
            const ce = composer.querySelector('div[contenteditable="true"]');
            if (!ce) return JSON.stringify({{ok: false, error: "no contenteditable"}});

            ce.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true}}));
            ce.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true}}));
            ce.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
            ce.dispatchEvent(new FocusEvent('focus', {{bubbles: true}}));
            ce.focus();
            await new Promise(r => setTimeout(r, 300));

            const text = {body_js};
            const chunkSize = 50;
            for (let i = 0; i < text.length; i += chunkSize) {{
                document.execCommand('insertText', false, text.slice(i, i + chunkSize));
                await new Promise(r => setTimeout(r, 30));
            }}
            return JSON.stringify({{ok: true}});
        }})()
    """
    )

    data = json.loads(result or "{}")
    if not data.get("ok"):
        logger.warning("Could not fill body: %s", data.get("error", "unknown"))
    sleep_random(300, 500)


def _click_submit_shadow(page: BridgePage) -> None:
    """Click the Post button inside r-post-form-submit-button shadow DOM."""
    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        result = page.evaluate(
            """
            (() => {
                const host = document.querySelector('r-post-form-submit-button');
                if (!host || !host.shadowRoot) return JSON.stringify({found: false});
                const btn = [...host.shadowRoot.querySelectorAll('button')]
                    .find(b => b.textContent.trim() === 'Post');
                if (!btn) return JSON.stringify({found: false});
                if (btn.disabled) return JSON.stringify({found: true, disabled: true});
                btn.click();
                return JSON.stringify({found: true, clicked: true});
            })()
        """
        )

        data = json.loads(result or "{}")
        if data.get("clicked"):
            sleep_random(2000, 3000)
            return
        time.sleep(0.5)
    raise PublishError("Post button not found or disabled")
