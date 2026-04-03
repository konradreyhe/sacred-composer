"""Sacred Composer CLI — generate music from mathematical patterns.

Usage:
    python -m sacred_composer --key D_minor --tempo 72 --bars 32 --output piece.mid
    python -m sacred_composer --consciousness meditation --output meditation.mid
    python -m sacred_composer --random --output surprise.mid
    python -m sacred_composer --list-patterns
"""

import argparse
import json
import random
import sys
import time

from sacred_composer.builder import CompositionBuilder
from sacred_composer.constants import SCALES, NOTE_NAMES

# ---------------------------------------------------------------------------
# Colour helpers (graceful fallback when colorama is absent)
# ---------------------------------------------------------------------------

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init()
    _GREEN = Fore.GREEN
    _CYAN = Fore.CYAN
    _YELLOW = Fore.YELLOW
    _RED = Fore.RED
    _DIM = Style.DIM
    _RESET = Style.RESET_ALL
except ImportError:
    _GREEN = _CYAN = _YELLOW = _RED = _DIM = _RESET = ""


def _info(msg: str) -> None:
    print(f"{_GREEN}[sacred]{_RESET} {msg}")


def _warn(msg: str) -> None:
    print(f"{_YELLOW}[warn]{_RESET} {msg}", file=sys.stderr)


