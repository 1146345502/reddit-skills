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


def get_subreddit_rules(page: BridgePage, subreddit: str) -> dict:
    """Extract subreddit rules, available flairs, and posting requirements."""
    page.navigate(f"https://www.reddit.com/r/{subreddit}/")
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(500, 1000)

    result = page.evaluate(
        """
        (() => {
            const rules = [];
            const ruleEls = document.querySelectorAll(
                '[id*="rule"], .rule-description, [class*="rule"]'
            );
            ruleEls.forEach(el => {
                const t = el.textContent.trim();
                if (t.length > 5 && t.length < 300) rules.push(t);
            });

            const flairBadges = new Set();
            document.querySelectorAll(
                'flair-badge, [slot="flair"], [class*="flair"]'
            ).forEach(f => {
                const t = f.textContent.trim();
                if (t && t.length < 50) flairBadges.add(t);
            });

            const header = document.querySelector('shreddit-subreddit-header');
            let memberInfo = '';
            if (header) memberInfo = header.textContent.trim().slice(0, 300);

            return JSON.stringify({
                rules: [...new Set(rules)].slice(0, 15),
                flairs: [...flairBadges],
                memberInfo
            });
        })()
    """
    )
    return json.loads(result or "{}")


def get_submit_flairs(page: BridgePage, subreddit: str) -> list[str]:
    """Get available post flairs from the submit page flair picker."""
    page.navigate(f"https://www.reddit.com/r/{subreddit}/submit?type=TEXT")
    page.wait_for_load()
    page.wait_dom_stable()
    sleep_random(1000, 2000)

    result = page.evaluate(
        """
        (async () => {
            const modal = document.querySelector('r-post-flairs-modal');
            if (!modal || !modal.shadowRoot)
                return JSON.stringify({flairs: [], error: 'no flair picker'});

            const btn = modal.shadowRoot.querySelector('button');
            if (btn) { btn.click(); await new Promise(r => setTimeout(r, 1500)); }

            const radios = [...modal.shadowRoot.querySelectorAll(
                'faceplate-radio-input'
            )];
            const flairs = radios
                .map(r => r.textContent.trim())
                .filter(t => t && t !== 'No flair');

            const cancelBtn = [...modal.shadowRoot.querySelectorAll('button')]
                .find(b => b.textContent.trim() === 'Cancel');
            if (cancelBtn) cancelBtn.click();

            return JSON.stringify({flairs});
        })()
    """
    )
    data = json.loads(result or "{}")
    return data.get("flairs", [])


def submit_text_post(page: BridgePage, content: SubmitTextContent) -> None:
    """Submit a text post to a subreddit."""
    _validate_title(content.title)
    _navigate_to_submit(page, content.subreddit)

    _fill_title_shadow(page, content.title)
    _select_flair_if_provided(page, content.flair_id)

    if content.body:
        _fill_body_composer(page, content.body)

    _clear_beforeunload(page)
    _click_submit_shadow(page)
    _handle_rules_dialog(page)
    _clear_beforeunload(page)
    logger.info("Text post submitted to r/%s", content.subreddit)


def submit_link_post(page: BridgePage, content: SubmitLinkContent) -> None:
    """Submit a link post to a subreddit."""
    _validate_title(content.title)
    _navigate_to_submit(page, content.subreddit, post_type="LINK")

    _fill_title_shadow(page, content.title)
    _select_flair_if_provided(page, content.flair_id)

    page.wait_for_element(SUBMIT_URL_INPUT, timeout=10.0)
    page.click_element(SUBMIT_URL_INPUT)
    sleep_random(200, 400)
    page.input_text(SUBMIT_URL_INPUT, content.url)
    sleep_random(300, 500)

    _clear_beforeunload(page)
    _click_submit_shadow(page)
    _handle_rules_dialog(page)
    _clear_beforeunload(page)
    logger.info("Link post submitted to r/%s", content.subreddit)


