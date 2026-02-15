from dataclasses import dataclass, field
from html import unescape
from typing import List, Optional
from datetime import datetime


@dataclass
class FeedItem:
    """A single news story from a feed."""
    title: str = ''
    summary: str = ''
    link: str = ''
    image_url: str = ''
    local_image_path: Optional[str] = None
    published: Optional[datetime] = None
    source_name: str = ''
    accent_color: str = '#E53935'

    @property
    def has_image(self) -> bool:
        return bool(self.local_image_path)

    @property
    def display_title(self) -> str:
        """Title cleaned up for display."""
        if not self.title:
            return 'Untitled'
        return unescape(self.title).strip()

    @property
    def display_summary(self) -> str:
        """Summary cleaned up for display, strip HTML tags and entities."""
        import re
        if not self.summary:
            return ''
        text = re.sub(r'<[^>]+>', '', self.summary)
        text = unescape(text).strip()
        if len(text) > 650:
            text = text[:647] + '...'
        return text


@dataclass
class FeedSource:
    """A news source with its items and metadata."""
    name: str = ''
    feed_url: str = ''
    accent_color: str = '#E53935'
    items: List[FeedItem] = field(default_factory=list)
    last_fetched: Optional[datetime] = None
    is_demo: bool = False
    refresh_interval: int = 3600
    story_duration: float = 12.0
    items_limit: int = 10

    # Per-source font overrides (None means use global)
    headline_size: Optional[int] = None
    summary_size: Optional[int] = None
    queue_item_size: Optional[int] = None
    ticker_size: Optional[int] = None

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def is_stale(self) -> bool:
        if self.last_fetched is None:
            return True
        elapsed = (datetime.now() - self.last_fetched).total_seconds()
        return elapsed >= self.refresh_interval
