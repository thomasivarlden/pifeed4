"""Ken Burns effect controller.

Computes (x, y, scale) transform values over time so the UI layer can
position a scaled image with a slow pan/zoom.  Pure Python -- no
framework imports.
"""

import random
from collections import namedtuple

from .easing import linear

Transform = namedtuple('Transform', ['x', 'y', 'scale'])


class KenBurnsController:
    """Continuously generates pan/zoom transforms for an image.

    Each frame the caller invokes :meth:`update` with the delta-time
    and receives a :class:`Transform` that the rendering layer applies
    to the image surface.
    """

    def __init__(
        self,
        cycle_duration: float = 15.0,
        scale_min: float = 1.05,
        scale_max: float = 1.20,
    ):
        self.cycle_duration = cycle_duration
        self.scale_min = scale_min
        self.scale_max = scale_max
        self.active: bool = False
        self.elapsed: float = 0.0
        self._start: Transform = Transform(0, 0, 1.0)
        self._end: Transform = Transform(0, 0, 1.0)
        self._viewport: tuple[int, int] = (0, 0)
        self._image_size: tuple[int, int] = (0, 0)

    def start(self, image_size, viewport_size) -> None:
        """Begin a new Ken Burns cycle.

        Args:
            image_size: ``(width, height)`` of the source image in pixels.
            viewport_size: ``(width, height)`` of the visible area.
        """
        self._image_size = image_size
        self._viewport = viewport_size
        self._start = self._random_transform()
        self._end = self._random_transform()
        self.elapsed = 0.0
        self.active = True

    def stop(self) -> None:
        """Halt the effect.  Subsequent :meth:`update` calls return an
        identity transform."""
        self.active = False

    def update(self, dt: float) -> Transform:
        """Advance the animation by *dt* seconds and return the current
        transform.

        When a cycle completes the controller automatically chains to a
        new random endpoint so the motion never stops.
        """
        if not self.active:
            return Transform(0, 0, 1.0)

        self.elapsed += dt
        t = min(self.elapsed / self.cycle_duration, 1.0)

        x = self._start.x + (self._end.x - self._start.x) * t
        y = self._start.y + (self._end.y - self._start.y) * t
        scale = self._start.scale + (self._end.scale - self._start.scale) * t

        if t >= 1.0:
            # Seamlessly chain: current end becomes next start.
            self._start = self._end
            self._end = self._random_transform()
            self.elapsed = 0.0

        return Transform(x, y, scale)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _random_transform(self) -> Transform:
        """Generate a random pan + zoom transform.

        ``scale_min`` / ``scale_max`` express the desired zoom level
        relative to the **viewport** (e.g. 1.05 = 5 % larger than the
        viewport).  Images are pre-loaded at ~130 % of the viewport so
        ``Transform.scale`` is always ≤ 1.0, meaning the hero widget
        only ever scales *down* — which is fast and artefact-free.
        """
        # Pick a random zoom level (relative to viewport)
        target_zoom = random.uniform(self.scale_min, self.scale_max)

        vw, vh = self._viewport
        iw, ih = self._image_size

        # Convert to a render multiplier for the pre-loaded image.
        # "cover" mode: the displayed image must be at least
        # (vw * target_zoom) × (vh * target_zoom).
        render_scale = max(
            (vw * target_zoom) / iw,
            (vh * target_zoom) / ih,
        )
        # Safety: never upscale beyond the pre-loaded size
        render_scale = min(render_scale, 1.0)

        disp_w = iw * render_scale
        disp_h = ih * render_scale

        # Pan range: displayed image must cover viewport.
        max_x = 0
        min_x = -(disp_w - vw)
        max_y = 0
        min_y = -(disp_h - vh)

        if min_x > max_x:
            min_x = max_x = (vw - disp_w) / 2
        if min_y > max_y:
            min_y = max_y = (vh - disp_h) / 2

        return Transform(
            x=random.uniform(min_x, max_x),
            y=random.uniform(min_y, max_y),
            scale=render_scale,
        )
