"""Lower-third banner overlay for headline and summary text.

Positioned at the bottom of the hero area.  Slides in from the left
(controlled by ``x_offset``) and fades headline/summary independently
(controlled by opacity values from the sequencer).
"""

import pygame


def hex_to_rgb(hex_color):
    """Convert '#RRGGBB' to an (R, G, B) tuple."""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    if len(h) == 3:
        return (int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16))
    return (229, 57, 53)  # fallback red


class LowerThirdWidget:
    """Lower-third banner with headline and summary drawn at the bottom
    of the hero area."""

    def __init__(self, hero_rect, height=180, headline_size=42, summary_size=28):
        """
        Args:
            hero_rect:     ``pygame.Rect`` of the hero area (banner anchors
                           to its bottom edge).
            height:        Pixel height of the banner.
            headline_size: Font point size for headline text.
            summary_size:  Font point size for summary text.
        """
        self.hero_rect = hero_rect
        self.height = height

        # Cached font objects
        self.headline_font = pygame.font.SysFont(None, headline_size, bold=True)
        self.summary_font = pygame.font.SysFont(None, summary_size)

        # Current content
        self.headline_text = ''
        self.summary_text = ''
        self.accent_color = (229, 57, 53)

        # Pre-rendered text surfaces (rebuilt in set_content)
        self._headline_surface = None
        self._summary_surface = None
        self._bg_surface = None

    # ------------------------------------------------------------------
    # Content management
    # ------------------------------------------------------------------

    def set_content(self, headline, summary, accent_hex='#E53935'):
        """Update the banner text and accent colour.

        Pre-renders word-wrapped text surfaces so draw() is cheap.
        """
        self.headline_text = headline or ''
        self.summary_text = summary or ''
        self.accent_color = hex_to_rgb(accent_hex)

        # Pre-render background surface (accent-tinted with left bar)
        banner_w = self.hero_rect.width
        self._bg_surface = pygame.Surface((banner_w, self.height), pygame.SRCALPHA)
        r, g, b = self.accent_color
        self._bg_surface.fill((int(r * 0.3), int(g * 0.3), int(b * 0.3), 216))
        pygame.draw.rect(self._bg_surface, (*self.accent_color, 255),
                         (0, 0, 8, self.height))

        max_text_width = self.hero_rect.width - 64  # 32 px padding each side

        if self.headline_text:
            self._headline_surface = self._render_wrapped(
                self.headline_font, self.headline_text,
                (255, 255, 255), max_text_width, max_lines=3,
            )
        else:
            self._headline_surface = None

        if self.summary_text:
            self._summary_surface = self._render_wrapped(
                self.summary_font, self.summary_text,
                (230, 230, 230), max_text_width, max_lines=6,
            )
        else:
            self._summary_surface = None

    # ------------------------------------------------------------------
    # Text wrapping
    # ------------------------------------------------------------------

    def _render_wrapped(self, font, text, color, max_width, max_lines=2):
        """Word-wrap *text* and return a single ``pygame.Surface``.

        Truncates with an ellipsis when *max_lines* is exceeded.
        Returns ``None`` if the text is empty after processing.
        """
        words = text.split()
        if not words:
            return None

        lines = []
        current_line = ''

        for word in words:
            test = current_line + (' ' if current_line else '') + word
            if font.size(test)[0] <= max_width:
                current_line = test
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
                if len(lines) >= max_lines:
                    # Truncate the last line with an ellipsis
                    last = lines[-1]
                    while last and font.size(last + '...')[0] > max_width:
                        last = last[:-1]
                    lines[-1] = last.rstrip() + '...'
                    current_line = ''
                    break

        if current_line and len(lines) < max_lines:
            lines.append(current_line)

        if not lines:
            return None

        line_height = font.get_linesize()
        total_height = line_height * len(lines)
        surf = pygame.Surface((max_width, total_height), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            rendered = font.render(line, True, color)
            surf.blit(rendered, (0, i * line_height))
        return surf

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """Lower-third has no independent animation (driven by sequencer
        values passed to draw)."""

    def draw(self, surface, x_offset=0, headline_opacity=1.0, summary_opacity=1.0):
        """Draw the lower-third banner.

        Args:
            surface:          Target surface (screen).
            x_offset:         Horizontal offset in pixels for slide-in
                              (``0`` = fully visible, ``-500`` = off-screen).
            headline_opacity: ``0.0`` .. ``1.0`` fade for headline text.
            summary_opacity:  ``0.0`` .. ``1.0`` fade for summary text.
        """
        if not self._bg_surface:
            return

        banner_x = self.hero_rect.x + int(x_offset)
        banner_y = self.hero_rect.bottom - self.height

        # Cached background surface
        surface.blit(self._bg_surface, (banner_x, banner_y))

        # -- Text --
        text_x = banner_x + 32
        text_y = banner_y + 20

        # Headline (set_alpha + restore avoids expensive .copy())
        if self._headline_surface and headline_opacity > 0.0:
            self._headline_surface.set_alpha(int(255 * headline_opacity))
            surface.blit(self._headline_surface, (text_x, text_y))
            self._headline_surface.set_alpha(255)
            text_y += self._headline_surface.get_height() + 12

        # Summary
        if self._summary_surface and summary_opacity > 0.0:
            self._summary_surface.set_alpha(int(255 * summary_opacity))
            surface.blit(self._summary_surface, (text_x, text_y))
            self._summary_surface.set_alpha(255)
