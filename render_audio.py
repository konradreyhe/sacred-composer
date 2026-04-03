#!/usr/bin/env python3
"""
render_audio.py - Audio rendering pipeline for MUSIK! compositions.

Renders MIDI files to WAV using the best available backend:
  1. FluidSynth + SoundFont (best quality)
  2. MuseScore 4 CLI (high quality, uses Muse Sounds)
  3. Pure Python synthesis (fallback - basic but works everywhere)

Usage:
  python render_audio.py input.mid              # renders to input.wav
  python render_audio.py input.mid output.wav   # explicit output path
  python render_audio.py --list-soundfonts      # show available soundfonts
"""

import sys
import os
import glob
import shutil
import struct
import subprocess
import math
import argparse
from pathlib import Path

# ---------------------------------------------------------------------------
# SoundFont search
# ---------------------------------------------------------------------------

SOUNDFONT_SEARCH_PATHS = [
    "C:/SoundFonts/*.sf2",
    "C:/SoundFonts/*.sf3",
    "C:/Program Files/FluidSynth/share/soundfonts/*.sf2",
    "C:/Program Files (x86)/FluidSynth/share/soundfonts/*.sf2",
    "C:/FluidSynth/share/soundfonts/*.sf2",
    os.path.expanduser("~/MuseScore*/Soundfonts/*.sf2"),
    os.path.expanduser("~/Documents/MuseScore*/Soundfonts/*.sf2"),
    "C:/Users/*/MuseScore*/Soundfonts/*.sf2",
    "C:/Users/*/Documents/MuseScore*/Soundfonts/*.sf2",
    # Common MuseScore 4 install location
    "C:/Program Files/MuseScore 4/share/sound/*.sf2",
    "C:/Program Files/MuseScore 4/share/sound/*.sf3",
]


def find_soundfonts():
    """Search common locations for SoundFont files. Returns list of paths."""
    found = []
    for pattern in SOUNDFONT_SEARCH_PATHS:
        found.extend(glob.glob(pattern))
    # Deduplicate, preserve order
    seen = set()
    unique = []
    for sf in found:
        norm = os.path.normpath(sf)
        if norm not in seen:
            seen.add(norm)
            unique.append(norm)
    return unique


def pick_best_soundfont(soundfonts):
    """Rank soundfonts by name preference, return best one or None."""
    preference = [
        "sonatina", "aegean", "musescore_general", "musescore general",
        "timbres of heaven", "timbres_of_heaven", "fluidr3",
    ]
    for keyword in preference:
        for sf in soundfonts:
            if keyword in os.path.basename(sf).lower():
                return sf
    return soundfonts[0] if soundfonts else None


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

def _find_fluidsynth_exe():
    """Return path to fluidsynth executable, or None."""
    # Check PATH first
    exe = shutil.which("fluidsynth")
    if exe:
        return exe
    # Check common Windows install locations
    for candidate in [
        "C:/tools/fluidsynth/bin/fluidsynth.exe",
        "C:/Program Files/FluidSynth/bin/fluidsynth.exe",
        "C:/Program Files (x86)/FluidSynth/bin/fluidsynth.exe",
    ]:
        if os.path.isfile(candidate):
            return candidate
    return None


def check_fluidsynth():
    """Return True if fluidsynth CLI is available."""
    return _find_fluidsynth_exe() is not None


def check_midi2audio():
    """Return True if midi2audio Python package is importable."""
    try:
        from midi2audio import FluidSynth  # noqa: F401
        return True
    except ImportError:
        return False


