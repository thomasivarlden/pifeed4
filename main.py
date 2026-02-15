#!/usr/bin/env python3
"""PiFeed - Broadcast-style animated news dashboard.

Usage:
    python main.py                          # Production mode (1080p fullscreen)
    python main.py --mode debug             # Debug mode (720p windowed)
    python main.py --mode debug --demo      # Demo mode with synthetic data
    python main.py --config-dir /path/to/config  # Custom config directory
"""

import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser(
        description='PiFeed - Broadcast-style animated news dashboard'
    )
    parser.add_argument(
        '--config-dir',
        default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config'),
        help='Path to configuration directory (default: ./config)',
    )
    parser.add_argument(
        '--mode',
        choices=['debug', 'production'],
        default='production',
        help='Run mode (default: production)',
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Use synthetic demo data (no network required)',
    )
    return parser.parse_args()


def main():
    args = parse_args()

    from pifeed.app import PiFeedApp

    app = PiFeedApp(
        config_dir=args.config_dir,
        mode=args.mode,
        demo=args.demo,
    )
    app.run()


if __name__ == '__main__':
    main()
