"""WAV renderer — NumPy-accelerated synthesis from Sacred Composer scores.

Renders Score objects directly to WAV using additive synthesis with
instrument-specific timbres, Karplus-Strong plucked strings, FM synthesis
for bells/brass, and optional Freeverb spatial processing.
"""

from __future__ import annotations

import struct
from typing import Optional

import numpy as np

from sacred_composer.core import Score, Voice, Note


def midi_to_freq(midi_note: float) -> float:
    """Convert MIDI note number (supports fractional for microtonal) to frequency."""
    return 440.0 * (2 ** ((midi_note - 69) / 12))


def _adsr_envelope(n_samples: int, sample_rate: int, duration: float,
                   attack: float = 0.02, decay: float = 0.05,
                   sustain: float = 0.7, release: float = 0.1) -> np.ndarray:
    """Vectorized ADSR envelope as a NumPy array."""
    t = np.arange(n_samples, dtype=np.float64) / sample_rate

    env = np.zeros(n_samples, dtype=np.float64)

    # Attack phase
    attack_mask = t < attack
    if attack > 0:
        env[attack_mask] = t[attack_mask] / attack
    else:
        env[attack_mask] = 1.0

    # Decay phase
    decay_start = attack
    decay_end = attack + decay
    decay_mask = (t >= decay_start) & (t < decay_end)
    if decay > 0:
        env[decay_mask] = 1.0 - (1.0 - sustain) * ((t[decay_mask] - decay_start) / decay)
    else:
        env[decay_mask] = sustain

    # Sustain phase
    sustain_end = max(0, duration - release)
    sustain_mask = (t >= decay_end) & (t < sustain_end)
    env[sustain_mask] = sustain

    # Release phase
    release_start = sustain_end
    release_end = sustain_end + release
    release_mask = (t >= release_start) & (t < release_end)
    if release > 0:
        env[release_mask] = sustain * (1.0 - (t[release_mask] - release_start) / release)

    # After release: already zero from np.zeros

    return env


# ---------------------------------------------------------------------------
# Instrument timbres: list of (harmonic_number, relative_amplitude) pairs
# ---------------------------------------------------------------------------
_TIMBRES: dict[str, list[tuple[float, float]]] = {
    "sine": [(1, 1.0)],
    "triangle": [(1, 1.0), (3, 1/9), (5, 1/25), (7, 1/49)],
    "piano": [(1, 1.0), (2, 0.5), (3, 0.25), (4, 0.15), (5, 0.08), (6, 0.04)],
    "strings": [(1, 1.0), (2, 0.8), (3, 0.6), (4, 0.4), (5, 0.3), (6, 0.2), (7, 0.15), (8, 0.1)],
    "flute": [(1, 1.0), (2, 0.3), (3, 0.1)],
    "organ": [(1, 1.0), (2, 1.0), (3, 0.5), (4, 0.5), (5, 0.25), (6, 0.25)],
    "bell": [(1, 1.0), (2.76, 0.6), (4.07, 0.4), (5.93, 0.25), (8.47, 0.15)],
    "karplus_strong": [],   # special: handled by Karplus-Strong algorithm
    "fm_bell": [],          # special: handled by FM synthesis
}

# GM program number to timbre name
_GM_TO_TIMBRE: dict[int, str] = {
    0: "piano", 6: "piano", 8: "bell", 11: "bell", 12: "bell",
    19: "organ", 24: "triangle",
    25: "karplus_strong", 26: "karplus_strong", 27: "karplus_strong",
    40: "strings", 41: "strings", 42: "strings", 43: "strings",
    46: "triangle", 48: "strings", 52: "organ",
    56: "triangle", 57: "triangle", 58: "triangle", 60: "triangle",
    61: "fm_bell", 62: "fm_bell",
    68: "flute", 70: "flute", 71: "flute", 73: "flute", 74: "flute", 75: "flute",
    104: "karplus_strong", 105: "karplus_strong",
}


def _get_timbre(gm_program: int) -> str:
    """Get timbre name for a GM program number."""
    return _GM_TO_TIMBRE.get(gm_program, "piano")


# ---------------------------------------------------------------------------
# Synthesis engines
# ---------------------------------------------------------------------------

def _synthesize_additive(
    freq: float,
    velocity: int,
    duration: float,
    timbre: list[tuple[float, float]],
    sample_rate: int,
) -> np.ndarray:
    """Additive synthesis — vectorized with NumPy."""
    amp = (velocity / 127.0) * 0.25
    total_dur = duration + 0.15  # include release tail
    n_samples = int(total_dur * sample_rate)

    attack = min(0.03, duration * 0.1)
    decay = min(0.06, duration * 0.2)
    release = min(0.15, duration * 0.3)

    t = np.arange(n_samples, dtype=np.float64) / sample_rate
    env = _adsr_envelope(n_samples, sample_rate, duration, attack, decay, 0.7, release)

    two_pi = 2.0 * np.pi
    signal = np.zeros(n_samples, dtype=np.float64)

    for harmonic, rel_amp in timbre:
        h_freq = freq * harmonic
        if h_freq > sample_rate / 2:  # Nyquist
            continue
        signal += rel_amp * np.sin(two_pi * h_freq * t)

    signal *= env * amp
    return signal