def submit_image_post(page: BridgePage, content: SubmitImageContent) -> None:
    """Submit an image post to a subreddit."""
    _validate_title(content.title)
    _navigate_to_submit(page, content.subreddit, post_type="IMAGE")

    _fill_title_shadow(page, content.title)
    _select_flair_if_provided(page, content.flair_id)

    page.wait_for_element(FILE_INPUT, timeout=10.0)
    page.set_file_input(FILE_INPUT, content.image_paths)
    sleep_random(2000, 4000)

    _clear_beforeunload(page)
    _click_submit_shadow(page)
    _handle_rules_dialog(page)
    _clear_beforeunload(page)
    logger.info("Image post submitted to r/%s", content.subreddit)


# ─── Internal helpers ────────────────────────────────────────────


def _clear_beforeunload(page: BridgePage) -> None:
    """Best-effort JS-side neutralization of beforeunload handlers.

    Primary protection is at the extension level (CDP dialog auto-accept).
    This is defense-in-depth for edge cases.
    """
    page.evaluate(
        """
        (() => {
            window.onbeforeunload = null;
            try {
                Object.defineProperty(window, 'onbeforeunload', {
                    configurable: true, set() {}, get() { return null; }
                });
            } catch(e) {}
            return 'cleared';
        })()
    """
    )


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


def _select_flair_if_provided(page: BridgePage, flair_text: str) -> None:
    """Select a post flair via the shadow DOM flair picker.

    Runs the full open-select-add sequence in a single evaluate call so
    the debugger session stays attached throughout.
    """
    if not flair_text:
        return

    flair_js = json.dumps(flair_text)
    result = page.evaluate(
        f"""
        (async () => {{
            const modal = document.querySelector('r-post-flairs-modal');
            if (!modal || !modal.shadowRoot)
                return JSON.stringify({{ok: false, error: 'no flair picker'}});

            const trigger = modal.shadowRoot.querySelector('button');
            if (!trigger)
                return JSON.stringify({{ok: false, error: 'no trigger btn'}});
            trigger.click();
            await new Promise(r => setTimeout(r, 2000));

            const target = {flair_js}.toLowerCase();
            const radios = [...modal.shadowRoot.querySelectorAll(
                'faceplate-radio-input'
            )];
            const match = radios.find(
                r => r.textContent.trim().toLowerCase().includes(target)
            );
            if (!match) {{
                const cancel = [...modal.shadowRoot.querySelectorAll('button')]
                    .find(b => b.textContent.trim() === 'Cancel');
                if (cancel) cancel.click();
                return JSON.stringify({{ok: false, error: 'flair not found',
                    available: radios.map(r => r.textContent.trim())}});
            }}

            match.scrollIntoView({{block: 'center'}});
            await new Promise(r => setTimeout(r, 200));
            if (match.shadowRoot) {{
                const inp = match.shadowRoot.querySelector(
                    'input[type="radio"]');
                if (inp) {{
                    inp.checked = true;
                    inp.dispatchEvent(
                        new Event('input', {{bubbles: true}}));
                    inp.dispatchEvent(
                        new Event('change', {{bubbles: true}}));
                    inp.click();
                }}
            }}
            match.click();
            await new Promise(r => setTimeout(r, 500));

            const addBtn = [...modal.shadowRoot.querySelectorAll('button')]
                .find(b => b.textContent.trim() === 'Add');
            if (!addBtn)
                return JSON.stringify({{ok: false, error: 'no Add btn'}});

            addBtn.dispatchEvent(new MouseEvent('click',
                {{bubbles: true, cancelable: true}}));
            await new Promise(r => setTimeout(r, 1000));

            const stillOpen = modal.shadowRoot.querySelector(
                'dialog[open], [open]');
            if (stillOpen) {{
                addBtn.focus();
                addBtn.click();
                await new Promise(r => setTimeout(r, 800));
            }}

            const finalCheck = modal.shadowRoot.querySelector(
                'dialog[open], [open]');
            if (finalCheck) {{
                const cancel = [...modal.shadowRoot.querySelectorAll('button')]
                    .find(b => b.textContent.trim() === 'Cancel');
                if (cancel) cancel.click();
                return JSON.stringify({{ok: false,
                    error: 'modal did not close after Add'}});
            }}

            return JSON.stringify({{
                ok: true, flair: match.textContent.trim()}});
        }})()
    """
    )
    data = json.loads(result or "{}")
    if data.get("ok"):
        logger.info("Flair applied: %s", data.get("flair"))
    else:
        logger.warning("Flair selection issue: %s", data.get("error"))
    sleep_random(500, 800)