def check_musescore():
    """Return path to MuseScore executable or None."""
    # Explicit well-known paths first
    candidates = [
        "C:/Program Files/MuseScore 4/bin/MuseScore4.exe",
        "C:/Program Files (x86)/MuseScore 4/bin/MuseScore4.exe",
        "C:/Program Files/MuseScore 3/bin/MuseScore3.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    # Check PATH
    for name in ["MuseScore4", "MuseScore4.exe", "mscore", "musescore"]:
        path = shutil.which(name)
        if path:
            return path
    return None


def detect_backends():
    """Detect all available rendering backends. Returns dict of capabilities."""
    soundfonts = find_soundfonts()
    best_sf = pick_best_soundfont(soundfonts)
    has_fluidsynth = check_fluidsynth()
    has_midi2audio = check_midi2audio()
    musescore_path = check_musescore()

    return {
        "soundfonts": soundfonts,
        "best_soundfont": best_sf,
        "fluidsynth_cli": has_fluidsynth,
        "midi2audio": has_midi2audio,
        "musescore": musescore_path,
    }


def print_status(backends):
    """Print detected backends and capabilities."""
    print("=" * 60)
    print("  MUSIK! Audio Rendering Pipeline - Backend Status")
    print("=" * 60)

    # FluidSynth
    if backends["fluidsynth_cli"]:
        print("[OK]  FluidSynth CLI found on PATH")
    else:
        print("[--]  FluidSynth CLI not found")

    if backends["midi2audio"]:
        print("[OK]  midi2audio Python package available")
    else:
        print("[--]  midi2audio Python package not installed")

    # MuseScore
    if backends["musescore"]:
        print(f"[OK]  MuseScore found: {backends['musescore']}")
    else:
        print("[--]  MuseScore not found")

    # SoundFonts
    if backends["soundfonts"]:
        print(f"[OK]  {len(backends['soundfonts'])} SoundFont(s) found:")
        for sf in backends["soundfonts"]:
            marker = " <-- BEST" if sf == backends["best_soundfont"] else ""
            size_mb = os.path.getsize(sf) / (1024 * 1024) if os.path.exists(sf) else 0
            print(f"      {sf} ({size_mb:.0f} MB){marker}")
    else:
        print("[--]  No SoundFonts found")

    # Which backend will be used
    print()
    if (backends["fluidsynth_cli"] or backends["midi2audio"]) and backends["best_soundfont"]:
        print(">>> Will use: FluidSynth (best quality)")
    elif backends["musescore"]:
        print(">>> Will use: MuseScore CLI")
    else:
        print(">>> Will use: Pure Python synthesis (basic fallback)")

    print("=" * 60)


# ---------------------------------------------------------------------------
# Backend 1: FluidSynth (via midi2audio or CLI)
# ---------------------------------------------------------------------------

def render_fluidsynth(midi_path, wav_path, soundfont_path):
    """Render MIDI to WAV using FluidSynth. Tries midi2audio first, then CLI."""
    print(f"Rendering with FluidSynth...")
    print(f"  SoundFont: {soundfont_path}")

    # Try midi2audio Python wrapper first (cleaner)
    try:
        from midi2audio import FluidSynth
        fs = FluidSynth(soundfont_path)
        fs.midi_to_audio(midi_path, wav_path)
        print(f"  Done (via midi2audio): {wav_path}")
        return True
    except ImportError:
        pass
    except Exception as e:
        print(f"  midi2audio failed: {e}, trying CLI...")

    # Fall back to fluidsynth CLI
    fs_exe = _find_fluidsynth_exe()
    if fs_exe:
        cmd = [
            fs_exe, "-a", "file", "-ni",
            "-F", wav_path, "-r", "44100",
            soundfont_path, midi_path,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0 and os.path.exists(wav_path):
                print(f"  Done (via CLI): {wav_path}")
                return True
            else:
                print(f"  FluidSynth CLI failed: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print("  FluidSynth CLI timed out")
        except FileNotFoundError:
            print("  FluidSynth CLI not found")

    return False


# ---------------------------------------------------------------------------
# Backend 2: MuseScore CLI
# ---------------------------------------------------------------------------

def render_musescore(midi_path, wav_path, musescore_exe):
    """Render MIDI to WAV using MuseScore CLI."""
    print(f"Rendering with MuseScore...")
    print(f"  MuseScore: {musescore_exe}")
    cmd = [musescore_exe, "-o", wav_path, midi_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0 and os.path.exists(wav_path):
            print(f"  Done: {wav_path}")
            return True
        else:
            print(f"  MuseScore failed: {result.stderr.strip()}")
    except subprocess.TimeoutExpired:
        print("  MuseScore timed out (>5min)")
    except FileNotFoundError:
        print(f"  MuseScore not found at: {musescore_exe}")
    return False


# ---------------------------------------------------------------------------
# Backend 3: Pure Python synthesis (fallback)
# ---------------------------------------------------------------------------

def parse_midi_for_synthesis(midi_path):
    """
    Parse a MIDI file and extract note events.
    Returns list of (start_sec, duration_sec, midi_note, velocity, channel).

    Tries pretty_midi first, falls back to mido, then to a minimal parser.
    """
    # Try pretty_midi (best)
    try:
        import pretty_midi
        pm = pretty_midi.PrettyMIDI(midi_path)
        notes = []
        for instrument in pm.instruments:
            for note in instrument.notes:
                dur = note.end - note.start
                if dur > 0:
                    notes.append((note.start, dur, note.pitch, note.velocity, 0))
        if notes:
            return sorted(notes, key=lambda n: n[0])
    except ImportError:
        pass
    except Exception as e:
        print(f"  pretty_midi parse error: {e}")

    # Try mido
    try:
        import mido
        mid = mido.MidiFile(midi_path)
        notes = []
        # Track note-on/off and convert ticks to seconds
        tempo = 500000  # default 120 BPM
        ticks_per_beat = mid.ticks_per_beat
        active = {}  # (channel, note) -> (start_time, velocity)
        current_time = 0.0

        for msg in mido.merge_tracks(mid.tracks):
            dt_sec = mido.tick2second(msg.time, ticks_per_beat, tempo)
            current_time += dt_sec

            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (current_time, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    start, vel = active.pop(key)
                    dur = current_time - start
                    if dur > 0:
                        notes.append((start, dur, msg.note, vel, msg.channel))

        if notes:
            return sorted(notes, key=lambda n: n[0])
    except ImportError:
        pass
    except Exception as e:
        print(f"  mido parse error: {e}")

    # Minimal fallback: raw MIDI parsing (handles basic Type 0/1 files)
    return _parse_midi_raw(midi_path)


def _parse_midi_raw(midi_path):
    """Bare-bones MIDI parser. No dependencies. Handles basic cases."""
    notes = []
    try:
        with open(midi_path, "rb") as f:
            data = f.read()
    except IOError as e:
        print(f"  Cannot read MIDI file: {e}")
        return notes

    if data[:4] != b"MThd":
        print("  Not a valid MIDI file")
        return notes

    # Header
    header_len = struct.unpack(">I", data[4:8])[0]
    fmt, ntrks, division = struct.unpack(">HHH", data[8:14])
    ticks_per_beat = division if not (division & 0x8000) else 480

    pos = 8 + header_len
    tempo = 500000  # microseconds per beat (120 BPM)
    all_events = []

    for _ in range(ntrks):
        if data[pos:pos+4] != b"MTrk":
            break
        trk_len = struct.unpack(">I", data[pos+4:pos+8])[0]
        trk_data = data[pos+8:pos+8+trk_len]
        pos += 8 + trk_len

        tick = 0
        i = 0
        running_status = 0

        while i < len(trk_data):
            # Read variable-length delta
            delta = 0
            while i < len(trk_data):
                b = trk_data[i]
                i += 1
                delta = (delta << 7) | (b & 0x7F)
                if not (b & 0x80):
                    break
            tick += delta

            if i >= len(trk_data):
                break

            status = trk_data[i]
            if status & 0x80:
                i += 1
                running_status = status
            else:
                status = running_status

            msg_type = status & 0xF0
            channel = status & 0x0F

            if msg_type == 0x90:  # Note On
                if i + 1 < len(trk_data):
                    note = trk_data[i]
                    vel = trk_data[i + 1]
                    i += 2
                    all_events.append((tick, "on" if vel > 0 else "off", channel, note, vel))
                else:
                    break
            elif msg_type == 0x80:  # Note Off
                if i + 1 < len(trk_data):
                    note = trk_data[i]
                    vel = trk_data[i + 1]
                    i += 2
                    all_events.append((tick, "off", channel, note, vel))
                else:
                    break
            elif msg_type in (0xA0, 0xB0, 0xE0):  # 2-byte messages
                i += 2
            elif msg_type == 0xC0 or msg_type == 0xD0:  # 1-byte messages
                i += 1
            elif status == 0xFF:  # Meta event
                if i + 1 < len(trk_data):
                    meta_type = trk_data[i]
                    i += 1
                    length = 0
                    while i < len(trk_data):
                        b = trk_data[i]
                        i += 1
                        length = (length << 7) | (b & 0x7F)
                        if not (b & 0x80):
                            break
                    if meta_type == 0x51 and length == 3 and i + 2 < len(trk_data):
                        tempo = (trk_data[i] << 16) | (trk_data[i+1] << 8) | trk_data[i+2]
                    i += length
                else:
                    break
            elif status == 0xF0 or status == 0xF7:  # SysEx
                length = 0
                while i < len(trk_data):
                    b = trk_data[i]
                    i += 1
                    length = (length << 7) | (b & 0x7F)
                    if not (b & 0x80):
                        break
                i += length
            else:
                i += 1  # skip unknown

    # Convert tick-based events to time-based notes
    all_events.sort(key=lambda e: e[0])
    active = {}
    for tick, etype, ch, note, vel in all_events:
        time_sec = (tick / ticks_per_beat) * (tempo / 1_000_000)
        key = (ch, note)
        if etype == "on":
            active[key] = (time_sec, vel)
        elif etype == "off" and key in active:
            start, v = active.pop(key)
            dur = time_sec - start
            if dur > 0:
                notes.append((start, dur, note, v, ch))

    return sorted(notes, key=lambda n: n[0])


def midi_note_to_freq(note):
    """Convert MIDI note number to frequency in Hz."""
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def render_pure_python(midi_path, wav_path):
    """
    Render MIDI to WAV using pure Python synthesis.
    Generates triangle waves with simple ADSR envelope.
    Sounds basic but proves the notes are correct.
    """
    print("Rendering with pure Python synthesis (fallback)...")
    print("  (Quality: basic. Install FluidSynth + SoundFont for better results.)")

    notes = parse_midi_for_synthesis(midi_path)
    if not notes:
        print("  ERROR: Could not parse any notes from MIDI file.")
        return False

    print(f"  Parsed {len(notes)} notes")

    sample_rate = 44100
    # Determine total duration
    end_time = max(n[0] + n[1] for n in notes) + 0.5  # 0.5s tail
    total_samples = int(end_time * sample_rate)

    # Pre-allocate as list of floats (avoid numpy dependency if possible)
    try:
        import numpy as np
        use_numpy = True
        buffer = np.zeros(total_samples, dtype=np.float64)
    except ImportError:
        use_numpy = False
        buffer = [0.0] * total_samples

    print(f"  Synthesizing {end_time:.1f}s of audio...")

    for start, dur, midi_note, velocity, channel in notes:
        freq = midi_note_to_freq(midi_note)
        amp = (velocity / 127.0) * 0.3  # scale amplitude

        # ADSR envelope parameters (in seconds)
        attack = min(0.02, dur * 0.1)
        decay = min(0.05, dur * 0.2)
        sustain_level = 0.7
        release = min(0.1, dur * 0.3)
        sustain_dur = max(0, dur - attack - decay - release)

        sample_start = int(start * sample_rate)
        sample_count = int((dur + release) * sample_rate)

        for i in range(sample_count):
            idx = sample_start + i
            if idx >= total_samples:
                break

            t = i / sample_rate

            # ADSR envelope
            if t < attack:
                env = t / attack if attack > 0 else 1.0
            elif t < attack + decay:
                env = 1.0 - (1.0 - sustain_level) * ((t - attack) / decay) if decay > 0 else sustain_level
            elif t < attack + decay + sustain_dur:
                env = sustain_level
            else:
                rel_t = t - (attack + decay + sustain_dur)
                env = sustain_level * (1.0 - rel_t / release) if release > 0 else 0.0
                env = max(0.0, env)

            # Triangle wave (softer than square, richer than sine)
            phase = (freq * t) % 1.0
            if phase < 0.25:
                sample = 4.0 * phase
            elif phase < 0.75:
                sample = 2.0 - 4.0 * phase
            else:
                sample = -4.0 + 4.0 * phase

            buffer[idx] += sample * amp * env

    # Normalize to prevent clipping
    if use_numpy:
        peak = np.max(np.abs(buffer))
        if peak > 0:
            buffer = buffer / peak * 0.9
        # Convert to 16-bit PCM
        pcm = (buffer * 32767).astype(np.int16)
        pcm_bytes = pcm.tobytes()
    else:
        peak = max(abs(s) for s in buffer) if buffer else 1.0
        if peak > 0:
            scale = 0.9 / peak
            buffer = [s * scale for s in buffer]
        pcm_bytes = b"".join(
            struct.pack("<h", max(-32767, min(32767, int(s * 32767))))
            for s in buffer
        )

    # Write WAV file (mono, 16-bit, 44100 Hz)
    _write_wav(wav_path, pcm_bytes, sample_rate, channels=1, bits=16)

    size_mb = os.path.getsize(wav_path) / (1024 * 1024)
    print(f"  Done: {wav_path} ({size_mb:.1f} MB, {end_time:.1f}s)")
    return True


def _write_wav(path, pcm_data, sample_rate, channels, bits):
    """Write a WAV file from raw PCM bytes. No dependencies."""
    bytes_per_sample = bits // 8
    data_size = len(pcm_data)
    with open(path, "wb") as f:
        # RIFF header
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        # fmt chunk
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))  # chunk size
        f.write(struct.pack("<H", 1))   # PCM format
        f.write(struct.pack("<H", channels))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * channels * bytes_per_sample))
        f.write(struct.pack("<H", channels * bytes_per_sample))
        f.write(struct.pack("<H", bits))
        # data chunk
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(pcm_data)


# ---------------------------------------------------------------------------
# Installation help
# ---------------------------------------------------------------------------

def print_install_help():
    """Print instructions for installing FluidSynth and SoundFonts."""
    print("""
==============================================================
  HOW TO GET BETTER AUDIO QUALITY
==============================================================

The pure Python fallback works but sounds basic.
For good quality, install FluidSynth + a SoundFont:

--- FluidSynth ---
  1. Download from: https://github.com/FluidSynth/fluidsynth/releases
     (Get the latest Windows zip, e.g. fluidsynth-2.x.x-win10-x64.zip)
  2. Extract to C:\\FluidSynth\\
  3. Add C:\\FluidSynth\\bin to your PATH
  4. Verify:  fluidsynth --version

  Python package:
    pip install midi2audio

--- SoundFonts (pick one) ---
  Best orchestral (free):
    - MuseScore_General.sf2 (~350 MB) - ships with MuseScore 4
      https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/
    - FluidR3_GM.sf2 (~140 MB) - classic, lighter
      https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.htm
    - Sonatina Symphonic Orchestra (~400 MB) - best free orchestral
      https://github.com/MatthewCallis/Sonatina-Symphonic-Orchestra
    - Timbres of Heaven (~400 MB) - excellent piano/strings

  Place .sf2 files in:  C:\\SoundFonts\\

--- MuseScore (alternative) ---
  Download MuseScore 4: https://musescore.org/en/download
  Install "Muse Sounds" for high-quality rendering.
  CLI usage:  MuseScore4.exe -o output.wav input.mid

==============================================================
""")


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render(midi_path, wav_path=None, force_backend=None):
    """
    Render a MIDI file to WAV using the best available backend.

    Args:
        midi_path: Path to input .mid file
        wav_path: Path to output .wav file (default: same name as input)
        force_backend: "fluidsynth", "musescore", or "python" (default: auto)

    Returns:
        True if rendering succeeded, False otherwise.
    """
    midi_path = os.path.abspath(midi_path)
    if not os.path.exists(midi_path):
        print(f"ERROR: MIDI file not found: {midi_path}")
        return False

    if wav_path is None:
        wav_path = os.path.splitext(midi_path)[0] + ".wav"
    wav_path = os.path.abspath(wav_path)

    print(f"Input:  {midi_path}")
    print(f"Output: {wav_path}")
    print()

    backends = detect_backends()

    # Try backends in order of quality
    if force_backend != "python":
        # 1. FluidSynth
        if force_backend in (None, "fluidsynth"):
            if (backends["fluidsynth_cli"] or backends["midi2audio"]) and backends["best_soundfont"]:
                if render_fluidsynth(midi_path, wav_path, backends["best_soundfont"]):
                    return True
                print("  FluidSynth failed, trying next backend...")

        # 2. MuseScore
        if force_backend in (None, "musescore"):
            if backends["musescore"]:
                if render_musescore(midi_path, wav_path, backends["musescore"]):
                    return True
                print("  MuseScore failed, trying next backend...")

    # 3. Pure Python fallback
    print()
    success = render_pure_python(midi_path, wav_path)
    if success:
        print()
        print_install_help()
    return success


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MUSIK! Audio Rendering Pipeline - MIDI to WAV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python render_audio.py input.mid
  python render_audio.py input.mid output.wav
  python render_audio.py --list-soundfonts
  python render_audio.py input.mid --backend python
        """,
    )
    parser.add_argument("input", nargs="?", help="Input MIDI file (.mid)")
    parser.add_argument("output", nargs="?", help="Output WAV file (default: input.wav)")
    parser.add_argument("--list-soundfonts", action="store_true",
                        help="List available SoundFonts and backends")
    parser.add_argument("--backend", choices=["fluidsynth", "musescore", "python"],
                        help="Force a specific backend")

    args = parser.parse_args()

    if args.list_soundfonts:
        backends = detect_backends()
        print_status(backends)
        if not backends["soundfonts"]:
            print()
            print_install_help()
        return 0

    if not args.input:
        parser.print_help()
        return 1

    if not os.path.exists(args.input):
        print(f"ERROR: File not found: {args.input}")
        return 1

    success = render(args.input, args.output, force_backend=args.backend)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