def _error(msg: str) -> None:
    print(f"{_RED}[error]{_RESET} {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Listing helpers
# ---------------------------------------------------------------------------

PATTERN_NAMES = list(CompositionBuilder.PATTERN_GENERATORS.keys())
CONSCIOUSNESS_NAMES = list(CompositionBuilder.CONSCIOUSNESS_PRESETS.keys())
SCALE_NAMES = list(SCALES.keys())
NOTE_NAME_LIST = list(dict.fromkeys(NOTE_NAMES.keys()))  # unique, ordered


def _list_patterns() -> None:
    _info("Available melody/bass patterns:")
    for p in PATTERN_NAMES:
        print(f"  {_CYAN}{p}{_RESET}")


def _list_scales() -> None:
    _info("Available scale types:")
    for s in SCALE_NAMES:
        print(f"  {_CYAN}{s}{_RESET}")
    print()
    _info(f"Root notes: {', '.join(NOTE_NAME_LIST)}")
    print(f"  Combine as {_CYAN}Root_scale{_RESET}, e.g. D_minor, F#_harmonic_minor")


def _list_consciousness() -> None:
    _info("Consciousness presets:")
    for name, preset in CompositionBuilder.CONSCIOUSNESS_PRESETS.items():
        print(f"  {_CYAN}{name:15s}{_RESET} "
              f"tempo={preset['tempo']}  key={preset['key']}  bars={preset['bars']}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="sacred-composer",
        description="Generate music from mathematical patterns.",
    )

    # Generation parameters
    parser.add_argument("--key", default="D_minor",
                        help="Musical key (e.g. D_minor, C_major, F#_harmonic_minor)")
    parser.add_argument("--tempo", type=int, default=72,
                        help="Tempo in BPM (default: 72)")
    parser.add_argument("--bars", type=int, default=32,
                        help="Number of bars (default: 32)")
    parser.add_argument("--pattern", default="infinity_series",
                        help="Melody pattern (see --list-patterns)")
    parser.add_argument("--bass-pattern", default="harmonic_series",
                        help="Bass pattern (default: harmonic_series)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed for reproducibility")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file (.mid, .wav, .ly, .musicxml)")

    # Modes
    parser.add_argument("--harmony", action="store_true",
                        help="Enable chord-first composition")
    parser.add_argument("--consciousness", choices=CONSCIOUSNESS_NAMES,
                        metavar="PRESET",
                        help="Use a consciousness preset "
                             f"({', '.join(CONSCIOUSNESS_NAMES)})")
    parser.add_argument("--random", action="store_true",
                        help="Randomise all parameters")
    parser.add_argument("--adaptive", metavar="FILE",
                        help="Generate adaptive soundtrack from JSON state file")

    # Info / listing
    parser.add_argument("--list-patterns", action="store_true",
                        help="List available melody patterns")
    parser.add_argument("--list-scales", action="store_true",
                        help="List available scales")
    parser.add_argument("--list-consciousness", action="store_true",
                        help="List consciousness presets")
    parser.add_argument("--info", action="store_true",
                        help="Print composition info without rendering")

    args = parser.parse_args()

    # ---- Listing commands (no output file needed) ----
    if args.list_patterns:
        _list_patterns()
        return
    if args.list_scales:
        _list_scales()
        return
    if args.list_consciousness:
        _list_consciousness()
        return

    # ---- Adaptive mode ----
    if args.adaptive:
        if not args.output:
            _error("--output is required with --adaptive")
            sys.exit(1)
        _generate_adaptive(args)
        return

    # ---- Normal generation requires --output ----
    if not args.output:
        _error("--output / -o is required (e.g. --output piece.mid)")
        sys.exit(1)

    # ---- Random mode ----
    if args.random:
        rng = random.Random()
        args.key = rng.choice(NOTE_NAME_LIST[:12]) + "_" + rng.choice(SCALE_NAMES)
        args.tempo = rng.randint(50, 140)
        args.bars = rng.choice([16, 24, 32, 48, 64])
        args.pattern = rng.choice(PATTERN_NAMES)
        args.bass_pattern = rng.choice(PATTERN_NAMES)
        args.seed = rng.randint(0, 9999)
        _info(f"Random: key={args.key} tempo={args.tempo} bars={args.bars} "
              f"pattern={args.pattern} seed={args.seed}")

    # ---- Build ----
    _info("Building composition...")

    if args.consciousness:
        builder = CompositionBuilder(title=f"Sacred — {args.consciousness}")
        builder.consciousness(args.consciousness)
    else:
        builder = CompositionBuilder(
            key=args.key,
            tempo=args.tempo,
            bars=args.bars,
            title="Sacred Composition",
        )
        builder.form(pattern="fibonacci", n_sections=5)
        builder.melody(pattern=args.pattern, seed=args.seed)
        builder.bass(pattern=args.bass_pattern, seed=args.seed + 10)
        builder.drone()

    if args.harmony:
        builder.harmony(seed=args.seed)

    try:
        piece = builder.build()
    except Exception as exc:
        _error(f"Build failed: {exc}")
        if args.random:
            _warn("Tip: some random parameter combinations can trigger edge cases. Try again.")
        sys.exit(1)

    # ---- Info ----
    _print_info(piece)

    if args.info:
        return

    # ---- Render ----
    output = args.output
    is_wav = output.endswith(".wav")

    if is_wav:
        _info(f"Rendering WAV (this may take a moment)...")
        t0 = time.time()

    piece.render(output)

    if is_wav:
        elapsed = time.time() - t0
        _info(f"WAV rendered in {elapsed:.1f}s")

    _info(f"Written: {_CYAN}{output}{_RESET}")


def _print_info(piece) -> None:
    """Print summary information about the composition."""
    score = piece.score
    total_notes = sum(len(v.notes) for v in score.voices)
    duration_beats = score.duration
    duration_sec = duration_beats / piece.tempo * 60
    minutes = int(duration_sec // 60)
    seconds = int(duration_sec % 60)

    _info(f"Tempo:    {piece.tempo} BPM")
    _info(f"Voices:   {len(score.voices)}")
    for v in score.voices:
        print(f"          {_DIM}{v.name} ({len(v.notes)} notes){_RESET}")
    _info(f"Notes:    {total_notes}")
    _info(f"Duration: {duration_beats:.0f} beats  ({minutes}:{seconds:02d})")


def _generate_adaptive(args) -> None:
    """Generate adaptive soundtrack from a JSON state file."""
    from sacred_composer.adaptive import GameState, generate_soundtrack

    try:
        with open(args.adaptive, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        _error(f"Cannot read state file: {exc}")
        sys.exit(1)

    # Expected format: list of {"beat": float, "state": {...}} objects
    states: list[tuple[float, GameState]] = []
    for entry in data:
        beat = float(entry.get("beat", 0))
        s = entry.get("state", {})
        gs = GameState(
            danger=s.get("danger", 0.0),
            energy=s.get("energy", 0.5),
            environment=s.get("environment", "forest"),
            time_of_day=s.get("time_of_day", 12.0),
            health=s.get("health", 1.0),
            speed=s.get("speed", 0.5),
        )
        states.append((beat, gs))

    _info(f"Loaded {len(states)} state(s) from {args.adaptive}")
    piece = generate_soundtrack(states, seed=args.seed)
    _print_info(piece)

    is_wav = args.output.endswith(".wav")
    if is_wav:
        _info("Rendering WAV (this may take a moment)...")
        t0 = time.time()

    piece.render(args.output)

    if is_wav:
        elapsed = time.time() - t0
        _info(f"WAV rendered in {elapsed:.1f}s")

    _info(f"Written: {_CYAN}{args.output}{_RESET}")


if __name__ == "__main__":
    main()
