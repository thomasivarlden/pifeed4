"""YAML configuration loader with deep-merge support.

Loads ``defaults.yaml``, then a mode-specific override file (e.g.
``debug.yaml`` or ``production.yaml``), and finally applies any CLI
overrides before constructing a :class:`PiFeedConfig` instance.
"""

import dataclasses
import os

import yaml

from .schema import (
    AnimConfig,
    AppConfig,
    CacheConfig,
    DebugConfig,
    FontConfig,
    LayoutConfig,
    PiFeedConfig,
    ThemeConfig,
    TimingConfig,
    WindowConfig,
)


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* dict.

    Nested dicts are merged recursively; all other values in *override*
    replace the corresponding value in *base*.  Neither input dict is
    mutated.
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(
    config_dir: str,
    mode: str = 'production',
    cli_overrides: dict = None,
) -> PiFeedConfig:
    """Load config from YAML files with mode-specific overrides.

    Resolution order (later wins):
    1. ``defaults.yaml``
    2. ``<mode>.yaml``   (e.g. ``debug.yaml`` or ``production.yaml``)
    3. *cli_overrides*   (programmatic / command-line overrides)
    """
    # 1. Load defaults.yaml
    defaults_path = os.path.join(config_dir, 'defaults.yaml')
    config_data: dict = {}
    if os.path.exists(defaults_path):
        with open(defaults_path) as f:
            config_data = yaml.safe_load(f) or {}

    # 2. Load mode override (debug.yaml or production.yaml)
    mode_path = os.path.join(config_dir, f'{mode}.yaml')
    if os.path.exists(mode_path):
        with open(mode_path) as f:
            mode_data = yaml.safe_load(f) or {}
            config_data = deep_merge(config_data, mode_data)

    # 3. Apply CLI overrides
    if cli_overrides:
        config_data = deep_merge(config_data, cli_overrides)

    # Build PiFeedConfig from the merged dict
    return _dict_to_config(config_data)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SECTION_MAP = {
    'app': AppConfig,
    'window': WindowConfig,
    'layout': LayoutConfig,
    'animation': AnimConfig,
    'timing': TimingConfig,
    'fonts': FontConfig,
    'theme': ThemeConfig,
    'cache': CacheConfig,
    'debug': DebugConfig,
}


def _dict_to_config(data: dict) -> PiFeedConfig:
    """Convert a merged config dict to a :class:`PiFeedConfig` dataclass."""
    config = PiFeedConfig()

    for section_name, _cls in _SECTION_MAP.items():
        if section_name in data:
            current = getattr(config, section_name)
            setattr(config, section_name, _update_dataclass(current, data[section_name]))

    return config


def _update_dataclass(instance, data: dict):
    """Update a dataclass *instance* from *data*, ignoring unknown keys."""
    field_names = {f.name for f in dataclasses.fields(instance)}
    for key, value in data.items():
        if key in field_names:
            setattr(instance, key, value)
    return instance
