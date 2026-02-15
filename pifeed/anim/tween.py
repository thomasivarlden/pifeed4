"""Frame-based tweening system.

Provides ``Tween`` (single value interpolation) and ``TweenGroup``
(named collection of tweens updated each frame).  Pure Python -- no
framework imports.
"""

from __future__ import annotations

from .easing import linear


class Tween:
    """Animates a single numeric value from *start* to *end* over
    *duration* seconds using the supplied *easing* function.

    Call :meth:`update` each frame with the delta-time *dt*.  Read
    :attr:`value` to get the current interpolated result.
    """

    def __init__(
        self,
        start: float,
        end: float,
        duration: float,
        easing=linear,
        on_complete=None,
    ):
        self.start = start
        self.end = end
        self.duration = duration
        self.easing = easing
        self.on_complete = on_complete
        self.elapsed: float = 0.0
        self.value: float = start
        self.finished: bool = False

    def update(self, dt: float) -> None:
        if self.finished:
            return
        self.elapsed += dt
        t = min(self.elapsed / self.duration, 1.0) if self.duration > 0 else 1.0
        eased = self.easing(t)
        self.value = self.start + (self.end - self.start) * eased
        if t >= 1.0:
            self.value = self.end
            self.finished = True
            if self.on_complete:
                self.on_complete()


class TweenGroup:
    """Manages a set of named :class:`Tween` instances.

    Each frame the caller invokes :meth:`update` with the delta-time.
    Finished tweens are automatically removed after their completion
    callback fires.
    """

    def __init__(self):
        self.tweens: dict[str, Tween] = {}
        self._final_values: dict[str, float] = {}

    def add(self, name: str, tween: Tween) -> None:
        """Register (or replace) a tween under *name*."""
        self.tweens[name] = tween
        # Clear any stale final value so get_value reads from the
        # live tween while it is active.
        self._final_values.pop(name, None)

    def get_value(self, name: str, default: float = 0.0) -> float:
        """Return the current value of the named tween.

        If the tween has already completed and been pruned, the final
        snapped value is returned.  If no tween by that name was ever
        registered, *default* is returned.
        """
        if name in self.tweens:
            return self.tweens[name].value
        if name in self._final_values:
            return self._final_values[name]
        return default

    def update(self, dt: float) -> None:
        """Advance every active tween by *dt* seconds and prune
        finished ones.

        Safe against mutations during iteration: ``on_complete``
        callbacks may call :meth:`add` or :meth:`cancel` on this
        group.
        """
        # Snapshot so the dict can be mutated by on_complete callbacks.
        active = list(self.tweens.items())
        finished: list[str] = []
        for name, tween in active:
            tween.update(dt)
            if tween.finished:
                finished.append(name)
        for name in finished:
            # Only delete if it hasn't been replaced by a callback.
            if name in self.tweens and self.tweens[name].finished:
                self._final_values[name] = self.tweens[name].value
                del self.tweens[name]

    def cancel(self, name: str | None = None) -> None:
        """Cancel a single tween by *name*, or all tweens if *name*
        is ``None``."""
        if name is not None:
            self.tweens.pop(name, None)
            self._final_values.pop(name, None)
        else:
            self.tweens.clear()
            self._final_values.clear()

    @property
    def is_active(self) -> bool:
        """``True`` while at least one tween is still running."""
        return len(self.tweens) > 0
