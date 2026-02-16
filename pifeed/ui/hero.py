"""Hero image widget with double-buffered crossfade and Ken Burns support.

The hero area occupies approximately 70 % of the screen width (left side).
Images are loaded into a back buffer and crossfaded to the front buffer.
Ken Burns panning/zooming is applied by positioning an oversized image
within the hero rect using the Transform(x, y, scale) values from the
animation system.
"""

import os
import logging
import random
import pygame

logger = logging.getLogger('pifeed.ui.hero')

_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')


class HeroWidget:
    """Hero image area with double-buffered images for crossfade + Ken Burns."""

    def __init__(self, rect, fallback_dir=None):
        """
        Args:
            rect:         ``pygame.Rect`` defining the hero area on screen.
            fallback_dir: Path to a directory of background images used when
                          a story has no image.  ``None`` disables fallbacks.
        """
        self.rect = rect
        self._front_image = None   # pygame.Surface (pre-scaled for KB)
        self._back_image = None    # pygame.Surface (pre-scaled for KB)
        self._front_source = ''
        self._back_source = ''
        self._fallback_paths = self._scan_fallbacks(fallback_dir)
        self._last_fallback = None
        self._placeholder = self._make_placeholder()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _scan_fallbacks(fallback_dir):
        """Return a sorted list of image paths found in *fallback_dir*."""
        if not fallback_dir or not os.path.isdir(fallback_dir):
            return []
        paths = [
            os.path.join(fallback_dir, f)
            for f in sorted(os.listdir(fallback_dir))
            if os.path.splitext(f)[1].lower() in _IMAGE_EXTENSIONS
        ]
        return paths

    def _pick_fallback(self):
        """Pick a random fallback background, avoiding the same one twice in a row."""
        if not self._fallback_paths:
            return None
        candidates = [p for p in self._fallback_paths if p != self._last_fallback]
        if not candidates:
            candidates = self._fallback_paths
        choice = random.choice(candidates)
        self._last_fallback = choice
        return choice

    def _make_placeholder(self):
        """Create a dark placeholder surface matching the hero rect size."""
        s = pygame.Surface((self.rect.width, self.rect.height))
        s.fill((20, 20, 30))
        return s

    def _load_and_scale(self, image_path):
        """Load an image and scale it to cover the hero area with 30 %
        oversize for Ken Burns headroom.  Returns a ``pygame.Surface``
        or ``None`` on failure."""
        try:
            img = pygame.image.load(image_path).convert()
        except Exception as exc:
            logger.warning("Failed to load image %s: %s", image_path, exc)
            return None

        # Target dimensions with 20 % oversize for Ken Burns headroom
        target_w = int(self.rect.width * 1.2)
        target_h = int(self.rect.height * 1.2)

        # Scale to *cover* the target (no letterboxing)
        iw, ih = img.get_size()
        scale = max(target_w / iw, target_h / ih)
        new_w = int(iw * scale)
        new_h = int(ih * scale)
        return pygame.transform.smoothscale(img, (new_w, new_h))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_image(self, image_path):
        """Load a new image into the back buffer for crossfade.

        Args:
            image_path: Local filesystem path, or ``None``/empty for the
                        dark placeholder.
        """
        if image_path and os.path.exists(image_path):
            result = self._load_and_scale(image_path)
            if result is not None:
                self._back_image = result
                self._back_source = image_path
                return
        # Fallback: try a random background image from the backgrounds folder
        fallback = self._pick_fallback()
        if fallback:
            result = self._load_and_scale(fallback)
            if result is not None:
                self._back_image = result
                self._back_source = fallback
                return
        # Last resort: solid dark placeholder
        self._back_image = self._placeholder.copy()
        self._back_source = ''

    def swap_buffers(self):
        """Promote the back buffer to front.  Called after a crossfade
        completes so the new image becomes the persistent display."""
        self._front_image = self._back_image
        self._front_source = self._back_source

    def get_image_size(self):
        """Return ``(width, height)`` of the back buffer image.

        Used by the Ken Burns controller to compute pan limits.
        """
        if self._back_image:
            return self._back_image.get_size()
        return (self.rect.width, self.rect.height)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def update(self, dt):
        """Hero has no per-frame animation of its own (Ken Burns is
        external), but the method exists for interface consistency."""

    def draw(self, surface, crossfade=0.0, kb_transform=None):
        """Draw the hero image area onto *surface*.

        Args:
            surface:      The main screen surface.
            crossfade:    ``0.0`` = front buffer only, ``1.0`` = back buffer
                          only.  Values in between blend both.
            kb_transform: A ``Transform(x, y, scale)`` namedtuple from the
                          Ken Burns controller, applied only to the fully
                          visible buffer (back during crossfade == 1.0,
                          front otherwise).
        """
        old_clip = surface.get_clip()
        surface.set_clip(self.rect)

        # Dark background (visible if no images loaded)
        surface.fill((20, 20, 30), self.rect)

        if 0.0 < crossfade < 1.0:
            # --- Mid-crossfade: blend front (fading out) and back (fading in) ---
            # Images are .convert() (no per-pixel alpha), so set_alpha()
            # is non-destructive and we can avoid expensive .copy() calls.
            if self._front_image:
                self._front_image.set_alpha(int(255 * (1.0 - crossfade)))
                self._blit_centered(surface, self._front_image, None)
                self._front_image.set_alpha(255)
            if self._back_image:
                self._back_image.set_alpha(int(255 * crossfade))
                self._blit_centered(surface, self._back_image, None)
                self._back_image.set_alpha(255)
        elif crossfade >= 1.0:
            # Crossfade complete -- show back buffer with Ken Burns
            img = self._back_image or self._placeholder
            self._blit_centered(surface, img, kb_transform)
        else:
            # Normal display -- show front buffer with Ken Burns
            img = self._front_image or self._placeholder
            self._blit_centered(surface, img, kb_transform)

        surface.set_clip(old_clip)

    def _blit_centered(self, surface, image, kb_transform):
        """Blit *image* into the hero rect, centered, with optional
        Ken Burns pan + zoom.

        ``Transform.scale`` is a render multiplier (≤ 1.0) that scales
        the pre-loaded image *down* to achieve the desired zoom level.
        ``x`` and ``y`` are pixel offsets computed for the scaled size.
        """
        iw, ih = image.get_size()

        if kb_transform:
            s = kb_transform.scale
            if s < 1.0:
                new_w = int(iw * s)
                new_h = int(ih * s)
                image = pygame.transform.scale(image, (new_w, new_h))
                iw, ih = new_w, new_h
            x = self.rect.x + int(kb_transform.x)
            y = self.rect.y + int(kb_transform.y)
        else:
            # No Ken Burns -- just center the (oversized) image.
            x = self.rect.x - (iw - self.rect.width) // 2
            y = self.rect.y - (ih - self.rect.height) // 2

        surface.blit(image, (x, y))
