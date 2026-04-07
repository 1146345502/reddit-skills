"""Image downloader with local caching."""

from __future__ import annotations

import logging
import os
import time
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(str(Path.home()), ".reddit-skills", "images")


def download_image(url: str) -> str:
    """Download an image from URL and cache locally.

    Returns:
        Absolute path to the cached image file.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)

    req = urllib.request.Request(url, headers={"User-Agent": "reddit-skills/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read()
        content_type = resp.headers.get("Content-Type", "")

    ext = _guess_extension(url, content_type)
    filename = f"{int(time.time() * 1000)}{ext}"
    filepath = os.path.join(CACHE_DIR, filename)

    if not os.path.exists(filepath):
        with open(filepath, "wb") as f:
            f.write(content)
        logger.info("Downloaded: %s -> %s", url, filepath)
    else:
        logger.debug("Cache hit: %s", filepath)

    return filepath


def process_images(paths: list[str]) -> list[str]:
    """Process a list of image paths/URLs, downloading URLs as needed.

    Returns:
        List of absolute local file paths.
    """
    result = []
    for path in paths:
        if path.startswith("http://") or path.startswith("https://"):
            try:
                local = download_image(path)
                result.append(local)
            except Exception as e:
                logger.error("Failed to download %s: %s", path, e)
        else:
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                result.append(abs_path)
            else:
                logger.warning("File not found: %s", abs_path)
    return result


def _guess_extension(url: str, content_type: str) -> str:
    """Guess file extension from URL or content-type."""
    type_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    if content_type in type_map:
        return type_map[content_type]

    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
        if ext in url.lower():
            return ext

    return ".jpg"
