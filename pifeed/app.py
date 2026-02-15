"""PiFeed application - PyGame game loop."""

import os
import logging
import pygame

from .config.loader import load_config
from .config.profiles import ProfileManager
from .data.manager import FeedManager
from .anim.sequencer import StorySequencer
from .ui.root import PiFeedRoot
from .utils.hotkeys import HotkeyManager

logger = logging.getLogger('pifeed.app')


class PiFeedApp:
    """Main PiFeed application with PyGame game loop."""

    def __init__(self, config_dir='config', mode='production', demo=False):
        self.config_dir = os.path.abspath(config_dir)
        self.mode = mode
        self.demo = demo
        self.pf_config = None
        self.profile_manager = None
        self.feed_manager = None
        self.sequencer = None
        self.hotkeys = None
        self.root = None
        self.running = False
        self._screen = None
        self._clock = None
        self._fullscreen = False

    def run(self):
        """Main entry point - initialize and run the game loop."""
        self._load_config()
        self._init_pygame()
        self._init_data()
        self._init_ui()
        self._start()
        self._game_loop()
        self._shutdown()

    def _load_config(self):
        """Load configuration."""
        self.pf_config = load_config(self.config_dir, self.mode)
        if self.demo:
            self.pf_config.app.demo = True

        log_level = getattr(logging, self.pf_config.app.log_level.upper(), logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S',
        )
        logger.info(f"PiFeed starting in {self.mode} mode")

    def _init_pygame(self):
        """Initialize PyGame."""
        pygame.init()

        w = self.pf_config.window.width
        h = self.pf_config.window.height
        title = self.pf_config.window.title

        flags = 0
        if self.pf_config.window.fullscreen:
            flags |= pygame.FULLSCREEN
            self._fullscreen = True

        self._screen = pygame.display.set_mode((w, h), flags)
        pygame.display.set_caption(title)
        self._clock = pygame.time.Clock()

        logger.info(f"Window: {w}x{h}, fullscreen={self._fullscreen}")

    def _init_data(self):
        """Initialize data layer."""
        project_root = os.path.dirname(self.config_dir)

        profiles_dir = self.pf_config.app.profiles_dir
        if not os.path.isabs(profiles_dir):
            profiles_dir = os.path.join(project_root, profiles_dir)
        self.profile_manager = ProfileManager(profiles_dir)
        self.feed_manager = FeedManager(self.pf_config, self.profile_manager)
        self.sequencer = StorySequencer(self.pf_config.animation)

        # Resolve backgrounds directory for hero fallback images
        bg_dir = self.pf_config.app.backgrounds_dir
        if not os.path.isabs(bg_dir):
            bg_dir = os.path.join(project_root, bg_dir)
        self._backgrounds_dir = bg_dir

        # Wire feed events
        self.feed_manager.bind(
            on_story_changed=self._on_story_changed,
            on_source_changed=self._on_source_changed,
        )

    def _init_ui(self):
        """Initialize UI components."""
        w, h = self._screen.get_size()
        self.root = PiFeedRoot(w, h, self.pf_config, self._clock,
                               backgrounds_dir=self._backgrounds_dir)

    def _start(self):
        """Start everything."""
        self.running = True
        self.feed_manager.start(demo_mode=self.pf_config.app.demo)

        # Debug mode setup
        if self.mode == 'debug':
            self.hotkeys = HotkeyManager(self)
            self.hotkeys.bind()
            if self.pf_config.debug.show_overlay:
                self.root.enable_debug_overlay()

        # Initial ticker
        self._update_ticker()
        logger.info("PiFeed started successfully")

    def _game_loop(self):
        """Main game loop - 60fps."""
        while self.running:
            dt = self._clock.tick(60) / 1000.0

            # Handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    # Escape / Q always quit, F always toggles fullscreen
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        self.running = False
                    elif event.key == pygame.K_f:
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_RIGHT:
                        self.feed_manager.advance_source()
                    elif event.key == pygame.K_LEFT:
                        self.feed_manager.previous_source()
                    elif event.key == pygame.K_DOWN:
                        self.feed_manager.advance_story()
                    elif event.key == pygame.K_UP:
                        self.feed_manager.previous_story()
                    elif self.hotkeys:
                        self.hotkeys.handle_event(event)

            # Update
            self.feed_manager.update(dt)
            kb_transform = self.sequencer.update(dt)
            self.root.update(dt)

            # Draw
            self.root.draw(self._screen, self.sequencer, kb_transform)
            pygame.display.flip()

    def _shutdown(self):
        """Clean up."""
        logger.info("PiFeed shutting down")
        if self.feed_manager:
            self.feed_manager.stop()
        if self.sequencer:
            self.sequencer.stop()
        pygame.quit()

    def toggle_fullscreen(self):
        """Toggle between fullscreen and windowed mode."""
        self._fullscreen = not self._fullscreen
        w = self.pf_config.window.width
        h = self.pf_config.window.height
        if self._fullscreen:
            self._screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
        else:
            self._screen = pygame.display.set_mode((w, h))
        # Rebuild UI for new screen size
        sw, sh = self._screen.get_size()
        self.root = PiFeedRoot(sw, sh, self.pf_config, self._clock,
                               backgrounds_dir=self._backgrounds_dir)
        if self.mode == 'debug' and self.pf_config.debug.show_overlay:
            self.root.enable_debug_overlay()
        self._update_ticker()

    def _on_story_changed(self, old_item, new_item):
        """Handle story change from feed manager."""
        if not new_item or not self.root:
            return

        # Image-only refresh for the same story (e.g. image just finished
        # downloading).  Update the hero back-buffer in place without
        # restarting the full transition sequence or resetting timers.
        if old_item is new_item:
            self.root.hero.set_image(new_item.local_image_path)
            return

        logger.debug(f"Story changed: {new_item.display_title[:50]}")

        # Promote the previous back buffer to front so the crossfade
        # transitions from the last-visible image instead of an older one.
        self.root.hero.swap_buffers()

        # Load new image into hero back buffer
        self.root.hero.set_image(new_item.local_image_path)

        # Start transition sequence
        image_size = self.root.hero.get_image_size()
        viewport = (self.root.hero.rect.width, self.root.hero.rect.height)
        self.sequencer.play(image_size, viewport)

        # Update lower third content
        self.root.lower_third.set_content(
            new_item.display_title,
            new_item.display_summary,
            new_item.accent_color,
        )

        # Update queue (previous + current + upcoming + next source hint)
        source = self.feed_manager.current_source
        if source and self.root.queue_rail:
            display_items, cur_idx = self._build_queue_display()
            ns = self.feed_manager.next_source
            self.root.queue_rail.update_items(
                display_items, cur_idx, source.accent_color,
                next_source_name=ns.name if ns else None,
                next_source_hex=ns.accent_color if ns else None,
            )

        # Update source progress
        current, total = self.feed_manager.source_progress()
        src_cur, src_tot = self.feed_manager.sources_progress()
        if source and self.root.queue_rail:
            self.root.queue_rail.update_source(
                source.name, current, total, source.accent_color,
                story_duration=source.story_duration,
                source_current=src_cur, source_total=src_tot,
            )

        self._update_ticker()

    def _on_source_changed(self, source):
        """Handle source rotation."""
        if not source or not self.root:
            return
        logger.info(f"Source changed to: {source.name}")

        self.root.channel_badge.set_source(source.name, source.accent_color)

        if self.root.queue_rail:
            display_items, cur_idx = self._build_queue_display()
            ns = self.feed_manager.next_source
            self.root.queue_rail.update_items(
                display_items, cur_idx, source.accent_color,
                next_source_name=ns.name if ns else None,
                next_source_hex=ns.accent_color if ns else None,
            )
            src_cur, src_tot = self.feed_manager.sources_progress()
            self.root.queue_rail.update_source(
                source.name, 1, len(source.items), source.accent_color,
                story_duration=source.story_duration,
                source_current=src_cur, source_total=src_tot,
            )

    def _build_queue_display(self):
        """Build the queue rail display list: [previous, current, upcoming…].

        Returns:
            ``(display_items, current_index)`` where *current_index* is the
            position of the current story in the list.
        """
        vis = self.pf_config.layout.queue_visible_items
        display_items = []

        prev = self.feed_manager.previous_item
        if prev:
            display_items.append(prev)
            cur_idx = 1
        else:
            cur_idx = 0

        current = self.feed_manager.current_item
        if current:
            display_items.append(current)

        remaining = vis - len(display_items)
        display_items.extend(self.feed_manager.queue_items(remaining))
        return display_items, cur_idx

    def _update_ticker(self):
        """Update ticker with headlines from all sources."""
        if self.root and self.root.ticker:
            items = self.feed_manager.ticker_items()
            self.root.ticker.set_items(items)
