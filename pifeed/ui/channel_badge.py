"""Channel name badge displayed in the upper-right of the hero area.

Shows the current source/channel name in a styled pill with the
source's accent colour, mirroring the clock widget on the left.
"""

import pygame


def hex_to_rgb(hex_color):
    h = hex_color.lstrip('#')
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    if len(h) == 3:
        return (int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16))
    return (229, 57, 53)


class ChannelBadge:
    """Accent-coloured pill showing the current channel/source name."""

    def __init__(self, right_x, y, font_size=38):
        """
        Args:
            right_x: Right edge x-coordinate (badge is right-aligned).
            y:       Top y-coordinate (same row as the clock).
            font_size: Font size for the channel name.
        """
        self._right_x = right_x
        self._y = y

        self._name_font = pygame.font.SysFont(None, font_size, bold=True)
        self._label_font = pygame.font.SysFont(None, 20)

        self._name = ''
        self._accent = (229, 57, 53)
        self._name_surface = None
        self._label_surface = self._label_font.render(
            'CHANNEL', True, (180, 180, 190),
        )

    def set_source(self, name, accent_hex='#E53935'):
        """Update the displayed channel name and accent colour."""
        accent = hex_to_rgb(accent_hex)
        if name == self._name and accent == self._accent:
            return
        self._name = name
        self._accent = accent
        self._name_surface = self._name_font.render(
            name.upper(), True, (255, 255, 255),
        )

    def update(self, dt):
        pass

    def draw(self, surface):
        if not self._name_surface:
            return

        pad_x = 16
        pad_y = 8
        gap = 2

        label_w = self._label_surface.get_width()
        label_h = self._label_surface.get_height()
        name_w = self._name_surface.get_width()
        name_h = self._name_surface.get_height()

        content_w = max(label_w, name_w)
        content_h = label_h + gap + name_h
        pill_w = content_w + pad_x * 2 + 6  # 6 for accent bar
        pill_h = content_h + pad_y * 2

        pill_x = self._right_x - pill_w
        pill_y = self._y

        # Background pill
        bg = pygame.Surface((pill_w, pill_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 120),
                         (0, 0, pill_w, pill_h), border_radius=6)
        surface.blit(bg, (pill_x, pill_y))

        # Accent bar on the right edge
        bar = pygame.Surface((6, pill_h), pygame.SRCALPHA)
        bar.fill((*self._accent, 230))
        surface.blit(bar, (pill_x + pill_w - 6, pill_y))

        # "CHANNEL" label
        lx = pill_x + pad_x
        ly = pill_y + pad_y
        surface.blit(self._label_surface, (lx, ly))

        # Source name
        ny = ly + label_h + gap
        surface.blit(self._name_surface, (lx, ny))
