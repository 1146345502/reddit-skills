"""Reddit data type definitions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Author:
    name: str = ""
    profile_url: str = ""
    avatar_url: str = ""
    karma: int = 0

    @classmethod
    def from_dict(cls, d: dict) -> Author:
        return cls(
            name=d.get("name", ""),
            profile_url=d.get("profileUrl", ""),
            avatar_url=d.get("avatarUrl", ""),
            karma=d.get("karma", 0),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "profileUrl": self.profile_url,
        }


@dataclass
class PostStats:
    score: int = 0
    upvote_ratio: float = 0.0
    num_comments: int = 0
    is_saved: bool = False
    vote_state: int = 0  # 1=upvoted, -1=downvoted, 0=none

    @classmethod
    def from_dict(cls, d: dict) -> PostStats:
        return cls(
            score=d.get("score", 0),
            upvote_ratio=d.get("upvoteRatio", 0.0),
            num_comments=d.get("numComments", 0),
            is_saved=d.get("isSaved", False),
            vote_state=d.get("voteState", 0),
        )

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "upvoteRatio": self.upvote_ratio,
            "numComments": self.num_comments,
            "isSaved": self.is_saved,
        }


@dataclass
class Post:
    id: str = ""
    title: str = ""
    subreddit: str = ""
    author: Author = field(default_factory=Author)
    url: str = ""
    permalink: str = ""
    post_type: str = ""  # text, link, image, video, gallery
    created_utc: float = 0.0
    stats: PostStats = field(default_factory=PostStats)
    flair: str = ""
    is_nsfw: bool = False
    is_spoiler: bool = False
    thumbnail: str = ""
    domain: str = ""
    selftext: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> Post:
        return cls(
            id=d.get("id", ""),
            title=d.get("title", ""),
            subreddit=d.get("subreddit", ""),
            author=Author.from_dict(d.get("author", {})),
            url=d.get("url", ""),
            permalink=d.get("permalink", ""),
            post_type=d.get("postType", ""),
            created_utc=d.get("createdUtc", 0.0),
            stats=PostStats.from_dict(d.get("stats", {})),
            flair=d.get("flair", ""),
            is_nsfw=d.get("isNsfw", False),
            is_spoiler=d.get("isSpoiler", False),
            thumbnail=d.get("thumbnail", ""),
            domain=d.get("domain", ""),
            selftext=d.get("selftext", ""),
        )

    def to_dict(self) -> dict:
        result: dict = {
            "id": self.id,
            "title": self.title,
            "subreddit": self.subreddit,
            "author": self.author.to_dict(),
            "permalink": self.permalink,
            "postType": self.post_type,
            "createdUtc": self.created_utc,
            "stats": self.stats.to_dict(),
        }
        if self.flair:
            result["flair"] = self.flair
        if self.url:
            result["url"] = self.url
        if self.domain:
            result["domain"] = self.domain
        if self.selftext:
            result["selftext"] = self.selftext
        return result


@dataclass
class Comment:
    id: str = ""
    author: Author = field(default_factory=Author)
    body: str = ""
    score: int = 0
    created_utc: float = 0.0
    depth: int = 0
    is_op: bool = False
    replies: list[Comment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> Comment:
        return cls(
            id=d.get("id", ""),
            author=Author.from_dict(d.get("author", {})),
            body=d.get("body", ""),
            score=d.get("score", 0),
            created_utc=d.get("createdUtc", 0.0),
            depth=d.get("depth", 0),
            is_op=d.get("isOp", False),
            replies=[cls.from_dict(r) for r in d.get("replies", []) or []],
        )

    def to_dict(self) -> dict:
        result: dict = {
            "id": self.id,
            "author": self.author.to_dict(),
            "body": self.body,
            "score": self.score,
            "createdUtc": self.created_utc,
            "depth": self.depth,
        }
        if self.is_op:
            result["isOp"] = True
        if self.replies:
            result["replies"] = [r.to_dict() for r in self.replies]
        return result


@dataclass
class PostDetail:
    post: Post = field(default_factory=Post)
    selftext: str = ""
    selftext_html: str = ""
    comments: list[Comment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> PostDetail:
        return cls(
            post=Post.from_dict(d.get("post", {})),
            selftext=d.get("selftext", ""),
            selftext_html=d.get("selftextHtml", ""),
            comments=[Comment.from_dict(c) for c in d.get("comments", []) or []],
        )

    def to_dict(self) -> dict:
        return {
            "post": self.post.to_dict(),
            "selftext": self.selftext,
            "comments": [c.to_dict() for c in self.comments],
        }


@dataclass
class UserProfile:
    username: str = ""
    display_name: str = ""
    karma: int = 0
    post_karma: int = 0
    comment_karma: int = 0
    created_utc: float = 0.0
    description: str = ""
    is_mod: bool = False
    avatar_url: str = ""

    def to_dict(self) -> dict:
        return {
            "username": self.username,
            "displayName": self.display_name,
            "karma": self.karma,
            "postKarma": self.post_karma,
            "commentKarma": self.comment_karma,
            "createdUtc": self.created_utc,
            "description": self.description,
        }


@dataclass
class SearchFilter:
    """Search filter options."""

    sort: str = "relevance"  # relevance, hot, top, new, comments
    time: str = "all"  # hour, day, week, month, year, all
    post_type: str = ""  # link, self, image, video, gallery


@dataclass
class SubmitTextContent:
    """Text post submission."""

    subreddit: str = ""
    title: str = ""
    body: str = ""
    flair_id: str = ""
    nsfw: bool = False
    spoiler: bool = False


@dataclass
class SubmitLinkContent:
    """Link post submission."""

    subreddit: str = ""
    title: str = ""
    url: str = ""
    flair_id: str = ""
    nsfw: bool = False
    spoiler: bool = False


@dataclass
class SubmitImageContent:
    """Image post submission."""

    subreddit: str = ""
    title: str = ""
    image_paths: list[str] = field(default_factory=list)
    flair_id: str = ""
    nsfw: bool = False
    spoiler: bool = False


@dataclass
class ActionResult:
    """Generic action response."""

    post_id: str = ""
    success: bool = False
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "postId": self.post_id,
            "success": self.success,
            "message": self.message,
        }
