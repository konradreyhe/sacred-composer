"""1/f (pink) noise generation for natural tempo variation."""

from __future__ import annotations

import numpy as np


def generate_1f_noise(n: int, sigma_ms: float = 12.0) -> np.ndarray:
    """Generate 1/f (pink) noise for natural tempo variation.

    Returns *n* samples of correlated noise with the given standard
    deviation (in seconds).  The 1/f spectrum produces phrase-level
    accelerandos and ritardandos that resemble a real performer's rubato.
    """
    if n <= 0:
        return np.array([])
    white = np.random.randn(n)
    freqs = np.fft.rfftfreq(n)
    freqs[0] = 1  # avoid division by zero
    spectrum = np.fft.rfft(white)
    spectrum *= 1.0 / np.sqrt(freqs)
    pink = np.fft.irfft(spectrum, n=n)
    # Normalize to desired standard deviation (convert ms -> seconds)
    if np.std(pink) > 0:
        pink = pink / np.std(pink) * (sigma_ms / 1000.0)
    return pink
