"""Reddit automation exception hierarchy."""


class RedditError(Exception):
    """Base exception for Reddit automation."""


class NoPostsError(RedditError):
    """No posts captured."""

    def __init__(self) -> None:
        super().__init__("No posts captured from page")


class NoPostDetailError(RedditError):
    """No post detail captured."""

    def __init__(self) -> None:
        super().__init__("No post detail captured")


class NotLoggedInError(RedditError):
    """Not logged in."""

    def __init__(self) -> None:
        super().__init__("Not logged in. Please log in to Reddit in your browser first.")


class PostNotAccessibleError(RedditError):
    """Post not accessible."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Post not accessible: {reason}")


class PublishError(RedditError):
    """Publish failed."""


class TitleTooLongError(PublishError):
    """Title exceeds length limit."""

    def __init__(self, current: int, maximum: int) -> None:
        self.current = current
        self.maximum = maximum
        super().__init__(f"Title length {current} exceeds maximum {maximum}")


class BridgeError(RedditError):
    """Bridge communication error."""


class ElementNotFoundError(RedditError):
    """Page element not found."""

    def __init__(self, selector: str) -> None:
        self.selector = selector
        super().__init__(f"Element not found: {selector}")
