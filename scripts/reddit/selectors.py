"""Reddit page CSS selectors.

These target new Reddit (www.reddit.com) as of 2025-2026.
Reddit uses shreddit-* web components and data-testid attributes.
Selectors may need updating if Reddit changes its frontend.
"""

# ========== Login / Auth ==========
LOGIN_BUTTON = (
    'a[href*="/login"], '
    'button[data-testid="login-button"], '
    'a[data-testid="login-button"]'
)
LOGGED_IN_USER = (
    "#user-drawer-avatar-logged-in, "
    "#expand-user-drawer-button, "
    "#header-action-item-chat-button, "
    '[data-testid="current-user"], '
    'span[class*="header-user-name"]'
)

# ========== Home / Feed ==========
POST_CONTAINER = "shreddit-post"

# ========== Search ==========
SEARCH_RESULT = '[data-testid="search-post-unit"]'

# ========== Post Detail ==========
POST_DETAIL_TITLE = 'h1, [data-testid="post-title"], [slot="title"]'

# ========== Comments ==========
COMMENT_CONTAINER = "shreddit-comment"
COMMENT_SUBMIT = (
    'button[type="submit"][slot="submit-button"], '
    'button[data-testid="comment-submission-form-submit"]'
)

# ========== Submit / Publish ==========
SUBMIT_URL_INPUT = (
    'input[placeholder*="Url"], input[name="url"], input[placeholder*="url"]'
)
FILE_INPUT = 'input[type="file"]'
