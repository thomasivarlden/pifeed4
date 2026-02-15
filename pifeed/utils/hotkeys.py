"""Debug mode keyboard bindings for PiFeed (PyGame)."""

import logging
import pygame

logger = logging.getLogger('pifeed.hotkeys')


class HotkeyManager:
    """Manages keyboard shortcuts for debug mode."""

    def __init__(self, app):
        self.app = app
        self.active = False

    def bind(self):
        """Activate hotkey handling."""
        self.active = True
        logger.info("Debug hotkeys active: Space=next, N=source, D=debug, F=fullscreen, Q=quit")

    def unbind(self):
        """Deactivate hotkey handling."""
        self.active = False

    def handle_event(self, event):
        """Process a pygame KEYDOWN event. Returns True if handled."""
        if not self.active or event.type != pygame.KEYDOWN:
            return False

        if event.key == pygame.K_SPACE:
            self._next_story()
            return True
        elif event.key == pygame.K_n:
            self._next_source()
            return True
        elif event.key == pygame.K_d:
            self._toggle_debug()
            return True
        elif event.key == pygame.K_f:
            self._toggle_fullscreen()
            return True
        elif event.key in (pygame.K_q, pygame.K_ESCAPE):
            self._quit()
            return True

        return False

    def _next_story(self):
        if hasattr(self.app, 'feed_manager') and self.app.feed_manager:
            logger.debug("Hotkey: next story")
            self.app.feed_manager.advance_story()

    def _next_source(self):
        if hasattr(self.app, 'feed_manager') and self.app.feed_manager:
            logger.debug("Hotkey: next source")
            self.app.feed_manager.advance_source()

    def _toggle_debug(self):
        if hasattr(self.app, 'root') and self.app.root:
            logger.debug("Hotkey: toggle debug overlay")
            self.app.root.toggle_debug_overlay()

    def _toggle_fullscreen(self):
        logger.debug("Hotkey: toggle fullscreen")
        self.app.toggle_fullscreen()

    def _quit(self):
        logger.info("Hotkey: quit")
        self.app.running = False