def _handle_rules_dialog(page: BridgePage) -> None:
    """Poll for and dismiss the 'Your post may break rules' dialog."""
    deadline = time.monotonic() + 8.0
    while time.monotonic() < deadline:
        time.sleep(1.0)
        result = page.evaluate(
            """
            (() => {
                const url = location.href;
                if (!url.includes('/submit')) return JSON.stringify(
                    {found: false, navigated: true, url});

                const allBtns = [...document.querySelectorAll('button')];
                const submitBtn = allBtns.find(
                    b => b.textContent.trim() === 'Submit without editing'
                );
                if (submitBtn) {
                    submitBtn.click();
                    return JSON.stringify({found: true, action: 'submitted'});
                }

                for (const el of document.querySelectorAll('*')) {
                    if (!el.shadowRoot) continue;
                    const btn = [...el.shadowRoot.querySelectorAll('button')]
                        .find(b => b.textContent.trim()
                            === 'Submit without editing');
                    if (btn) { btn.click(); return JSON.stringify(
                        {found: true, action: 'submitted_shadow'}); }
                }

                return JSON.stringify({found: false, waiting: true});
            })()
        """
        )
        data = json.loads(result or "{}")
        if data.get("navigated"):
            logger.info("Post navigation complete: %s", data.get("url", ""))
            return
        if data.get("action"):
            logger.info("Rules dialog handled: %s", data.get("action"))
            time.sleep(3.0)
            return
    logger.info("No rules dialog appeared within timeout")


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
    """Fill the body via contenteditable inside shreddit-composer.

    Inserts text line-by-line using insertText + insertParagraph to
    preserve paragraph breaks without the rich-text editor garbling
    content during chunked insertion.
    """
    body_js = json.dumps(body)
    result = page.evaluate(
        f"""
        (async () => {{
            const composer = document.querySelector(
                'shreddit-composer[name="body"]');
            if (!composer)
                return JSON.stringify({{ok: false, error: 'no body composer'}});
            const ce = composer.querySelector('div[contenteditable="true"]');
            if (!ce)
                return JSON.stringify({{ok: false, error: 'no contenteditable'}});

            ce.dispatchEvent(new MouseEvent('mousedown', {{bubbles: true}}));
            ce.dispatchEvent(new MouseEvent('mouseup', {{bubbles: true}}));
            ce.dispatchEvent(new MouseEvent('click', {{bubbles: true}}));
            ce.dispatchEvent(new FocusEvent('focus', {{bubbles: true}}));
            ce.focus();
            await new Promise(r => setTimeout(r, 300));

            const text = {body_js};
            const lines = text.split('\\n');
            for (let i = 0; i < lines.length; i++) {{
                if (lines[i])
                    document.execCommand('insertText', false, lines[i]);
                if (i < lines.length - 1) {{
                    const enterOpts = {{key: 'Enter', code: 'Enter',
                        keyCode: 13, which: 13, bubbles: true}};
                    ce.dispatchEvent(new KeyboardEvent('keydown', enterOpts));
                    ce.dispatchEvent(new KeyboardEvent('keypress', enterOpts));
                    ce.dispatchEvent(new KeyboardEvent('keyup', enterOpts));
                }}
                if (i % 10 === 9)
                    await new Promise(r => setTimeout(r, 50));
            }}
            return JSON.stringify({{ok: true, lines: lines.length}});
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
