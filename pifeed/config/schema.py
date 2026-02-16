"""Configuration schema for PiFeed4.

Defines all configuration dataclasses with sensible defaults for the
Kivy-based news dashboard.
"""

from dataclasses import dataclass, field
from typing import List, Optional


def hex_to_rgba(hex_color: str) -> List[float]:
    """Convert a hex color string (e.g. '#E53935' or '#E53935FF') to an RGBA list.

    Accepts 3-digit (#RGB), 6-digit (#RRGGBB), and 8-digit (#RRGGBBAA) hex
    strings, with or without the leading '#'. If no alpha component is given,
    alpha defaults to 1.0.
    """
    color = hex_color.lstrip('#')

    if len(color) == 3:
        r = int(color[0] * 2, 16) / 255.0
        g = int(color[1] * 2, 16) / 255.0
        b = int(color[2] * 2, 16) / 255.0
        a = 1.0
    elif len(color) == 6:
        r = int(color[0:2], 16) / 255.0
        g = int(color[2:4], 16) / 255.0
        b = int(color[4:6], 16) / 255.0
        a = 1.0
    elif len(color) == 8:
        r = int(color[0:2], 16) / 255.0
        g = int(color[2:4], 16) / 255.0
        b = int(color[4:6], 16) / 255.0
        a = int(color[6:8], 16) / 255.0
    else:
        raise ValueError(f"Invalid hex color: {hex_color}")

    return [r, g, b, a]


# ---------------------------------------------------------------------------
# Section configs
# ---------------------------------------------------------------------------

@dataclass
class AppConfig:
    """Top-level application settings."""
    mode: str = 'production'       # 'production' or 'debug'
    demo: bool = False
    profiles_dir: str = 'profiles'
    cache_dir: str = 'cache'
    backgrounds_dir: str = 'backgrounds'
    log_level: str = 'INFO'


@dataclass
class WindowConfig:
    """Kivy window / display settings."""
    width: int = 1920
    height: int = 1080
    fullscreen: bool = True
    title: str = 'PiFeed'
    target_fps: int = 30


@dataclass
class LayoutConfig:
    """Proportions and sizing for the dashboard layout."""
    hero_width_ratio: float = 0.70
    queue_width_ratio: float = 0.30
    ticker_height: int = 48
    lower_third_height: int = 180
    queue_visible_items: int = 6


@dataclass
class AnimConfig:
    """Animation durations, easings, and parameters."""
    crossfade_duration: float = 0.8
    ken_burns_cycle: float = 15.0
    ken_burns_scale_min: float = 1.05
    ken_burns_scale_max: float = 1.20
    lower_third_slide_duration: float = 0.6
    lower_third_easing: str = 'out_back'
    headline_stagger_delay: float = 0.15
    headline_fade_duration: float = 0.4
    summary_delay: float = 0.8
    summary_fade_duration: float = 0.5
    queue_shift_duration: float = 0.4
    queue_pulse_period: float = 2.0
    ticker_speed: float = 80.0
    live_pulse_period: float = 2.0
    live_pulse_min_opacity: float = 0.3


@dataclass
class TimingConfig:
    """Story rotation and feed refresh timing."""
    story_duration: float = 12.0
    items_per_source: int = 10
    feed_refresh_interval: int = 3600


@dataclass
class FontConfig:
    """Font sizes for each text element."""
    headline_size: int = 42
    summary_size: int = 28
    queue_item_size: int = 22
    ticker_size: int = 26
    clock_time_size: int = 36
    clock_date_size: int = 20


@dataclass
class ThemeConfig:
    """Colors and visual theming."""
    background_color: List[float] = field(
        default_factory=lambda: [0.08, 0.08, 0.12, 1.0]
    )
    lower_third_bg_opacity: float = 0.85
    queue_bg_color: List[float] = field(
        default_factory=lambda: [0.06, 0.06, 0.10, 0.95]
    )
    ticker_bg_color: List[float] = field(
        default_factory=lambda: [0.05, 0.05, 0.08, 0.95]
    )
    text_color: List[float] = field(
        default_factory=lambda: [1.0, 1.0, 1.0, 1.0]
    )
    text_secondary_color: List[float] = field(
        default_factory=lambda: [0.8, 0.8, 0.8, 1.0]
    )
    default_accent_color: str = '#E53935'


@dataclass
class CacheConfig:
    """Image and feed caching limits."""
    max_size_mb: int = 100
    image_timeout: int = 10
    feed_timeout: int = 15


@dataclass
class DebugConfig:
    """Debug overlay and diagnostic settings."""
    show_overlay: bool = True
    overlay_update_interval: float = 0.5
    show_fps: bool = True
    show_frame_time: bool = True
    show_memory: bool = True


# ---------------------------------------------------------------------------
# Root config
# ---------------------------------------------------------------------------

@dataclass
class PiFeedConfig:
    """Root configuration container that holds every section."""
    app: AppConfig = field(default_factory=AppConfig)
    window: WindowConfig = field(default_factory=WindowConfig)
    layout: LayoutConfig = field(default_factory=LayoutConfig)
    animation: AnimConfig = field(default_factory=AnimConfig)
    timing: TimingConfig = field(default_factory=TimingConfig)
    fonts: FontConfig = field(default_factory=FontConfig)
    theme: ThemeConfig = field(default_factory=ThemeConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)


# ---------------------------------------------------------------------------
# Source profile
# ---------------------------------------------------------------------------

@dataclass
class SourceProfile:
    """Per-source configuration loaded from a profile YAML file.

    Optional fields (set to ``None``) fall back to the corresponding global
    setting in :class:`PiFeedConfig`.
    """
    name: str = ''
    feed_url: str = ''
    enabled: bool = True
    is_demo: bool = False
    refresh_interval: Optional[int] = None    # Override global
    story_duration: Optional[float] = None    # Override global
    items_limit: Optional[int] = None         # Override global
    accent_color: str = '#E53935'
    headline_size: Optional[int] = None
    summary_size: Optional[int] = None
    queue_item_size: Optional[int] = None
    ticker_size: Optional[int] = None
