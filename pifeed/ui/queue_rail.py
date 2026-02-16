"""Queue rail sidebar -- live queue showing previous, current, and
upcoming stories with scroll animation on story advance.

Occupies the right 30 % of the screen above the ticker bar.
"""

import pygame

from ..anim.tween import Tween, TweenGroup
from ..anim import easing


def hex_to_rgb(hex_color):
    """Convert '#RRGGBB' to an (R, G, B) tuple."""
    h = hex_color.lstrip('#')
    if len(h) == 6:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    if len(h) == 3:
        return (int(h[0] * 2, 16), int(h[1] * 2, 16), int(h[2] * 2, 16))
    return (229, 57, 53)


# ======================================================================
# QueueItemWidget
# ======================================================================

class QueueItemWidget:
    """A single row in the queue rail.

    Each item has a *role*: ``'previous'``, ``'current'``, or
    ``'upcoming'``.  The role controls visual treatment (dimming,
    highlight, arrow indicator).

    Titles are word-wrapped up to three lines to show more content.
    """

    # Left edge of text (after accent bar + arrow space)
    _TEXT_LEFT = 34
    _TEXT_RIGHT_PAD = 12

    def __init__(self, rect, font_size=22):
        self.rect = rect
        self.title_font = pygame.font.SysFont(None, font_size)
        self.label_font = pygame.font.SysFont(None, 36, bold=True)

        # Data
        self.title = ''
        self.accent_color = (229, 57, 53)
        self.role = 'upcoming'
        self.index = 0

        # Pre-rendered surfaces
        self._title_surface = None
        self._label_surface = None  # "UP NEXT" label for next_source role
        self._role_bg = None        # Cached role background surface
        self._accent_bar = None     # Cached accent bar surface

    def set_data(self, title, accent_color, index, role='upcoming'):
        """Update the item's display data and pre-render text surfaces."""
        self.title = title
        self.accent_color = accent_color
        self.index = index
        self.role = role
        self._label_surface = None

        max_w = self.rect.width - self._TEXT_LEFT - self._TEXT_RIGHT_PAD
        w, h = self.rect.width, self.rect.height

        # Pre-render role-based background and accent bar
        self._role_bg = None
        self._accent_bar = None
        r, g, b = accent_color

        if role == 'current':
            self._role_bg = pygame.Surface((w, h), pygame.SRCALPHA)
            self._role_bg.fill((r, g, b, 55))
        elif role == 'previous':
            self._role_bg = pygame.Surface((w, h), pygame.SRCALPHA)
            self._role_bg.fill((0, 0, 0, 80))
            self._accent_bar = pygame.Surface((6, h), pygame.SRCALPHA)
            self._accent_bar.fill((r, g, b, 90))
        elif role == 'next_source':
            self._role_bg = pygame.Surface((w, h), pygame.SRCALPHA)
            self._role_bg.fill((r, g, b, 25))
            self._accent_bar = pygame.Surface((6, h), pygame.SRCALPHA)
            self._accent_bar.fill((r, g, b, 140))

        if role == 'next_source':
            # "UP NEXT" label in muted white, source name in accent colour
            self._label_surface = self.label_font.render(
                'UP NEXT', True, (160, 160, 170),
            )
            self._title_surface = self.title_font.render(
                title, True, accent_color,
            ) if title else None
        else:
            text_color = (140, 140, 140) if role == 'previous' else (255, 255, 255)
            self._title_surface = self._render_wrapped(
                self.title_font, title, text_color, max_w, max_lines=3,
            )

    @staticmethod
    def _render_wrapped(font, text, color, max_width, max_lines=3):
        """Word-wrap *text* into up to *max_lines* and return a surface."""
        if not text:
            return None

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
        total_h = line_height * len(lines)
        surf = pygame.Surface((max_width, total_h), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            rendered = font.render(line, True, color)
            surf.blit(rendered, (0, i * line_height))
        return surf

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """No per-frame animation (scroll is handled by QueueRailWidget)."""

    def draw(self, surface, y_offset=0):
        """Draw this queue item onto *surface*."""
        x = self.rect.x
        y = self.rect.y + y_offset
        w, h = self.rect.width, self.rect.height

        # --- Role-based background (cached in set_data) ---
        if self._role_bg:
            surface.blit(self._role_bg, (x, y))

        # --- Accent bar on the left edge ---
        if self.role == 'current':
            pygame.draw.rect(surface, self.accent_color, (x, y, 8, h))
        elif self._accent_bar:
            surface.blit(self._accent_bar, (x, y))
        elif self.role == 'upcoming':
            pygame.draw.rect(surface, self.accent_color, (x, y, 6, h))

        # --- Arrow indicator for the current item ---
        if self.role == 'current':
            arrow_x = x + 16
            arrow_cy = y + h // 2
            pygame.draw.polygon(surface, (255, 255, 255), [
                (arrow_x, arrow_cy - 9),
                (arrow_x + 11, arrow_cy),
                (arrow_x, arrow_cy + 9),
            ])

        # --- Separator line at the bottom ---
        pygame.draw.line(surface, (50, 50, 65),
                         (x, y + h - 1), (x + w, y + h - 1))

        # --- Content ---
        tx = x + self._TEXT_LEFT

        if self.role == 'next_source':
            # Two-line layout: "UP NEXT" label + source name
            total_h = 0
            if self._label_surface:
                total_h += self._label_surface.get_height() + 4
            if self._title_surface:
                total_h += self._title_surface.get_height()
            top_y = y + (h - total_h) // 2
            if self._label_surface:
                surface.blit(self._label_surface, (tx, top_y))
                top_y += self._label_surface.get_height() + 4
            if self._title_surface:
                surface.blit(self._title_surface, (tx, top_y))
        elif self._title_surface:
            ty = y + (h - self._title_surface.get_height()) // 2
            surface.blit(self._title_surface, (tx, ty))


# ======================================================================
# SourceIndicator
# ======================================================================

class SourceIndicator:
    """Shows the current source name and three progress bars:

    1. Stories — progress through the current source's items.
    2. Story timer — countdown for the current item.
    3. Sources — progress through all enabled sources.
    """

    def __init__(self, rect, font_size=26):
        self.rect = rect
        self.name_font = pygame.font.SysFont(None, font_size, bold=True)
        self.progress_font = pygame.font.SysFont(None, 20)

        self.source_name = 'Loading...'
        self.accent_color = (229, 57, 53)

        # Story-in-source progress
        self.item_current = 0
        self.item_total = 0

        # Source rotation progress
        self.source_current = 0
        self.source_total = 0

        # Story countdown timer (resets each story change)
        self._story_elapsed = 0.0
        self._story_duration = 12.0

        # Cached surfaces
        self._name_surface = None
        self._items_label = None
        self._sources_label = None
        self._bg_surface = None
        self._timer_label = None
        self._last_timer_secs = -1

    def update_data(self, name, item_current, item_total, accent_color,
                    story_duration=12.0, source_current=1, source_total=1):
        """Update all metadata and reset the story countdown."""
        self.source_name = name
        self.item_current = item_current
        self.item_total = item_total
        self.source_current = source_current
        self.source_total = source_total
        self.accent_color = accent_color
        self._story_elapsed = 0.0
        self._story_duration = max(story_duration, 0.1)

        self._name_surface = self.name_font.render(name, True, accent_color)
        self._items_label = self.progress_font.render(
            f'{item_current}/{item_total}', True, (180, 180, 180),
        )
        self._sources_label = self.progress_font.render(
            f'{source_current}/{source_total}', True, (180, 180, 180),
        )

        # Cache background surface
        w, h = self.rect.width, self.rect.height
        self._bg_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        self._bg_surface.fill((25, 25, 38, 230))

        self._last_timer_secs = -1  # force timer label rebuild

    def update(self, dt):
        """Advance the story countdown timer."""
        self._story_elapsed = min(
            self._story_elapsed + dt, self._story_duration,
        )
        # Cache timer label — only re-render when displayed seconds change
        remaining = max(0.0, self._story_duration - self._story_elapsed)
        secs = int(remaining) + 1 if remaining > 0 else 0
        if secs != self._last_timer_secs:
            self._last_timer_secs = secs
            self._timer_label = self.progress_font.render(
                f'{secs}s', True, (180, 180, 180),
            )

    def _draw_bar(self, surface, bx, by, bw, bh, fraction, color, label=None):
        """Draw a single progress bar with optional right-aligned label."""
        pygame.draw.rect(surface, (50, 50, 65),
                         (bx, by, bw, bh), border_radius=3)
        fill_w = int(bw * max(0.0, min(1.0, fraction)))
        if fill_w > 0:
            pygame.draw.rect(surface, color,
                             (bx, by, fill_w, bh), border_radius=3)
        if label:
            surface.blit(label, (bx + bw + 8, by - 2))

    def draw(self, surface):
        """Draw the source indicator onto *surface*."""
        x, y = self.rect.x, self.rect.y
        w, h = self.rect.width, self.rect.height

        # Background (cached in update_data)
        if self._bg_surface:
            surface.blit(self._bg_surface, (x, y))

        # Source name
        if self._name_surface:
            surface.blit(self._name_surface, (x + 12, y + 8))

        bar_x = x + 12
        bar_w = w - 74
        bar_h = 7
        bar_gap = 18

        # --- Row 1: sources rotation ---
        bar_y = y + 38
        frac = self.source_current / self.source_total if self.source_total else 0
        src_color = (100, 100, 140)
        self._draw_bar(surface, bar_x, bar_y, bar_w, bar_h,
                       frac, src_color, self._sources_label)

        # --- Row 2: stories in current source ---
        bar_y += bar_gap
        frac = self.item_current / self.item_total if self.item_total else 0
        self._draw_bar(surface, bar_x, bar_y, bar_w, bar_h,
                       frac, self.accent_color, self._items_label)

        # --- Row 3: story timer (elapsed, fills left-to-right) ---
        bar_y += bar_gap
        frac = self._story_elapsed / self._story_duration
        r, g, b = self.accent_color
        timer_color = (min(255, r + 60), min(255, g + 60), min(255, b + 60))
        self._draw_bar(surface, bar_x, bar_y, bar_w, bar_h,
                       frac, timer_color, self._timer_label)


# ======================================================================
# QueueRailWidget
# ======================================================================

class QueueRailWidget:
    """Sidebar widget composing ``QueueItemWidget`` rows and a
    ``SourceIndicator``.

    When the story advances, all rows scroll upward by one row height
    over 0.4 s before settling at their final positions.
    """

    def __init__(self, rect, visible_items=5, item_font_size=34):
        self.rect = rect
        self.visible_items = visible_items

        # Layout: items take up all space except the bottom indicator
        indicator_h = 130
        self._item_h = (rect.height - indicator_h) // visible_items

        self.items = []
        for i in range(visible_items):
            item_rect = pygame.Rect(
                rect.x, rect.y + i * self._item_h, rect.width, self._item_h,
            )
            self.items.append(QueueItemWidget(item_rect, font_size=item_font_size))

        indicator_rect = pygame.Rect(
            rect.x, rect.bottom - indicator_h, rect.width, indicator_h,
        )
        self.source_indicator = SourceIndicator(indicator_rect)

        # Cached background surface
        self._bg_surface = pygame.Surface(
            (rect.width, rect.height), pygame.SRCALPHA,
        )
        self._bg_surface.fill((15, 15, 25, 242))

        # Scroll animation state
        self.tweens = TweenGroup()
        self._scroll_offset = 0.0
        self._first_update = True

    # ------------------------------------------------------------------
    # Data updates
    # ------------------------------------------------------------------

    def update_items(self, display_items, current_index=1,
                     accent_hex='#E53935',
                     next_source_name=None, next_source_hex=None):
        """Populate the queue rows from a display list.

        Args:
            display_items:    Ordered list — ``[previous, current, upcoming…]``.
            current_index:    Index of the current story in *display_items*.
            accent_hex:       Hex colour for the current source.
            next_source_name: Name of the next source (shown after last item).
            next_source_hex:  Accent hex colour of the next source.
        """
        accent = hex_to_rgb(accent_hex)
        next_source_placed = False

        for i, widget in enumerate(self.items):
            if i < len(display_items) and display_items[i] is not None:
                if i < current_index:
                    role = 'previous'
                elif i == current_index:
                    role = 'current'
                else:
                    role = 'upcoming'
                widget.set_data(
                    display_items[i].display_title, accent, i, role,
                )
            elif not next_source_placed and next_source_name:
                ns_accent = hex_to_rgb(next_source_hex or '#888888')
                widget.set_data(next_source_name, ns_accent, i, 'next_source')
                next_source_placed = True
            else:
                widget.set_data('', accent, i, 'upcoming')

        # Start scroll animation (skip on initial load)
        if not self._first_update:
            self._scroll_offset = float(self._item_h)
            self.tweens.add('scroll', Tween(
                float(self._item_h), 0.0, 0.4,
                easing.in_out_quad,
            ))
        self._first_update = False

    def update_source(self, name, current, total, accent_hex='#E53935',
                      story_duration=12.0, source_current=1, source_total=1):
        """Update the source indicator at the bottom of the rail."""
        self.source_indicator.update_data(
            name, current, total, hex_to_rgb(accent_hex),
            story_duration=story_duration,
            source_current=source_current,
            source_total=source_total,
        )

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """Advance scroll animation and child widgets."""
        self.tweens.update(dt)
        self._scroll_offset = self.tweens.get_value('scroll', 0.0)
        for item in self.items:
            item.update(dt)
        self.source_indicator.update(dt)

    def draw(self, surface):
        """Draw the full queue rail onto *surface*."""
        # Background (cached)
        surface.blit(self._bg_surface, self.rect.topleft)

        # Clip items to the area above the source indicator so that
        # items scrolling off the top do not bleed over
        old_clip = surface.get_clip()
        items_bottom = self.source_indicator.rect.y
        items_clip = pygame.Rect(
            self.rect.x, self.rect.y,
            self.rect.width, items_bottom - self.rect.y,
        )
        surface.set_clip(items_clip)

        y_offset = int(self._scroll_offset)
        for item in self.items:
            item.draw(surface, y_offset=y_offset)

        surface.set_clip(old_clip)

        # Source indicator (not affected by scroll)
        self.source_indicator.draw(surface)