def _synthesize_karplus_strong(
    freq: float,
    velocity: int,
    duration: float,
    sample_rate: int,
) -> np.ndarray:
    """Karplus-Strong plucked-string synthesis.

    Noise burst fed into a delay line with an averaging (low-pass) filter.
    """
    amp = (velocity / 127.0) * 0.25
    total_dur = duration + 0.15
    n_samples = int(total_dur * sample_rate)

    # Delay line length = one period
    period = max(2, int(round(sample_rate / freq)))

    # Initialize with noise burst
    _rng = np.random.RandomState(int(freq) & 0x7FFFFFFF)
    buf = _rng.uniform(-1.0, 1.0, period).astype(np.float64)

    output = np.empty(n_samples, dtype=np.float64)

    # Loss factor for decay control
    loss = 0.996

    idx = 0
    for i in range(n_samples):
        output[i] = buf[idx]
        # Averaging filter: mean of current and next sample
        next_idx = (idx + 1) % period
        buf[idx] = loss * 0.5 * (buf[idx] + buf[next_idx])
        idx = next_idx

    # Apply velocity scaling
    output *= amp

    return output


def _synthesize_fm(
    freq: float,
    velocity: int,
    duration: float,
    sample_rate: int,
) -> np.ndarray:
    """FM synthesis for bell and brass timbres.

    carrier_freq = freq
    modulator_freq = freq * mod_ratio
    modulation_index decays over time for evolving timbre.
    """
    amp = (velocity / 127.0) * 0.25
    total_dur = duration + 0.15
    n_samples = int(total_dur * sample_rate)

    attack = min(0.03, duration * 0.1)
    decay = min(0.06, duration * 0.2)
    release = min(0.15, duration * 0.3)

    t = np.arange(n_samples, dtype=np.float64) / sample_rate
    env = _adsr_envelope(n_samples, sample_rate, duration, attack, decay, 0.7, release)
    two_pi = 2.0 * np.pi

    # FM parameters for bell-like timbre
    carrier_freq = freq
    mod_ratio = 3.5       # inharmonic ratio for bell character
    mod_freq = freq * mod_ratio
    mod_index_start = 8.0
    mod_index_end = 0.5

    # Modulation index envelope (exponential decay)
    mod_env = mod_index_start * np.exp(-5.0 * t / max(duration, 0.01))
    mod_env = np.clip(mod_env, mod_index_end, mod_index_start)

    # FM equation: carrier(t) = sin(2pi * fc * t + mod_index * sin(2pi * fm * t))
    modulator = mod_env * np.sin(two_pi * mod_freq * t)
    signal = np.sin(two_pi * carrier_freq * t + modulator)

    signal *= env * amp
    return signal


def _synthesize_note(
    freq: float,
    velocity: int,
    duration: float,
    timbre_name: str,
    sample_rate: int,
) -> np.ndarray:
    """Dispatch to the appropriate synthesis engine."""
    if timbre_name == "karplus_strong":
        return _synthesize_karplus_strong(freq, velocity, duration, sample_rate)
    elif timbre_name == "fm_bell":
        return _synthesize_fm(freq, velocity, duration, sample_rate)
    else:
        partials = _TIMBRES.get(timbre_name, _TIMBRES["piano"])
        return _synthesize_additive(freq, velocity, duration, partials, sample_rate)


# ---------------------------------------------------------------------------
# Freeverb (Schroeder reverb: 8 comb filters + 4 allpass filters)
# ---------------------------------------------------------------------------

def _comb_filter(signal: np.ndarray, delay: int, feedback: float,
                 damp: float) -> np.ndarray:
    """Feedback comb filter with one-pole low-pass damping."""
    n = len(signal)
    out = np.zeros(n, dtype=np.float64)
    buf = np.zeros(delay, dtype=np.float64)
    filter_state = 0.0
    idx = 0

    for i in range(n):
        buf_out = buf[idx]
        # One-pole low-pass
        filter_state = buf_out * (1.0 - damp) + filter_state * damp
        buf[idx] = signal[i] + filter_state * feedback
        out[i] = buf_out
        idx = (idx + 1) % delay

    return out


