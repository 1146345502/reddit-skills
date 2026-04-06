"""Reddit commenting and replying."""

from __future__ import annotations

import json
import logging
import time

from .bridge import BridgePage
from .errors import ElementNotFoundError
from .human import sleep_random
from .selectors import COMMENT_SUBMIT
from .urls import make_post_detail_url

logger = logging.getLogger(__name__)

_FILL_COMMENT_JS = """
(async () => {{
    const ce = document.querySelector('shreddit-composer div[contenteditable="true"]');
    if (!ce) return JSON.stringify({{ok: false, error: "no contenteditable"}});

    const rect = ce.getBoundingClientRect();
    const x = rect.left + rect.width / 2;
    const y = rect.top + rect.height / 2;
    ce.dispatchEvent(new MouseEvent("mousedown", {{clientX: x, clientY: y, bubbles: true}}));
    ce.dispatchEvent(new MouseEvent("mouseup",   {{clientX: x, clientY: y, bubbles: true}}));
    ce.dispatchEvent(new MouseEvent("click",      {{clientX: x, clientY: y, bubbles: true}}));
    ce.dispatchEvent(new FocusEvent("focus",   {{bubbles: true}}));
    ce.dispatchEvent(new FocusEvent("focusin", {{bubbles: true}}));
    await new Promise(r => setTimeout(r, 300));

    document.execCommand("selectAll", false, null);
    document.execCommand("delete", false, null);
    await new Promise(r => setTimeout(r, 100));

    const text = {text_json};
    const lines = text.split("\\n");
    for (let i = 0; i < lines.length; i++) {{
        if (lines[i]) document.execCommand("insertText", false, lines[i]);
        if (i < lines.length - 1) {{
            document.execCommand("insertParagraph", false, null);
            await new Promise(r => setTimeout(r, 30));
        }}
    }}
    await new Promise(r => setTimeout(r, 200));

    return JSON.stringify({{ok: true, content: ce.innerText.trim().substring(0, 100)}});
}})()
"""


def post_comment(page: BridgePage, post_url: str, content: str) -> None:
    """Post a top-level comment on a Reddit post."""
    url = make_post_detail_url(post_url)
    page.navigate(url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    _fill_comment(page, content)
    _submit_comment(page)

    logger.info("Comment posted successfully")


def reply_comment(
    page: BridgePage,
    post_url: str,
    content: str,
    comment_id: str = "",
) -> None:
    """Reply to a specific comment."""
    url = make_post_detail_url(post_url)
    page.navigate(url)
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    if comment_id:
        _click_reply_button(page, comment_id)

    _fill_comment(page, content)
    _submit_comment(page)

    logger.info("Reply posted successfully")


def _click_reply_button(page: BridgePage, comment_id: str) -> None:
    """Open the reply box for a specific comment."""
    clicked = page.evaluate(
        f"""
        (() => {{
            const comment = document.querySelector(
                '[thingid="{comment_id}"], #{comment_id}'
            );
            if (!comment) return false;
            const shadow = comment.shadowRoot;
            if (shadow) {{
                const btn = [...shadow.querySelectorAll('button')]
                    .find(b => b.textContent.trim().toLowerCase().includes('reply'));
                if (btn) {{ btn.click(); return true; }}
            }}
            const btn = comment.querySelector(
                'button[aria-label*="Reply"], button[data-click-id="reply"]'
            );
            if (btn) {{ btn.click(); return true; }}
            return false;
        }})()
    """
    )
    if clicked:
        sleep_random(500, 800)
    else:
        logger.warning("Could not find reply button for comment %s", comment_id)


def _fill_comment(page: BridgePage, content: str) -> None:
    """Focus the comment input and insert text via execCommand."""
    page.wait_for_element('shreddit-composer div[contenteditable="true"]', timeout=10.0)

    text_json = json.dumps(content, ensure_ascii=False)
    raw = page.evaluate(_FILL_COMMENT_JS.format(text_json=text_json))
    if raw:
        result = json.loads(raw) if isinstance(raw, str) else raw
        if not result.get("ok"):
            raise ElementNotFoundError(result.get("error", "comment input"))
    sleep_random(300, 500)


def _submit_comment(page: BridgePage) -> None:
    """Click the comment submit button."""
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if page.has_element(COMMENT_SUBMIT):
            page.click_element(COMMENT_SUBMIT)
            sleep_random(1000, 2000)
            return
        time.sleep(0.3)
    raise ElementNotFoundError("comment submit button")
