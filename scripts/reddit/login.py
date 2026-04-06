"""Reddit login management."""

from __future__ import annotations

import logging
import time

from .bridge import BridgePage
from .human import sleep_random
from .selectors import LOGGED_IN_USER, LOGIN_BUTTON
from .urls import HOME_URL

logger = logging.getLogger(__name__)


def check_login_status(page: BridgePage) -> bool:
    """Check if user is logged in to Reddit.

    Returns:
        True if logged in, False otherwise.
    """
    current_url = page.evaluate("location.href") or ""
    if "reddit.com" not in current_url:
        page.navigate(HOME_URL)
        page.wait_for_load()

    page.wait_dom_stable(timeout=5.0)

    deadline = time.monotonic() + 10.0
    while time.monotonic() < deadline:
        if page.has_element(LOGGED_IN_USER):
            return True
        if page.has_element(LOGIN_BUTTON):
            return False
        time.sleep(0.3)

    return page.has_element(LOGGED_IN_USER)


def get_current_username(page: BridgePage) -> str:
    """Get the currently logged-in username.

    Returns:
        Username string, or empty string if not logged in.
    """
    try:
        if not check_login_status(page):
            return ""

        username = page.evaluate(
            """
            (() => {
                // New Reddit: user drawer has links like /user/USERNAME/dashboard
                const drawerLinks = document.querySelectorAll(
                    '#user-drawer-content a[href*="/user/"]'
                );
                for (const link of drawerLinks) {
                    const m = link.getAttribute('href').match(/\\/user\\/([^/]+)/);
                    if (m && m[1]) return m[1];
                }
                // Fallback: any profile link in the header area
                const headerLinks = document.querySelectorAll(
                    'header a[href*="/user/"], ' +
                    'reddit-header-large a[href*="/user/"], ' +
                    'nav a[href*="/user/"]'
                );
                for (const link of headerLinks) {
                    const href = link.getAttribute('href') || '';
                    const m = href.match(/\\/user\\/([^/]+)/);
                    if (m && m[1]) return m[1];
                }
                // Legacy selectors
                const el = document.querySelector(
                    '[data-testid="current-user"] span, ' +
                    'span[class*="header-user-name"]'
                );
                if (el) return el.textContent.trim();
                return '';
            })()
        """
        )
        return username or ""
    except Exception:
        logger.warning("Failed to get username")
        return ""


def logout(page: BridgePage) -> bool:
    """Log out via Reddit UI.

    Returns:
        True if logged out successfully, False if not logged in.
    """
    page.navigate(HOME_URL)
    page.wait_for_load()
    sleep_random(800, 1500)

    if not check_login_status(page):
        logger.info("Not logged in")
        return False

    try:
        page.click_element(
            '#USER_DROPDOWN_ID, button[aria-label*="User"], [id*="header-action-item"]'
        )
        sleep_random(500, 800)

        page.click_element(
            'a[href*="logout"], '
            'button[data-testid="logout-button"], '
            '[data-menuitem-identifier="logout"]'
        )
        sleep_random(1000, 2000)

        confirm_btn = page.query_selector('button[type="submit"], button.logout')
        if confirm_btn:
            page.click_element('button[type="submit"], button.logout')
            sleep_random(1000, 1500)

        logger.info("Logged out successfully")
        return True
    except Exception as e:
        logger.warning("Logout failed: %s", e)
        return False
