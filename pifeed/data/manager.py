"""Central feed manager - orchestrates sources, rotation, and events.

No Kivy dependency. Uses simple callbacks and timer-based scheduling
driven by the game loop's update(dt) calls.
"""

import os
import logging
import threading
from typing import List, Optional, Callable
from datetime import datetime
from .models import FeedItem, FeedSource
from .fetcher import FeedFetcherThread
from .cache import ImageCache
from .demo import DemoDataProvider

logger = logging.getLogger('pifeed.manager')


class FeedManager:
    """Central coordinator for feed data, rotation, and events."""

    def __init__(self, config, profile_manager):
        self.config = config
        self.profile_manager = profile_manager
        self.sources: List[FeedSource] = []
        self._current_source_idx: int = 0
        self._current_item_idx: int = 0

        # Timer-based scheduling (updated via update(dt))
        self._advance_timer: float = 0.0
        self._advance_duration: float = config.timing.story_duration
        self._advance_active: bool = False
        self._fetch_timers: dict = {}  # source_name -> {elapsed, interval}
        self._profile_check_timer: float = 0.0

        # Callbacks
        self._on_story_changed: Optional[Callable] = None
        self._on_source_changed: Optional[Callable] = None

        # Thread-safe queue for results from background threads
        self._pending_results: list = []
        self._results_lock = threading.Lock()

        # Initialize subsystems
        cache_dir = config.app.cache_dir
        if not os.path.isabs(cache_dir):
            cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))), cache_dir)

        self.fetcher = FeedFetcherThread(timeout=config.cache.feed_timeout)
        self.image_cache = ImageCache(cache_dir, max_size_mb=config.cache.max_size_mb,
                                       timeout=config.cache.image_timeout)
        self.demo_provider = DemoDataProvider(cache_dir)

        # Watch for profile changes
        profile_manager.on_profiles_changed(self._on_profiles_changed)

    def bind(self, on_story_changed=None, on_source_changed=None):
        """Register event callbacks."""
        if on_story_changed:
            self._on_story_changed = on_story_changed
        if on_source_changed:
            self._on_source_changed = on_source_changed

    def _dispatch_story_changed(self, old_item, new_item):
        if self._on_story_changed:
            self._on_story_changed(old_item, new_item)

    def _dispatch_source_changed(self, source):
        if self._on_source_changed:
            self._on_source_changed(source)

    def start(self, demo_mode: bool = False):
        """Start the feed manager."""
        if demo_mode:
            self._setup_demo()
        else:
            self._setup_from_profiles()

        # Only kick-start rotation if a source already has items (demo
        # mode).  For real feeds the items arrive asynchronously and
        # _on_fetch_complete will start the rotation once the first
        # source responds.
        if self.sources and self.current_source and self.current_source.items:
            self._schedule_advance()
            self._dispatch_source_changed(self.current_source)
            self._dispatch_story_changed(None, self.current_item)

    def update(self, dt):
        """Called every frame from the game loop. Processes timers and pending results."""
        # Process results from background threads
        self._process_pending_results()

        # Story advance timer
        if self._advance_active:
            self._advance_timer += dt
            if self._advance_timer >= self._advance_duration:
                self._advance_active = False
                self.advance_story()

        # Feed refresh timers
        for source_name, timer_info in list(self._fetch_timers.items()):
            timer_info['elapsed'] += dt
            if timer_info['elapsed'] >= timer_info['interval']:
                timer_info['elapsed'] = 0.0
                source = timer_info.get('source')
                if source:
                    self._do_fetch(source)

        # Profile hot-reload check (every 5 seconds)
        self._profile_check_timer += dt
        if self._profile_check_timer >= 5.0:
            self._profile_check_timer = 0.0
            self.profile_manager.check_for_changes()

    def _process_pending_results(self):
        """Process results queued from background threads."""
        with self._results_lock:
            results = list(self._pending_results)
            self._pending_results.clear()

        for callback, args in results:
            callback(*args)

    def _enqueue_result(self, callback, *args):
        """Thread-safe: queue a callback to run on the main thread."""
        with self._results_lock:
            self._pending_results.append((callback, args))

    def _setup_demo(self):
        """Set up demo data sources."""
        demo_profiles = [p for p in self.profile_manager.profiles if p.is_demo]
        if not demo_profiles:
            source = self.demo_provider.create_source()
            self.sources = [source]
        else:
            for profile in demo_profiles:
                source = self.demo_provider.create_source(accent_color=profile.accent_color)
                source.name = profile.name
                source.story_duration = profile.story_duration or self.config.timing.story_duration
                self.sources.append(source)

    def _setup_from_profiles(self):
        """Set up feed sources from profiles and start fetching."""
        self.sources.clear()
        self._fetch_timers.clear()
        for profile in self.profile_manager.get_enabled_profiles():
            if profile.is_demo:
                source = self.demo_provider.create_source(accent_color=profile.accent_color)
                source.name = profile.name
            else:
                source = FeedSource(
                    name=profile.name,
                    feed_url=profile.feed_url,
                    accent_color=profile.accent_color,
                    refresh_interval=profile.refresh_interval or self.config.timing.feed_refresh_interval,
                    story_duration=profile.story_duration or self.config.timing.story_duration,
                    items_limit=profile.items_limit or self.config.timing.items_per_source,
                    headline_size=profile.headline_size,
                    summary_size=profile.summary_size,
                    queue_item_size=profile.queue_item_size,
                    ticker_size=profile.ticker_size,
                )
                self._schedule_fetch(source)
            self.sources.append(source)

    def _schedule_fetch(self, source: FeedSource):
        """Schedule feed fetching for a source."""
        if source.is_demo or not source.feed_url:
            return
        # Fetch immediately
        self._do_fetch(source)
        # Schedule periodic refresh
        if source.refresh_interval > 0:
            self._fetch_timers[source.name] = {
                'elapsed': 0.0,
                'interval': float(source.refresh_interval),
                'source': source,
            }

    def _do_fetch(self, source: FeedSource):
        """Trigger a background feed fetch."""
        def on_fetched(items):
            self._enqueue_result(self._on_fetch_complete, source, items)
        self.fetcher.fetch_async(source.feed_url, source.name, source.accent_color, on_fetched)

    def _on_fetch_complete(self, source: FeedSource, items: List[FeedItem]):
        """Handle completed feed fetch (runs on main thread via _process_pending_results)."""
        if items:
            source.items = items[:source.items_limit]
            source.last_fetched = datetime.now()

            # Start caching images
            for item in source.items:
                if item.image_url:
                    def _make_callback(img_url):
                        def _cb(url, path):
                            self._enqueue_result(self._on_image_cached, url, path)
                        return _cb
                    self.image_cache.ensure_cached(
                        item.image_url,
                        callback=_make_callback(item.image_url),
                    )

            logger.info(f"Updated {source.name} with {len(items)} items")

            if not self._advance_active:
                # Advance timer is dead — either first fetch to arrive, or
                # rotation stalled because all sources were empty.  Point
                # at this source and kick-start the rotation.
                self._current_source_idx = self.sources.index(source)
                self._current_item_idx = 0
                self._dispatch_source_changed(source)
                self._dispatch_story_changed(None, self.current_item)
                self._schedule_advance()
            elif source == self.current_source and self._current_item_idx == 0:
                # Current source got a refresh while showing its first item
                self._dispatch_story_changed(None, self.current_item)
        else:
            logger.warning(f"No items received for {source.name}")

    def _on_image_cached(self, url: str, local_path: Optional[str]):
        """Handle completed image download."""
        if not local_path:
            return
        for source in self.sources:
            for item in source.items:
                if item.image_url == url:
                    item.local_image_path = local_path

        current = self.current_item
        if current and current.image_url == url:
            self._dispatch_story_changed(current, current)

    @property
    def current_source(self) -> Optional[FeedSource]:
        if not self.sources:
            return None
        return self.sources[self._current_source_idx % len(self.sources)]

    @property
    def current_item(self) -> Optional[FeedItem]:
        source = self.current_source
        if not source or not source.items:
            return None
        return source.items[self._current_item_idx % len(source.items)]

    @property
    def previous_item(self) -> Optional[FeedItem]:
        """The item before the current one, or ``None`` at position 0."""
        source = self.current_source
        if not source or not source.items or self._current_item_idx <= 0:
            return None
        return source.items[self._current_item_idx - 1]

    @property
    def next_source(self) -> Optional[FeedSource]:
        """The next source in the rotation, or ``None`` if only one."""
        if len(self.sources) < 2:
            return None
        idx = (self._current_source_idx + 1) % len(self.sources)
        return self.sources[idx]

    def queue_items(self, count: int = 6) -> List[FeedItem]:
        """Get the next items in queue for display."""
        source = self.current_source
        if not source or not source.items:
            return []
        items = []
        idx = self._current_item_idx + 1
        for _ in range(count):
            if idx < len(source.items):
                items.append(source.items[idx])
                idx += 1
            else:
                break
        return items

    def ticker_items(self) -> List[FeedItem]:
        """Get all items from all sources for the ticker."""
        all_items = []
        for source in self.sources:
            all_items.extend(source.items)
        return all_items

    def advance_story(self):
        """Advance to the next story."""
        old_item = self.current_item
        source = self.current_source

        if not source or not source.items:
            self._advance_to_next_source()
            return

        self._current_item_idx += 1

        if self._current_item_idx >= len(source.items) or \
           self._current_item_idx >= source.items_limit:
            self._advance_to_next_source()
            return

        new_item = self.current_item
        self._dispatch_story_changed(old_item, new_item)
        self._schedule_advance()

    def previous_story(self):
        """Go back to the previous story."""
        old_item = self.current_item
        source = self.current_source

        if not source or not source.items:
            return

        if self._current_item_idx > 0:
            self._current_item_idx -= 1
            new_item = self.current_item
            self._dispatch_story_changed(old_item, new_item)
            self._schedule_advance()
        else:
            self._retreat_to_previous_source()

    def advance_source(self):
        """Skip to the next source."""
        self._advance_to_next_source()

    def previous_source(self):
        """Skip to the previous source."""
        self._retreat_to_previous_source()

    def _retreat_to_previous_source(self):
        """Move to the previous source with items."""
        if not self.sources:
            return

        old_source = self.current_source
        attempts = len(self.sources)

        while attempts > 0:
            self._current_source_idx = (self._current_source_idx - 1) % len(self.sources)
            self._current_item_idx = 0

            if self.current_source and self.current_source.items:
                break
            attempts -= 1

        new_source = self.current_source
        if new_source and new_source != old_source:
            self._dispatch_source_changed(new_source)

        if self.current_item:
            self._dispatch_story_changed(None, self.current_item)
            self._schedule_advance()

    def _advance_to_next_source(self):
        """Move to the next source with items."""
        if not self.sources:
            return

        old_source = self.current_source
        attempts = len(self.sources)

        while attempts > 0:
            self._current_source_idx = (self._current_source_idx + 1) % len(self.sources)
            self._current_item_idx = 0

            if self.current_source and self.current_source.items:
                break
            attempts -= 1

        new_source = self.current_source
        if new_source and new_source != old_source:
            self._dispatch_source_changed(new_source)

        if self.current_item:
            self._dispatch_story_changed(None, self.current_item)
            self._schedule_advance()

    def _schedule_advance(self):
        """Schedule the next story advance."""
        source = self.current_source
        self._advance_duration = source.story_duration if source else self.config.timing.story_duration
        self._advance_timer = 0.0
        self._advance_active = True

    def source_progress(self) -> tuple:
        """Return (current_item_index, total_items) for the current source."""
        source = self.current_source
        if not source:
            return (0, 0)
        return (self._current_item_idx + 1, len(source.items))

    def sources_progress(self) -> tuple:
        """Return (current_source_index, total_sources) for rotation display."""
        if not self.sources:
            return (0, 0)
        return (self._current_source_idx + 1, len(self.sources))

    def stop(self):
        """Stop all timers."""
        self._advance_active = False
        self._fetch_timers.clear()

    def _on_profiles_changed(self, profiles):
        """Handle profile hot-reload."""
        logger.info("Profiles changed, reconfiguring sources...")
        self.stop()
        self._current_source_idx = 0
        self._current_item_idx = 0
        self._setup_from_profiles()
        # Only kick-start if a source already has items (e.g. demo).
        # Real feeds will start rotation via _on_fetch_complete.
        if self.sources and self.current_source and self.current_source.items:
            self._schedule_advance()
            self._dispatch_source_changed(self.current_source)
            self._dispatch_story_changed(None, self.current_item)
