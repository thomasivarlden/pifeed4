"""Scrolling headline ticker bar along the bottom of the screen.

Headlines are joined with a separator and rendered into a single surface
that scrolls continuously from right to left.  Two copies are drawn
side-by-side for seamless looping.
"""

import pygame

SEPARATOR = '  +++  '


class TickerWidget:
    """Horizontally scrolling ticker bar."""

    def __init__(self, rect, font_size=26, speed=80.0,
                 bg_color=(13, 13, 20, 242)):
        """
        Args:
            rect:      ``pygame.Rect`` for the ticker area.
            font_size: Headline text size.
            speed:     Scroll speed in pixels per second.
            bg_color:  ``(R, G, B, A)`` background fill colour.
        """
        self.rect = rect
        self.speed = speed
        self.bg_color = bg_color

        # Cached font (created once)
        self.font = pygame.font.SysFont(None, font_size)

        # Rendered text state
        self._text = ''
        self._text_surface = None
        self._text_width = 0

        # Cached background surface
        self._bg_surface = pygame.Surface(
            (rect.width, rect.height), pygame.SRCALPHA,
        )
        self._bg_surface.fill(bg_color)

        # Current scroll position (pixels, decreasing each frame)
        self._offset_x = 0.0

    # ------------------------------------------------------------------
    # Data update
    # ------------------------------------------------------------------

    def set_items(self, feed_items):
        """Rebuild the ticker text from a list of ``FeedItem`` objects.

        Only re-renders the text surface when the content actually changes.
        """
        if not feed_items:
            text = 'PiFeed - No stories available' + SEPARATOR
        else:
            headlines = [
                item.display_title
                for item in feed_items
                if item.display_title
            ]
            text = SEPARATOR.join(headlines) + SEPARATOR

        if text != self._text:
            first_time = self._text_surface is None
            self._text = text
            self._text_surface = self.font.render(text, True, (255, 255, 255))
            self._text_width = self._text_surface.get_width()
            if first_time:
                # Start scrolling from the right edge only on initial population
                self._offset_x = float(self.rect.width)

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """Advance the scroll position by *dt* seconds."""
        self._offset_x -= self.speed * dt
        # Wrap around when the first copy is entirely off-screen left
        if self._text_width > 0 and self._offset_x < -self._text_width:
            self._offset_x += self._text_width

    def draw(self, surface):
        """Draw the ticker bar onto *surface*."""
        # Background (cached)
        surface.blit(self._bg_surface, self.rect.topleft)

        # Top accent / separator line
        pygame.draw.line(
            surface, (75, 75, 90),
            (self.rect.x, self.rect.y),
            (self.rect.right, self.rect.y),
        )

        if not self._text_surface:
            return

        # Clip drawing to the ticker rect
        old_clip = surface.get_clip()
        surface.set_clip(self.rect)

        # Vertical centering
        y = self.rect.y + (self.rect.height - self._text_surface.get_height()) // 2
        x = self.rect.x + int(self._offset_x)

        # Draw two copies side-by-side for seamless looping
        surface.blit(self._text_surface, (x, y))
        surface.blit(self._text_surface, (x + self._text_width, y))

        surface.set_clip(old_clip)
