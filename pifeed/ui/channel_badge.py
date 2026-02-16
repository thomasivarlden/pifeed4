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
        # Cached composite surfaces (rebuilt in set_source)
        self._pill_bg = None
        self._accent_bar_surf = None
        self._pill_w = 0
        self._pill_h = 0

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

        # Pre-compute pill dimensions and cache surfaces
        pad_x, pad_y, gap = 16, 8, 2
        label_w = self._label_surface.get_width()
        label_h = self._label_surface.get_height()
        name_w = self._name_surface.get_width()
        name_h = self._name_surface.get_height()
        content_w = max(label_w, name_w)
        content_h = label_h + gap + name_h
        self._pill_w = content_w + pad_x * 2 + 6
        self._pill_h = content_h + pad_y * 2

        self._pill_bg = pygame.Surface(
            (self._pill_w, self._pill_h), pygame.SRCALPHA,
        )
        pygame.draw.rect(self._pill_bg, (0, 0, 0, 120),
                         (0, 0, self._pill_w, self._pill_h), border_radius=6)

        self._accent_bar_surf = pygame.Surface(
            (6, self._pill_h), pygame.SRCALPHA,
        )
        self._accent_bar_surf.fill((*self._accent, 230))

    def update(self, dt):
        pass

    def draw(self, surface):
        if not self._name_surface or not self._pill_bg:
            return

        pill_x = self._right_x - self._pill_w
        pill_y = self._y

        # Cached background pill and accent bar
        surface.blit(self._pill_bg, (pill_x, pill_y))
        surface.blit(self._accent_bar_surf,
                     (pill_x + self._pill_w - 6, pill_y))

        # "CHANNEL" label
        lx = pill_x + 16
        ly = pill_y + 8
        surface.blit(self._label_surface, (lx, ly))

        # Source name
        label_h = self._label_surface.get_height()
        ny = ly + label_h + 2
        surface.blit(self._name_surface, (lx, ny))
