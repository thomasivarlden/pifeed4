"""Story sequencer -- orchestrates the full transition timeline.

Manages named state values that the UI layer reads each frame:

* ``crossfade``            -- 0.0 (old image) to 1.0 (new image)
* ``lower_third_x_offset`` -- slides from off-screen (-500) to 0
* ``headline_opacity``     -- 0.0 to 1.0
* ``summary_opacity``      -- 0.0 to 1.0

The Ken Burns transform is returned from :meth:`update`.

Phase timeline
--------------
t = 0.0 s  Start crossfade (0 -> 1 over crossfade_duration)
t ~ 0.8 s  Crossfade done -> slide in lower third (out_back)
t ~ 1.4 s  Lower third in -> headline fade
t ~ 1.8+s  After summary_delay -> summary fade

Pure Python -- no framework imports.
"""

from __future__ import annotations

from .tween import Tween, TweenGroup
from .ken_burns import KenBurnsController, Transform
from . import easing


class StorySequencer:
    """Drives one story-transition using frame-based tweens.

    The caller must invoke :meth:`update` every frame with the
    delta-time and read the public state attributes to position UI
    elements.
    """

    def __init__(self, config):
        """
        Args:
            config: An ``AnimConfig`` instance (or compatible object)
                    exposing timing fields such as ``crossfade_duration``,
                    ``ken_burns_cycle``, etc.
        """
        self.config = config
        self.tweens = TweenGroup()
        self.ken_burns = KenBurnsController(
            cycle_duration=config.ken_burns_cycle,
            scale_min=config.ken_burns_scale_min,
            scale_max=config.ken_burns_scale_max,
        )

        self._phase: str = 'idle'
        self._phase_timer: float = 0.0
        self._crossfade_done: bool = False
        self._slide_done: bool = False
        self._headline_done: bool = False

        # ------------------------------------------------------------------
        # Public state -- the UI reads these each frame.
        # ------------------------------------------------------------------
        self.crossfade: float = 0.0
        self.lower_third_x_offset: float = -500  # pixels off-screen left
        self.headline_opacity: float = 0.0
        self.summary_opacity: float = 0.0
        self.transitioning: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play(self, image_size, viewport_size) -> None:
        """Kick off the full story-transition sequence.

        Args:
            image_size: ``(w, h)`` of the new hero image.
            viewport_size: ``(w, h)`` of the hero display area.
        """
        self.cancel()
        self.transitioning = True
        self._phase = 'crossfade'
        self._crossfade_done = False
        self._slide_done = False
        self._headline_done = False

        # Slide distance: full viewport width so the lower third
        # starts completely off-screen to the left.
        self._slide_start = -viewport_size[0]

        # Reset state values to starting positions.
        self.crossfade = 0.0
        self.lower_third_x_offset = self._slide_start
        self.headline_opacity = 0.0
        self.summary_opacity = 0.0

        # Phase 1 -- crossfade
        self.tweens.add('crossfade', Tween(
            0.0, 1.0,
            self.config.crossfade_duration,
            easing.in_out_quad,
            on_complete=self._on_crossfade_done,
        ))

        # Start Ken Burns on the new image.
        self.ken_burns.start(image_size, viewport_size)

    def update(self, dt: float) -> Transform:
        """Advance every active tween by *dt* seconds.

        Returns:
            The current :class:`~ken_burns.Transform` for the hero
            image (x, y, scale).
        """
        self.tweens.update(dt)

        # Sync public state from tweens (keep last value if tween removed).
        self.crossfade = self.tweens.get_value('crossfade', self.crossfade)
        self.lower_third_x_offset = self.tweens.get_value(
            'lower_third_x', self.lower_third_x_offset,
        )
        self.headline_opacity = self.tweens.get_value(
            'headline', self.headline_opacity,
        )
        self.summary_opacity = self.tweens.get_value(
            'summary', self.summary_opacity,
        )

        # Delayed summary phase -- wait for summary_delay after headline.
        if self._phase == 'waiting_summary':
            self._phase_timer += dt
            if self._phase_timer >= self.config.summary_delay:
                self.tweens.add('summary', Tween(
                    0.0, 1.0,
                    self.config.summary_fade_duration,
                    easing.in_out_quad,
                    on_complete=self._on_all_done,
                ))
                self._phase = 'summary'

        # Ken Burns runs independently.
        return self.ken_burns.update(dt)

    def cancel(self) -> None:
        """Cancel all tweens and stop Ken Burns."""
        self.tweens.cancel()
        self.ken_burns.stop()
        self.transitioning = False
        self._phase = 'idle'

    def stop(self) -> None:
        """Alias for :meth:`cancel`."""
        self.cancel()

    # ------------------------------------------------------------------
    # Phase callbacks (chained via Tween.on_complete)
    # ------------------------------------------------------------------

    def _on_crossfade_done(self) -> None:
        self._crossfade_done = True
        # Phase 2 -- slide in lower third
        self.tweens.add('lower_third_x', Tween(
            self._slide_start, 0,
            self.config.lower_third_slide_duration,
            easing.out_quad,
            on_complete=self._on_slide_done,
        ))

    def _on_slide_done(self) -> None:
        self._slide_done = True
        # Phase 3 -- headline fade in
        self.tweens.add('headline', Tween(
            0.0, 1.0,
            self.config.headline_fade_duration,
            easing.in_out_quad,
            on_complete=self._on_headline_done,
        ))

    def _on_headline_done(self) -> None:
        self._headline_done = True
        self._phase_timer = 0.0
        self._phase = 'waiting_summary'

    def _on_all_done(self) -> None:
        self.transitioning = False
        self._phase = 'idle'
