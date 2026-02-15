# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is PiFeed4

PiFeed4 is a broadcast-style animated news dashboard built with **pygame-ce** (Community Edition). It fetches RSS/Atom feeds, caches article images, and displays stories in a TV news-like layout with Ken Burns pan/zoom, crossfade transitions, a lower-third headline banner, a scrolling ticker, and a sidebar queue rail. Designed to run on Raspberry Pi or similar always-on displays.

## Running

```bash
# Activate venv and run (production: 1080p fullscreen)
./run.sh

# Debug mode (720p windowed, verbose logging, debug overlay)
python main.py --mode debug

# Demo mode (synthetic data, no network required)
python main.py --mode debug --demo
```

Dependencies: `pip install -r requirements.txt` (into the `.venv`). Python 3.14.

## Architecture

### Game loop (no framework event system)

The app uses a pure pygame game loop at 60fps (`PiFeedApp._game_loop`). There is no Kivy/Qt — all state is driven by `update(dt)` / `draw()` calls each frame. Background work (feed fetching, image downloading) runs on daemon threads; results are queued via a thread-safe `_pending_results` list and processed on the main thread in `FeedManager.update()`.

### Key layers

- **`pifeed/app.py`** — `PiFeedApp`: owns the game loop, wires data events to UI updates. Entry point is `run()`.
- **`pifeed/config/`** — YAML config with deep-merge: `defaults.yaml` → `<mode>.yaml` → CLI overrides. All settings are typed dataclasses in `schema.py`. `SourceProfile` (also in schema.py) defines per-source overrides.
- **`pifeed/data/`** — Feed management layer (no UI dependency):
  - `FeedManager` — central coordinator: source rotation, story advance timer, event dispatch (`on_story_changed`, `on_source_changed`). Timer-based scheduling driven by `update(dt)`.
  - `FeedFetcherThread` — background RSS fetch via `feedparser` + `requests`.
  - `ImageCache` — disk cache with LRU eviction, background downloads.
  - `DemoDataProvider` — synthetic data with Pillow-generated placeholder images.
- **`pifeed/anim/`** — Pure-Python animation system (no framework imports):
  - `Tween` / `TweenGroup` — named value interpolation with easing and `on_complete` chaining.
  - `StorySequencer` — orchestrates the multi-phase transition timeline: crossfade → lower-third slide → headline fade → summary fade. Exposes public state floats that the UI reads each frame.
  - `KenBurnsController` — continuous pan/zoom with auto-chaining cycles. Returns `Transform(x, y, scale)`.
  - `easing.py` — standard easing functions (`out_back`, `in_out_quad`, etc.).
- **`pifeed/ui/`** — PyGame rendering widgets, all follow `update(dt)` / `draw(surface, ...)` pattern:
  - `PiFeedRoot` — layout calculator and compositor. Creates child widgets and delegates draw calls.
  - `HeroWidget` — double-buffered crossfade with Ken Burns. Images pre-loaded at 130% viewport size.
  - `LowerThirdWidget` — slide-in headline/summary banner with accent color.
  - `QueueRailWidget` — sidebar showing previous/current/upcoming stories.
  - `TickerWidget` — seamless horizontal scrolling headline bar.
  - `ClockWidget` — time/date with pulsing LIVE indicator.
  - `DebugOverlay` — FPS/frame-time/memory stats (debug mode only).

### Configuration

Config files in `config/` use YAML with deep-merge layering. Profile YAML files in `profiles/` each define one feed source (name, feed_url, accent_color, timing overrides). Profiles support hot-reload — `ProfileManager` checks file mtimes every 5 seconds.

### Threading model

Main thread: game loop + all UI + timer-based scheduling. Background daemon threads: feed fetching (`FeedFetcherThread`) and image downloading (`ImageCache`). Thread→main communication uses `FeedManager._enqueue_result()` with a lock-protected list, drained each frame in `update()`.

### Debug hotkeys (debug mode only)

Space=next story, N=next source, D=toggle debug overlay, F=fullscreen, Q/Esc=quit.
