"""Per-call RNG context — replaces module-level ``random`` / ``np.random``.

The composer pipeline used to seed Python's global ``random`` module and
``numpy.random`` at the start of every ``compose()`` call.  That pattern
breaks determinism as soon as two compositions run concurrently (threads
or async tasks) because they share the same process-wide RNG state.

This module exposes a ``random.Random`` and a ``numpy.random.Generator``
scoped to the current ``ContextVar``.  Inside one logical composition
the two RNGs behave exactly like the old globals; across concurrent
calls each gets its own independent state.

Usage::

    from composer._rng import set_rng, rng, np_rng

    def compose(..., seed):
        set_rng(seed)
        ...
        # Downstream code calls rng() / np_rng() instead of the globals.
"""

from __future__ import annotations

import contextvars
import random
from typing import Optional

import numpy as np

_rng_var: contextvars.ContextVar[Optional[random.Random]] = contextvars.ContextVar(
    "composer_rng", default=None,
)
_np_rng_var: contextvars.ContextVar[Optional[np.random.Generator]] = contextvars.ContextVar(
    "composer_np_rng", default=None,
)


def set_rng(seed: Optional[int]) -> None:
    """Initialise per-call RNGs from *seed*.  Call at the start of compose().

    Passing ``None`` creates RNGs seeded from the OS entropy pool.
    """
    _rng_var.set(random.Random(seed))
    _np_rng_var.set(np.random.default_rng(seed))


def rng() -> random.Random:
    """Return the active per-call ``random.Random``.

    If no context has been established (e.g. a helper is invoked
    directly from user code or a test), a fresh OS-seeded
    ``random.Random`` is created and cached for the current context.
    """
    r = _rng_var.get()
    if r is None:
        r = random.Random()
        _rng_var.set(r)
    return r


def np_rng() -> np.random.Generator:
    """Return the active per-call ``numpy.random.Generator``."""
    r = _np_rng_var.get()
    if r is None:
        r = np.random.default_rng()
        _np_rng_var.set(r)
    return r
