# PiFeed

Broadcast-style animated news dashboard built with **pygame-ce**. Fetches RSS/Atom feeds, caches article images, and displays stories in a TV news-like layout with Ken Burns pan/zoom, crossfade transitions, and a scrolling ticker. Designed for Raspberry Pi or any always-on wall-mounted display.

![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue)
![pygame-ce](https://img.shields.io/badge/pygame--ce-2.4%2B-green)

## Screen Layout

```
┌──────────────────────────────────┬────────────────┐
│  Clock/LIVE              Channel │                │
│  (top-left)              Badge   │   Queue Rail   │
│                       (top-right)│                │
│                                  │  Previous item │
│          Hero Image              │  Current  item │
│        (70% width)               │  Upcoming items│
│                                  │  UP NEXT hint  │
│  Ken Burns pan + zoom            │                │
│  Double-buffered crossfade       ├────────────────┤
│                                  │ Source Indicator│
│  ┌─ Lower Third ──────────┐     │ 3 progress bars │
│  │  Headline               │     │                │
│  │  Summary (up to 6 lines)│     │                │
│  └─────────────────────────┘     │                │
├──────────────────────────────────┴────────────────┤
│  Ticker — continuous scrolling headlines ────────→ │
└───────────────────────────────────────────────────┘
```

## Features

- **Multi-source RSS/Atom** — rotates through configurable feed sources with per-source accent colours, timing, and item limits
- **Ken Burns effect** — slow pan and zoom on hero images with seamless cycle chaining
- **Crossfade transitions** — double-buffered hero images with smooth alpha blending
- **Lower third banner** — slides in with headline and word-wrapped summary text
- **Queue rail sidebar** — shows previous, current, and upcoming stories with scroll animation and an "UP NEXT" source preview
- **Source indicator** — three progress bars: source rotation, story progress, and story countdown timer
- **Channel badge** — displays the current source name with accent colour
- **Scrolling ticker** — continuous headline bar across the bottom from all sources
- **Profile hot-reload** — edit YAML profiles and see changes within 5 seconds, no restart needed
- **Background fetching** — feeds and images download on background threads without blocking the UI
- **Image cache** — disk-based LRU cache with configurable size limit
- **Keyboard controls** — arrow keys to navigate stories/sources, F for fullscreen, Esc/Q to quit

## Quick Start

```bash
# Clone
git clone https://github.com/thomasivarlden/pifeed4.git
cd pifeed4

# Set up virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run (production: 1080p fullscreen)
./run.sh

# Or run directly
python main.py
```

## Usage

```bash
# Production mode — 1920x1080 fullscreen
python main.py

# Debug mode — 720p windowed with FPS overlay
python main.py --mode debug

# Demo mode — synthetic data, no network required
python main.py --mode debug --demo

# Custom config directory
python main.py --config-dir /path/to/config
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Esc` / `Q` | Quit |
| `F` | Toggle fullscreen |
| `Right` | Next source |
| `Left` | Previous source |
| `Down` | Next story |
| `Up` | Previous story |
| `Space` | Next story (debug mode) |
| `N` | Next source (debug mode) |
| `D` | Toggle debug overlay (debug mode) |

## Configuration

### Config files (`config/`)

YAML with deep-merge layering: `defaults.yaml` is the base, overridden by `debug.yaml` or `production.yaml` depending on the run mode.

Key settings in `defaults.yaml`:

```yaml
layout:
  hero_width_ratio: 0.70    # Hero takes 70% of screen width
  queue_width_ratio: 0.30   # Queue rail takes 30%
  ticker_height: 56
  lower_third_height: 500
  queue_visible_items: 5

fonts:
  headline_size: 72
  summary_size: 64
  queue_item_size: 68

timing:
  story_duration: 12.0       # Seconds per story
  items_per_source: 10        # Max items shown per source
  feed_refresh_interval: 3600 # Seconds between feed refreshes
```

### Feed profiles (`profiles/`)

Each YAML file defines one news source:

```yaml
name: "BBC News"
feed_url: "http://feeds.bbci.co.uk/news/rss.xml"
enabled: true

timing:
  refresh_interval: 1800    # Override default refresh (seconds)
  story_duration: 12.0      # Override default story duration

display:
  items_limit: 10
  accent_color: "#BB1919"   # Source accent colour
```

To add a new source, create a new `.yaml` file in `profiles/`. It will be picked up automatically within 5 seconds (hot-reload). Set `enabled: false` to disable a source without removing the file.

### Included Sources

Nordic & EU security and defence feeds, plus general tech/security news:

| Source | Category |
|--------|----------|
| BBC News | General news |
| The Hacker News | Cybersecurity |
| SecurityWeek | Cybersecurity |
| Dark Reading | Cybersecurity |
| CyberWire | Cybersecurity |
| CERT-SE | Swedish CERT |
| CERT-EU | EU CERT advisories |
| NSM NCSC Norway | Norwegian cyber security |
| NCSC Finland (news) | Finnish cyber security |
| NCSC-FI (vulns) | Finnish vulnerability alerts |
| UK NCSC | UK cyber security |
| Forsvarsmakten | Swedish armed forces |
| Krisinformation.se | Swedish crisis info |
| MCF | Swedish civil defence |
| Defence News | Global defence |
| Netnod | Networking & DNS |
| EU Council (press, FAC, JHA) | EU Council meetings |
| Riksdagen | Swedish parliament |

## Project Structure

```
pifeed/
├── app.py              # Game loop, event wiring
├── anim/               # Animation system (pure Python)
│   ├── easing.py       # Easing functions
│   ├── ken_burns.py    # Pan/zoom controller
│   ├── sequencer.py    # Multi-phase story transitions
│   └── tween.py        # Value interpolation engine
├── config/             # YAML loading and schema
│   ├── loader.py       # Deep-merge config loader
│   ├── profiles.py     # Profile manager with hot-reload
│   └── schema.py       # Typed config dataclasses
├── data/               # Feed management (no UI dependency)
│   ├── cache.py        # Disk image cache with LRU
│   ├── demo.py         # Synthetic demo data
│   ├── fetcher.py      # Background RSS fetching
│   ├── manager.py      # Source rotation and scheduling
│   └── models.py       # FeedItem / FeedSource dataclasses
└── ui/                 # PyGame rendering widgets
    ├── channel_badge.py # Source name badge
    ├── clock_widget.py  # Clock with LIVE pulse
    ├── debug_overlay.py # FPS/memory stats
    ├── hero.py          # Double-buffered hero image
    ├── lower_third.py   # Headline/summary banner
    ├── queue_rail.py    # Story queue sidebar
    ├── root.py          # Layout and compositor
    └── ticker.py        # Scrolling headline bar
```

## Architecture

- **Game loop**: Pure pygame at 60 fps. All widgets follow `update(dt)` / `draw(surface)`.
- **Threading**: Main thread owns the game loop and all UI. Background daemon threads handle feed fetching and image downloading. Results are queued via a lock-protected list and drained each frame.
- **Animation**: Frame-based `Tween`/`TweenGroup` system with easing functions and `on_complete` chaining. The `StorySequencer` orchestrates multi-phase transitions (crossfade, slide-in, text fades).
- **Configuration**: YAML with deep-merge layering. Profile hot-reload via mtime polling every 5 seconds.

## Requirements

- Python 3.14+
- pygame-ce >= 2.4.1
- feedparser >= 6.0
- PyYAML >= 6.0
- requests >= 2.31
- Pillow >= 10.0
- psutil >= 5.9

## License

MIT