def _allpass_filter(signal: np.ndarray, delay: int,
                    feedback: float = 0.5) -> np.ndarray:
    """Allpass filter for diffusion."""
    n = len(signal)
    out = np.zeros(n, dtype=np.float64)
    buf = np.zeros(delay, dtype=np.float64)
    idx = 0

    for i in range(n):
        buf_out = buf[idx]
        out[i] = -signal[i] + buf_out
        buf[idx] = signal[i] + buf_out * feedback
        idx = (idx + 1) % delay

    return out


def _freeverb(signal: np.ndarray, sample_rate: int,
              room_size: float = 0.7, damping: float = 0.5,
              wet: float = 0.3) -> np.ndarray:
    """Simplified Freeverb: 8 parallel comb filters + 4 serial allpass filters.

    Parameters
    ----------
    signal : mono input signal
    sample_rate : sample rate
    room_size : 0..1 feedback amount (bigger = longer tail)
    damping : 0..1 high-frequency absorption
    wet : wet/dry mix ratio (0 = fully dry, 1 = fully wet)
    """
    # Comb filter delay lengths (in samples at 44100; scale for other rates)
    scale = sample_rate / 44100.0
    comb_delays = [int(d * scale) for d in
                   [1557, 1617, 1491, 1422, 1277, 1356, 1188, 1116]]
    allpass_delays = [int(d * scale) for d in [556, 441, 341, 225]]

    feedback = room_size * 0.28 + 0.7  # map 0..1 to 0.7..0.98

    # Parallel comb filters, summed
    wet_signal = np.zeros_like(signal)
    for delay in comb_delays:
        wet_signal += _comb_filter(signal, delay, feedback, damping)

    # Scale down after summing 8 combs
    wet_signal *= (1.0 / 8.0)

    # Serial allpass filters for diffusion
    for delay in allpass_delays:
        wet_signal = _allpass_filter(wet_signal, delay)

    # Mix
    return signal * (1.0 - wet) + wet_signal * wet


# ---------------------------------------------------------------------------
# Main render and WAV writer
# ---------------------------------------------------------------------------

def render_wav(score: Score, filename: str, sample_rate: int = 44100,
               reverb: bool = False, room_size: float = 0.7,
               damping: float = 0.5, wet: float = 0.3) -> str:
    """Render a Score to a WAV file using NumPy-accelerated synthesis.

    Parameters
    ----------
    score : The Score to render.
    filename : Output .wav file path.
    sample_rate : Sample rate (default 44100).
    reverb : Enable Freeverb spatial processing (default False).
    room_size : Reverb room size 0..1 (default 0.7).
    damping : Reverb damping 0..1 (default 0.5).
    wet : Reverb wet/dry mix 0..1 (default 0.3).

    Returns
    -------
    The filename written.
    """
    beats_per_sec = score.tempo / 60.0

    # Calculate total duration
    total_dur_beats = score.duration
    total_dur_sec = total_dur_beats / beats_per_sec + 1.0  # 1s tail
    total_samples = int(total_dur_sec * sample_rate)

    # NumPy mix buffer
    buffer = np.zeros(total_samples, dtype=np.float64)

    note_count = 0
    for voice in score.voices:
        timbre_name = _get_timbre(voice.instrument)

        for note in voice.notes:
            if note.is_rest:
                continue

            freq = midi_to_freq(note.pitch)
            start_sec = note.time / beats_per_sec
            dur_sec = note.duration / beats_per_sec

            samples = _synthesize_note(freq, note.velocity, dur_sec,
                                       timbre_name, sample_rate)
            start_idx = int(start_sec * sample_rate)
            end_idx = start_idx + len(samples)

            # Clip to buffer bounds
            if start_idx >= total_samples:
                continue
            if end_idx > total_samples:
                samples = samples[:total_samples - start_idx]
                end_idx = total_samples

            buffer[start_idx:end_idx] += samples
            note_count += 1

    # Optional reverb
    if reverb:
        buffer = _freeverb(buffer, sample_rate, room_size, damping, wet)

    # Vectorized normalization
    peak = np.max(np.abs(buffer))
    if peak > 0:
        buffer *= 0.85 / peak

    # Vectorized 16-bit PCM conversion
    pcm_array = np.clip(buffer * 32767.0, -32767, 32767).astype(np.int16)
    pcm_bytes = pcm_array.tobytes()

    _write_wav(filename, pcm_bytes, sample_rate)
    return filename


def _write_wav(path: str, pcm_data: bytes, sample_rate: int,
               channels: int = 1, bits: int = 16) -> None:
    """Write WAV file from raw PCM bytes."""
    bytes_per_sample = bits // 8
    data_size = len(pcm_data)
    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))  # PCM
        f.write(struct.pack("<H", channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * channels * bytes_per_sample))
        f.write(struct.pack("<H", channels * bytes_per_sample))
        f.write(struct.pack("<H", bits))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(pcm_data)
