"""Clock widget with time, date, and pulsing LIVE indicator.

Renders into the parent surface at the configured (x, y) position.
All Font objects are cached at construction time.
"""

import math
import pygame
from datetime import datetime


class ClockWidget:
    """Displays current time, date, and a pulsing LIVE indicator."""

    def __init__(self, x, y, time_size=36, date_size=20):
        self.x = x
        self.y = y

        # Cached font objects (created once)
        self.time_font = pygame.font.SysFont('courier', time_size, bold=True)
        self.date_font = pygame.font.SysFont(None, date_size)
        self.live_font = pygame.font.SysFont(None, 14, bold=True)

        # Cached text surfaces (re-rendered only when text changes)
        self._time_text = ''
        self._date_text = ''
        self._time_surface = None
        self._date_surface = None

        # Clock update timer -- refreshes once per second
        self._update_timer = 0.0

        # LIVE pulse state (sinusoidal 0..1 mapped to opacity)
        self._pulse_phase = 0.0
        self.pulse_min = 0.3
        self.pulse_speed = 1.0  # full cycle = 2.0 / pulse_speed seconds

    # ------------------------------------------------------------------
    # Frame callbacks
    # ------------------------------------------------------------------

    def update(self, dt):
        """Advance clock and pulse animation by *dt* seconds."""
        # Refresh the time/date text every second
        self._update_timer += dt
        if self._update_timer >= 1.0 or self._time_surface is None:
            self._update_timer = 0.0
            now = datetime.now()
            new_time = now.strftime('%H:%M:%S')
            new_date = now.strftime('%A, %B %d')
            if new_time != self._time_text:
                self._time_text = new_time
                self._time_surface = self.time_font.render(
                    self._time_text, True, (255, 255, 255),
                )
            if new_date != self._date_text:
                self._date_text = new_date
                self._date_surface = self.date_font.render(
                    self._date_text, True, (200, 200, 200),
                )

        # Advance the sinusoidal pulse phase
        self._pulse_phase += dt * self.pulse_speed * math.pi
        # Keep phase bounded to avoid float drift over long runs
        if self._pulse_phase > 2.0 * math.pi:
            self._pulse_phase -= 2.0 * math.pi

    def draw(self, surface):
        """Draw the clock pill onto *surface*."""
        # Compute LIVE opacity from sine wave
        sine_val = 0.5 + 0.5 * math.sin(self._pulse_phase)
        live_opacity = int(255 * (self.pulse_min + (1.0 - self.pulse_min) * sine_val))

        # --- Measure total width so the pill fits its content ---
        cx_offset = 10  # left padding

        # LIVE dot + gap
        dot_radius = 7
        dot_w = dot_radius * 2 + 4  # 18 px
        cx_offset += dot_w

        # LIVE text
        live_text_surf = self.live_font.render('LIVE', True, (255, 70, 70))
        cx_offset += live_text_surf.get_width() + 10

        # Time
        time_w = self._time_surface.get_width() if self._time_surface else 0
        cx_offset += time_w + 10

        # Date
        date_w = self._date_surface.get_width() if self._date_surface else 0
        cx_offset += date_w + 10  # right padding

        total_w = cx_offset
        total_h = 44

        # Background pill
        bg = pygame.Surface((total_w, total_h), pygame.SRCALPHA)
        pygame.draw.rect(bg, (0, 0, 0, 100), (0, 0, total_w, total_h), border_radius=6)
        surface.blit(bg, (self.x, self.y))

        # Reset cursor for drawing contents
        cx = self.x + 10
        cy = self.y + total_h // 2

        # LIVE dot (pulsing red circle)
        dot_surf = pygame.Surface((dot_radius * 2, dot_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, (255, 50, 50, live_opacity),
                           (dot_radius, dot_radius), dot_radius)
        surface.blit(dot_surf, (cx, cy - dot_radius))
        cx += dot_radius * 2 + 4

        # LIVE text
        live_text_surf.set_alpha(live_opacity)
        surface.blit(live_text_surf, (cx, cy - live_text_surf.get_height() // 2))
        cx += live_text_surf.get_width() + 10

        # Time
        if self._time_surface:
            surface.blit(self._time_surface,
                         (cx, cy - self._time_surface.get_height() // 2))
            cx += self._time_surface.get_width() + 10

        # Date
        if self._date_surface:
            surface.blit(self._date_surface,
                         (cx, cy - self._date_surface.get_height() // 2))
