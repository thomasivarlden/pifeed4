"""Easing functions for animation interpolation.

Each function takes t in [0.0, 1.0] and returns the eased value.
Pure Python -- no framework imports.
"""

import math


def linear(t: float) -> float:
    """No easing -- constant velocity."""
    return t


def in_out_quad(t: float) -> float:
    """Quadratic ease in-out: accelerate then decelerate."""
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0


def out_quad(t: float) -> float:
    """Quadratic ease out: decelerate to stop."""
    return 1.0 - (1.0 - t) ** 2


def in_out_sine(t: float) -> float:
    """Sinusoidal ease in-out: gentle acceleration and deceleration."""
    return -(math.cos(math.pi * t) - 1.0) / 2.0


def out_back(t: float) -> float:
    """Overshoot ease out: exceed target then settle back.

    The overshoot constant c3 gives a roughly 10 % overshoot, which
    produces a punchy elastic feel suitable for slide-in panels.
    """
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * (t - 1.0) ** 3 + c1 * (t - 1.0) ** 2


def in_out_cubic(t: float) -> float:
    """Cubic ease in-out: stronger acceleration than quadratic."""
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - (-2.0 * t + 2.0) ** 3 / 2.0
