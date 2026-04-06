"""Reddit URL constants and builder functions."""

from urllib.parse import urlencode

HOME_URL = "https://www.reddit.com/"
SUBMIT_URL = "https://www.reddit.com/submit"


def make_subreddit_url(subreddit: str, sort: str = "hot") -> str:
    """Build subreddit URL with sort."""
    return f"https://www.reddit.com/r/{subreddit}/{sort}/"


def make_post_detail_url(permalink: str) -> str:
    """Build post detail URL from permalink."""
    if permalink.startswith("http"):
        return permalink
    return f"https://www.reddit.com{permalink}"


def make_search_url(query: str, sort: str = "relevance", time: str = "all") -> str:
    """Build search URL."""
    params = urlencode({"q": query, "sort": sort, "t": time})
    return f"https://www.reddit.com/search/?{params}"


def make_user_profile_url(username: str) -> str:
    """Build user profile URL."""
    return f"https://www.reddit.com/user/{username}/"


def make_submit_url(subreddit: str = "") -> str:
    """Build submit page URL."""
    if subreddit:
        return f"https://www.reddit.com/r/{subreddit}/submit"
    return SUBMIT_URL
