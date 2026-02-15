"""Root dashboard component that composes all UI widgets.

Calculates the screen layout from ``PiFeedConfig`` and creates:

* **HeroWidget** -- left 70 %, full height minus ticker
* **LowerThirdWidget** -- anchored to the bottom of the hero area
* **QueueRailWidget** -- right 30 %, full height minus ticker
* **TickerWidget** -- full width bar at the very bottom
* **ClockWidget** -- top-left corner over the hero area
* **DebugOverlay** -- top-right corner (togglable)

Each frame the caller invokes :meth:`update` then :meth:`draw`.
"""

import logging
import pygame

from .hero import HeroWidget
from .lower_third import LowerThirdWidget
from .queue_rail import QueueRailWidget
from .ticker import TickerWidget
from .clock_widget import ClockWidget
from .channel_badge import ChannelBadge
from .debug_overlay import DebugOverlay

logger = logging.getLogger('pifeed.ui.root')


class PiFeedRoot:
    """Root component that owns and composes every dashboard widget."""

    def __init__(self, screen_width, screen_height, config, pg_clock,
                 backgrounds_dir=None):
        """
        Args:
            screen_width:    Display width in pixels.
            screen_height:   Display height in pixels.
            config:          A ``PiFeedConfig`` instance.
            pg_clock:        A ``pygame.time.Clock`` (passed to the debug
                             overlay for FPS reporting).
            backgrounds_dir: Path to fallback background images for the hero
                             widget (``None`` to disable).
        """
        self.width = screen_width
        self.height = screen_height
        self.config = config

        # Convert the theme background (floats 0..1) to 8-bit RGB
        self.bg_color = (
            int(config.theme.background_color[0] * 255),
            int(config.theme.background_color[1] * 255),
            int(config.theme.background_color[2] * 255),
        )

        # ------------------------------------------------------------------
        # Layout rectangles
        # ------------------------------------------------------------------
        ticker_h = config.layout.ticker_height
        content_h = screen_height - ticker_h
        hero_w = int(screen_width * config.layout.hero_width_ratio)
        queue_w = screen_width - hero_w

        hero_rect = pygame.Rect(0, 0, hero_w, content_h)
        queue_rect = pygame.Rect(hero_w, 0, queue_w, content_h)
        ticker_rect = pygame.Rect(0, content_h, screen_width, ticker_h)

        # ------------------------------------------------------------------
        # Create child widgets
        # ------------------------------------------------------------------
        self.hero = HeroWidget(hero_rect, fallback_dir=backgrounds_dir)

        self.lower_third = LowerThirdWidget(
            hero_rect,
            height=config.layout.lower_third_height,
            headline_size=config.fonts.headline_size,
            summary_size=config.fonts.summary_size,
        )

        self.queue_rail = QueueRailWidget(
            queue_rect,
            visible_items=config.layout.queue_visible_items,
            item_font_size=config.fonts.queue_item_size,
        )

        self.ticker = TickerWidget(
            ticker_rect,
            font_size=config.fonts.ticker_size,
            speed=config.animation.ticker_speed,
            bg_color=(
                int(config.theme.ticker_bg_color[0] * 255),
                int(config.theme.ticker_bg_color[1] * 255),
                int(config.theme.ticker_bg_color[2] * 255),
                int(config.theme.ticker_bg_color[3] * 255),
            ),
        )

        self.clock = ClockWidget(
            x=int(screen_width * 0.01),
            y=int(content_h * 0.02),
            time_size=config.fonts.clock_time_size,
            date_size=config.fonts.clock_date_size,
        )
        self.clock.pulse_min = config.animation.live_pulse_min_opacity
        self.clock.pulse_speed = 2.0 / config.animation.live_pulse_period

        self.channel_badge = ChannelBadge(
            right_x=hero_w - int(screen_width * 0.01),
            y=int(content_h * 0.02),
        )

        # Debug overlay (created on demand)
        self.debug_overlay = None
        self._pg_clock = pg_clock

    # ------------------------------------------------------------------
    # Debug overlay management
    # ------------------------------------------------------------------

    def enable_debug_overlay(self):
        """Create and show the debug overlay."""
        if self.debug_overlay is not None:
            return
        self.debug_overlay = DebugOverlay(
            x=self.width - 190,
            y=10,
            clock_ref=self._pg_clock,
            update_interval=self.config.debug.overlay_update_interval,
        )

    def disable_debug_overlay(self):
        """Remove the debug overlay."""
        self.debug_overlay = None

    def toggle_debug_overlay(self):
        """Toggle the debug overlay on/off."""
        if self.debug_overlay is not None:
            self.disable_debug_overlay()
        else:
            self.enable_debug_overlay()

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """Advance all child widget animations by *dt* seconds.

        Does **not** advance the story sequencer (that is the caller's
        responsibility).
        """
        self.hero.update(dt)
        self.lower_third.update(dt)
        self.clock.update(dt)
        self.channel_badge.update(dt)
        self.ticker.update(dt)
        self.queue_rail.update(dt)
        if self.debug_overlay is not None:
            self.debug_overlay.update(dt)

    def draw(self, screen, sequencer, kb_transform=None):
        """Composite every widget onto *screen*.

        Args:
            screen:       The main display ``pygame.Surface``.
            sequencer:    The ``StorySequencer`` whose public state
                          attributes drive crossfade, lower-third slide,
                          and text opacity.
            kb_transform: A ``Transform(x, y, scale)`` namedtuple from
                          the Ken Burns controller (returned by
                          ``sequencer.update(dt)``).
        """
        screen.fill(self.bg_color)

        # Hero image (crossfade + Ken Burns)
        self.hero.draw(
            screen,
            crossfade=sequencer.crossfade,
            kb_transform=kb_transform,
        )

        # Lower-third banner (slide-in + text fade)
        self.lower_third.draw(
            screen,
            x_offset=sequencer.lower_third_x_offset,
            headline_opacity=sequencer.headline_opacity,
            summary_opacity=sequencer.summary_opacity,
        )

        # Queue rail sidebar
        self.queue_rail.draw(screen)

        # Ticker bar
        self.ticker.draw(screen)

        # Clock (drawn on top of the hero area, upper-left)
        self.clock.draw(screen)

        # Channel badge (upper-right of hero area)
        self.channel_badge.draw(screen)

        # Debug overlay (upper-right)
        if self.debug_overlay is not None:
            self.debug_overlay.draw(screen)
