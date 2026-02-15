import os
import hashlib
import logging
import threading
import time
from typing import Optional, Callable, Dict
import requests

logger = logging.getLogger('pifeed.cache')


class ImageCache:
    """Downloads and caches images on disk with LRU eviction."""

    def __init__(self, cache_dir: str, max_size_mb: int = 100, timeout: int = 10):
        self.cache_dir = cache_dir
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.timeout = timeout
        self._pending: Dict[str, bool] = {}  # URLs currently being downloaded
        self._lock = threading.Lock()
        os.makedirs(cache_dir, exist_ok=True)

    def get_local_path(self, url: str) -> Optional[str]:
        """Get the local cached path for a URL, or None if not cached."""
        if not url or url.startswith('demo://'):
            return None
        filepath = self._url_to_path(url)
        if os.path.exists(filepath):
            # Touch file for LRU tracking
            os.utime(filepath, None)
            return filepath
        return None

    def ensure_cached(self, url: str, callback: Optional[Callable[[str, Optional[str]], None]] = None):
        """Ensure an image is cached. Downloads in background if needed."""
        if not url or url.startswith('demo://'):
            return

        # Already cached?
        local_path = self.get_local_path(url)
        if local_path:
            if callback:
                callback(url, local_path)
            return

        # Already downloading?
        with self._lock:
            if url in self._pending:
                return
            self._pending[url] = True

        # Download in background
        thread = threading.Thread(target=self._download, args=(url, callback), daemon=True)
        thread.start()

    def _download(self, url: str, callback: Optional[Callable]):
        """Download an image and save to cache."""
        filepath = self._url_to_path(url)
        try:
            response = requests.get(url, timeout=self.timeout, stream=True)
            response.raise_for_status()

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.debug(f"Cached image: {url}")
            self._evict_if_needed()

            if callback:
                callback(url, filepath)

        except Exception as e:
            logger.warning(f"Failed to download image {url}: {e}")
            if os.path.exists(filepath):
                os.remove(filepath)
            if callback:
                callback(url, None)

        finally:
            with self._lock:
                self._pending.pop(url, None)

    def _url_to_path(self, url: str) -> str:
        """Convert a URL to a local file path using hash."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        # Try to preserve extension
        ext = '.jpg'
        for e in ('.png', '.gif', '.webp', '.jpeg', '.jpg'):
            if e in url.lower():
                ext = e
                break
        return os.path.join(self.cache_dir, f'{url_hash}{ext}')

    def _evict_if_needed(self):
        """Remove oldest files if cache exceeds max size."""
        try:
            files = []
            total_size = 0
            for filename in os.listdir(self.cache_dir):
                if filename.startswith('demo_'):
                    continue  # Don't evict demo images
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    stat = os.stat(filepath)
                    files.append((filepath, stat.st_atime, stat.st_size))
                    total_size += stat.st_size

            if total_size <= self.max_size_bytes:
                return

            # Sort by access time (oldest first)
            files.sort(key=lambda x: x[1])

            while total_size > self.max_size_bytes and files:
                filepath, _, size = files.pop(0)
                try:
                    os.remove(filepath)
                    total_size -= size
                    logger.debug(f"Evicted cached image: {filepath}")
                except OSError:
                    pass

        except Exception as e:
            logger.warning(f"Cache eviction error: {e}")

    def get_cache_size_mb(self) -> float:
        """Get current cache size in MB."""
        total = 0
        try:
            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)
                if os.path.isfile(filepath):
                    total += os.path.getsize(filepath)
        except OSError:
            pass
        return total / (1024 * 1024)
