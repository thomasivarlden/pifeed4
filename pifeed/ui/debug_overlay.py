"""Debug overlay showing FPS, frame time, and memory usage.

Draws a small semi-transparent panel in the corner of the screen.
Statistics are refreshed at a configurable interval (default 0.5 s)
to avoid per-frame string formatting overhead.
"""

import os
import pygame


class DebugOverlay:
    """FPS / frame-time / memory diagnostic overlay."""

    def __init__(self, x, y, clock_ref, update_interval=0.5):
        """
        Args:
            x:               Horizontal position on screen.
            y:               Vertical position on screen.
            clock_ref:       A ``pygame.time.Clock`` whose ``get_fps()``
                             method returns the current frame rate.
            update_interval: Seconds between stat refreshes.
        """
        self.x = x
        self.y = y
        self.clock_ref = clock_ref
        self.update_interval = update_interval

        # Cached font (created once)
        self.font = pygame.font.SysFont('monospace', 14)

        # Refresh timer
        self._timer = 0.0

        # Raw stat strings (updated periodically)
        self._fps_text = 'FPS: --'
        self._frame_text = 'Frame: --ms'
        self._mem_text = 'Mem: --MB'

        # Pre-rendered text surfaces (list of surfaces, rebuilt on refresh)
        self._surfaces = []

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """Refresh statistics every ``update_interval`` seconds."""
        self._timer += dt
        if self._timer < self.update_interval:
            return
        self._timer = 0.0

        fps = self.clock_ref.get_fps()
        self._fps_text = f'FPS: {fps:.1f}'

        frame_ms = (1000.0 / fps) if fps > 0 else 0.0
        self._frame_text = f'Frame: {frame_ms:.1f}ms'

        try:
            import psutil
            mem_mb = psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
            self._mem_text = f'Mem: {mem_mb:.1f}MB'
        except ImportError:
            try:
                import resource
                # macOS returns bytes; Linux returns kilobytes
                rusage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                # On macOS ru_maxrss is in bytes
                import sys
                if sys.platform == 'darwin':
                    mem_mb = rusage / (1024 * 1024)
                else:
                    mem_mb = rusage / 1024
                self._mem_text = f'Mem: {mem_mb:.1f}MB'
            except Exception:
                self._mem_text = 'Mem: N/A'

        # Re-render text surfaces
        self._surfaces = [
            self.font.render(self._fps_text, True, (0, 255, 0)),
            self.font.render(self._frame_text, True, (200, 200, 0)),
            self.font.render(self._mem_text, True, (128, 200, 255)),
        ]

    def draw(self, surface):
        """Draw the overlay panel onto *surface*."""
        if not self._surfaces:
            return

        panel_w = 180
        panel_h = 70
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 153),
                         (0, 0, panel_w, panel_h), border_radius=6)
        surface.blit(bg, (self.x, self.y))

        y = self.y + 6
        for surf in self._surfaces:
            surface.blit(surf, (self.x + 8, y))
            y += 20
