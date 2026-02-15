import logging
import re
import threading
from typing import List, Optional, Callable
from datetime import datetime
from urllib.parse import urljoin, urlparse
import feedparser
from .models import FeedItem

logger = logging.getLogger('pifeed.fetcher')


def parse_feed_items(feed_url: str, source_name: str, accent_color: str,
                     timeout: int = 15) -> List[FeedItem]:
    """Parse an RSS/Atom feed and return a list of FeedItems."""
    try:
        import requests as _requests
        headers = {'User-Agent': 'PiFeed/1.0 (RSS Reader)'}
        resp = _requests.get(feed_url, timeout=timeout, headers=headers)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            logger.error(f"Feed parse error for {source_name}: {feed.bozo_exception}")
            return []

        # Determine the feed's base URL for resolving relative image paths
        feed_link = feed.feed.get('link', feed_url)

        items = []
        for entry in feed.entries:
            # Extract image URL from various feed formats
            raw_image = _extract_image(entry)
            # Fallback: fetch og:image from the article page
            if not raw_image:
                raw_image = _fetch_og_image(entry.get('link', ''))
            image_url = _normalize_url(raw_image, feed_link)

            # Parse published date
            published = None
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                try:
                    published = datetime(*entry.published_parsed[:6])
                except (ValueError, TypeError):
                    pass

            item = FeedItem(
                title=entry.get('title', ''),
                summary=entry.get('summary', entry.get('description', '')),
                link=entry.get('link', ''),
                image_url=image_url,
                published=published,
                source_name=source_name,
                accent_color=accent_color,
            )
            items.append(item)

        logger.info(f"Fetched {len(items)} items from {source_name}")
        return items

    except Exception as e:
        logger.error(f"Failed to fetch feed for {source_name}: {e}")
        return []


def _extract_image(entry) -> str:
    """Extract the best image URL from a feed entry."""
    # Check media:content — pick the largest image by width
    if hasattr(entry, 'media_content') and entry.media_content:
        images = [
            m for m in entry.media_content
            if m.get('medium') == 'image'
            or m.get('type', '').startswith('image')
            or m.get('url', '')
        ]
        if images:
            best = max(images, key=lambda m: int(m.get('width', 0) or 0))
            url = best.get('url', '')
            if url:
                return url

    # Check media:thumbnail
    if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url', '')

    # Check enclosures
    if hasattr(entry, 'enclosures') and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image'):
                return enc.get('href', enc.get('url', ''))

    # Check for image in summary/description HTML
    content = entry.get('summary', '') or entry.get('description', '')
    if content:
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)

    # Check content:encoded (WordPress feeds, full article HTML)
    if hasattr(entry, 'content') and entry.content:
        for block in entry.content:
            html = block.get('value', '')
            if html:
                match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html)
                if match:
                    return match.group(1)

    return ''


def _normalize_url(url: str, base_url: str) -> str:
    """Resolve *url* against *base_url* and fix common feed quirks.

    Handles relative paths (``/images/foo.jpg``), protocol-relative
    URLs (``//cdn.example.com/…``), and malformed concatenations like
    ``https://site.comhttps://other.com/…``.
    """
    if not url:
        return ''

    # Fix double-scheme: "https://site.comhttps://real.com/path"
    for scheme in ('https://', 'http://'):
        idx = url.find(scheme, 1)
        if idx > 0:
            url = url[idx:]
            break

    parsed = urlparse(url)
    if not (parsed.scheme and parsed.netloc):
        url = urljoin(base_url, url)

    # BBC iChef thumbnails: upscale from 240px to 976px
    if 'ichef.bbci.co.uk' in url:
        url = re.sub(r'/\d+/', '/976/', url, count=1)

    return url


def _fetch_og_image(article_url: str, timeout: int = 8) -> str:
    """Fetch an article page and extract the og:image meta tag."""
    if not article_url:
        return ''
    try:
        import requests as _requests
        headers = {'User-Agent': 'PiFeed/1.0 (RSS Reader)'}
        resp = _requests.get(article_url, timeout=timeout, headers=headers,
                             stream=True)
        resp.raise_for_status()
        # Read decoded chunks until we find og:image or hit 128KB
        text = ''
        for chunk in resp.iter_content(chunk_size=16384, decode_unicode=True):
            if chunk:
                text += chunk if isinstance(chunk, str) else chunk.decode('utf-8', errors='ignore')
            if len(text) >= 131072 or 'og:image' in text:
                break
        resp.close()
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            text,
        )
        if not match:
            # Try reversed attribute order
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                text,
            )
        if match:
            return match.group(1)
    except Exception as e:
        logger.debug(f"og:image fetch failed for {article_url}: {e}")
    return ''


class FeedFetcherThread:
    """Manages background feed fetching."""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._threads: List[threading.Thread] = []

    def fetch_async(self, feed_url: str, source_name: str, accent_color: str,
                    callback: Callable[[List[FeedItem]], None]):
        """Fetch a feed in the background and call callback with results on completion."""
        def _worker():
            items = parse_feed_items(feed_url, source_name, accent_color, self.timeout)
            # Callback must be scheduled on main thread by the caller
            callback(items)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()
        self._threads.append(thread)
        # Clean up finished threads
        self._threads = [t for t in self._threads if t.is_alive()]
