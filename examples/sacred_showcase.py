"""Sacred Composer Showcase — multiple high-scoring compositions.

Demonstrates the CompositionBuilder producing quality output
across different keys, patterns, and moods.
"""

from sacred_composer import *
from sacred_composer.core import GM_INSTRUMENTS


def build_and_evaluate(title, key, tempo, bars, melody_pattern, melody_seed,
                       bass_seed, rhythm_pattern="euclidean_5_8", n_sections=5):
    """Build a piece and evaluate it."""
    labels = ["I", "II", "III", "IV", "V"][:n_sections]

    piece = (
        CompositionBuilder(key=key, tempo=tempo, bars=bars, title=title)
        .form(pattern="fibonacci", n_sections=n_sections, labels=labels)
        .melody(pattern=melody_pattern, instrument="violin", octave_range=(4, 5),
                rhythm_pattern=rhythm_pattern, base_duration=0.5, seed=melody_seed)
        .bass(pattern="harmonic_series", instrument="cello", octave_range=(2, 3),
              rhythm_pattern="euclidean_3_8", base_duration=2.0, seed=bass_seed)
        .build()
    )

    safe_name = title.lower().replace(" ", "_").replace("'", "")
    mid_file = f"showcase_{safe_name}.mid"
    piece.render(mid_file)

    result = evaluate_composition(piece, verbose=False)

    return piece, result, mid_file


def main():
    print("=" * 70)
    print("  SACRED COMPOSER SHOWCASE — Constraint-Aware Compositions")
    print("=" * 70)

    pieces = [
        # (title, key, tempo, bars, melody_pattern, melody_seed, bass_seed, rhythm)
        ("Sacred Offering in D minor", "D_minor", 72, 32,
         "infinity_series", 0, 10, "euclidean_5_8"),
        ("Fibonacci Nocturne in C minor", "C_minor", 60, 32,
         "fibonacci", 5, 15, "euclidean_5_8"),
        ("Golden Spiral in A minor", "A_minor", 66, 32,
         "golden_spiral", 3, 7, "euclidean_5_8"),
        ("Logistic Dreams in G minor", "G_minor", 76, 32,
         "logistic", 1, 12, "euclidean_5_8"),
        ("Infinity in E minor", "E_minor", 68, 32,
         "infinity_series", 8, 20, "euclidean_7_12"),
    ]

    results = []
    for args in pieces:
        title = args[0]
        piece, result, mid_file = build_and_evaluate(*args)
        info = piece.info()
        score = result["final_score"]
        l1 = "PASS" if result["level1_pass"] else f"FAIL({result['rule_violations']}v)"
        results.append((title, score, l1, info))

        print(f"\n  {title}")
        print(f"    Score: {score:.1f}/100  L1: {l1}")
        print(f"    Notes: {info['total_notes']}, Duration: {info['duration_seconds']:.1f}s")
        print(f"    File:  {mid_file}")

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    scores = [r[1] for r in results]
    print(f"\n  Pieces:   {len(results)}")
    print(f"  Avg:      {sum(scores)/len(scores):.1f}")
    print(f"  Best:     {max(scores):.1f}")
    print(f"  Worst:    {min(scores):.1f}")
    print(f"  Range:    {min(scores):.1f} - {max(scores):.1f}")
    print()

    for title, score, l1, info in sorted(results, key=lambda r: -r[1]):
        print(f"  {score:5.1f}  {l1:12s}  {title}")
    print()

    # Render the best piece to all formats
    best = max(results, key=lambda r: r[1])
    best_title = best[0]
    print(f"  Best piece: {best_title} ({best[1]:.1f}/100)")
    print(f"  Rendering best to .ly and .wav...")

    # Rebuild the best
    best_args = pieces[results.index(best)]
    best_piece, _, _ = build_and_evaluate(*best_args)
    safe = best_title.lower().replace(" ", "_").replace("'", "")
    best_piece.render(f"showcase_{safe}.ly")
    best_piece.render(f"showcase_{safe}.wav")

    import os
    wav_size = os.path.getsize(f"showcase_{safe}.wav") / (1024 * 1024)
    print(f"  WAV: {wav_size:.1f} MB")
    print()


if __name__ == "__main__":
    main()
