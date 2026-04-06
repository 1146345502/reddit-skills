"""Human behavior simulation parameters (delays, scrolling)."""

import random
import time


def sleep_random(min_ms: int, max_ms: int) -> None:
    """Random delay."""
    if max_ms <= min_ms:
        time.sleep(min_ms / 1000.0)
        return
    delay = random.randint(min_ms, max_ms) / 1000.0
    time.sleep(delay)


INACCESSIBLE_KEYWORDS = [
    "this community is private",
    "this post was removed",
    "this content is no longer available",
    "page not found",
    "this community has been banned",
    "content is unavailable",
    "this account has been suspended",
    "quarantined community",
]
