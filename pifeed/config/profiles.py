"""Source-profile loading with hot-reload file watching.

Each YAML file in the profiles directory describes a single news source.
:class:`ProfileManager` loads them all on startup and can be polled
periodically to pick up changes without restarting the application.
"""

import logging
import os
from typing import Callable, List, Optional

import yaml

from .schema import SourceProfile

logger = logging.getLogger('pifeed.profiles')


class ProfileManager:
    """Manages the set of :class:`SourceProfile` instances.

    Parameters
    ----------
    profiles_dir:
        Filesystem path to the directory containing profile YAML files.
    """

    def __init__(self, profiles_dir: str):
        self.profiles_dir: str = profiles_dir
        self.profiles: List[SourceProfile] = []
        self._file_mtimes: dict = {}
        self._on_change_callbacks: List[Callable] = []
        self.load_all()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load_all(self) -> None:
        """Load all YAML profile files from the profiles directory."""
        self.profiles.clear()
        self._file_mtimes.clear()

        if not os.path.isdir(self.profiles_dir):
            logger.warning("Profiles directory not found: %s", self.profiles_dir)
            return

        for filename in sorted(os.listdir(self.profiles_dir)):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(self.profiles_dir, filename)
                # Track mtime for ALL files so check_for_changes doesn't
                # flag disabled/skipped profiles as perpetually "new".
                self._file_mtimes[filepath] = os.path.getmtime(filepath)
                profile = self._load_profile(filepath)
                if profile and profile.enabled:
                    self.profiles.append(profile)

    def _load_profile(self, filepath: str) -> Optional[SourceProfile]:
        """Load a single profile from a YAML file."""
        try:
            with open(filepath) as f:
                data = yaml.safe_load(f) or {}

            profile = SourceProfile()
            profile.name = data.get('name', '')
            profile.feed_url = data.get('feed_url', '')
            profile.enabled = data.get('enabled', True)
            profile.is_demo = data.get('demo', False)

            # Timing overrides
            timing = data.get('timing', {})
            profile.refresh_interval = timing.get('refresh_interval')
            profile.story_duration = timing.get('story_duration')

            # Display overrides
            display = data.get('display', {})
            profile.items_limit = display.get('items_limit')
            profile.accent_color = display.get('accent_color', '#E53935')

            # Font overrides
            fonts = data.get('fonts', {})
            profile.headline_size = fonts.get('headline_size')
            profile.summary_size = fonts.get('summary_size')
            profile.queue_item_size = fonts.get('queue_item_size')
            profile.ticker_size = fonts.get('ticker_size')

            return profile
        except Exception as e:
            logger.error("Error loading profile %s: %s", filepath, e)
            return None

    # ------------------------------------------------------------------
    # Hot-reload
    # ------------------------------------------------------------------

    def check_for_changes(self, dt=None) -> None:
        """Check if any profile files have been modified.

        Intended to be called periodically from the game loop.
        """
        if not os.path.isdir(self.profiles_dir):
            return

        changed = False
        current_files: set = set()

        for filename in os.listdir(self.profiles_dir):
            if filename.endswith(('.yaml', '.yml')):
                filepath = os.path.join(self.profiles_dir, filename)
                current_files.add(filepath)
                mtime = os.path.getmtime(filepath)

                if filepath not in self._file_mtimes or self._file_mtimes[filepath] != mtime:
                    changed = True
                    break

        # Check for removed files
        if not changed:
            for filepath in self._file_mtimes:
                if filepath not in current_files:
                    changed = True
                    break

        if changed:
            logger.info("Profile changes detected, reloading...")
            self.load_all()
            for callback in self._on_change_callbacks:
                callback(self.profiles)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def on_profiles_changed(self, callback: Callable) -> None:
        """Register a callback invoked when profiles are reloaded.

        The callback receives a single argument: the new list of
        :class:`SourceProfile` instances.
        """
        self._on_change_callbacks.append(callback)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_enabled_profiles(self) -> List[SourceProfile]:
        """Return only enabled profiles."""
        return [p for p in self.profiles if p.enabled]
