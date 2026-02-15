"""PiFeed4 configuration package.

Public API:
    - Schema dataclasses (PiFeedConfig, SourceProfile, etc.)
    - hex_to_rgba helper
    - load_config loader
    - ProfileManager for source profiles
"""

from .schema import (
    AnimConfig,
    AppConfig,
    CacheConfig,
    DebugConfig,
    FontConfig,
    LayoutConfig,
    PiFeedConfig,
    SourceProfile,
    ThemeConfig,
    TimingConfig,
    WindowConfig,
    hex_to_rgba,
)
from .loader import deep_merge, load_config
from .profiles import ProfileManager

__all__ = [
    'AnimConfig',
    'AppConfig',
    'CacheConfig',
    'DebugConfig',
    'FontConfig',
    'LayoutConfig',
    'PiFeedConfig',
    'ProfileManager',
    'SourceProfile',
    'ThemeConfig',
    'TimingConfig',
    'WindowConfig',
    'deep_merge',
    'hex_to_rgba',
    'load_config',
]
