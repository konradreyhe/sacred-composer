# Sacred Geometry Vol. 1 — Launch Copy

## Show HN Post

**Title:** Show HN: I made an album where every note comes from a math equation

**Body:**

I built a deterministic music composition engine in Python that turns
mathematical patterns into classical-rule-compliant music. No ML, no
randomness — every note is traceable to its generating equation.

Sacred Geometry Vol. 1 is a 10-track album where each track is driven
by a different mathematical structure:

- Fibonacci sequence
- Nørgård's infinity series (1959)
- Golden spiral (phi-derived contour)
- Harmonic series (overtone physics)
- Logistic map at r=3.7 (edge of chaos)
- Mandelbrot set boundary walk
- Rössler strange attractor
- Cantor's middle-third removal
- Zipf's law (power-law distribution)

The engine maps these patterns to pitch, rhythm, and dynamics, then
applies classical music constraints (voice leading, leap recovery,
cadence placement) so the output follows actual music theory rules.

Track 6 features a "Goosebump Engine" — a deliberate appoggiatura
placed at the golden-section climax, based on Sloboda's 1991 research
on physiological responses to music. It's the only moment in the album
where the system intentionally violates its own rules.

The entire album is reproducible from a JSON file with 10 seeds.
`python render_masters.py` regenerates it bit-identically.

[Spotify link] | [GitHub] | [YouTube visualizations]

Tech: Python, NumPy, FluidSynth, Remotion (for videos). ~8,600 lines.
No dependencies on any ML framework.

---

## Twitter/X Thread

**1/7**
I made an album where every note comes from a math equation.

No AI. No randomness. Pure mathematical patterns → classical music.

Sacred Geometry Vol. 1 is out now. 10 tracks. 10 equations. Here's how it works: 🧵

**2/7**
Each track is driven by a different mathematical structure:

🔢 Fibonacci sequence
🌀 Golden spiral
📐 Mandelbrot set
🔄 Rössler strange attractor
📊 Zipf's law
🔀 Thue-Morse sequence
...and 4 more

The engine maps patterns to pitch, rhythm, and dynamics.

**3/7**
But raw math sounds terrible as music. So the engine applies classical
music constraints:

- Voice leading (no parallel fifths)
- Leap recovery
- Phrase structure
- Cadence placement

Result: music that follows real theory rules, generated from equations.

**4/7**
Track 6 has a "Goosebump Engine."

Based on Sloboda's 1991 research on why music gives us chills, it
places a deliberate appoggiatura at the golden-section climax.

It's the only moment the system intentionally breaks its own rules.

**5/7**
The entire album is reproducible from a JSON file with 10 numbers.

```json
{"seed": 2, "key": "E_minor", "pattern": "mandelbrot"}
```

Run one command. Get the exact same album. Every time.

**6/7**
Tech stack:
- Python (~8,600 lines)
- NumPy for pattern generation
- FluidSynth for audio rendering
- Remotion for music videos
- No ML frameworks. Zero.

**7/7**
Sacred Geometry Vol. 1 is on [Spotify/platform].

The code is open source: [GitHub link]

If you've ever wondered what a Mandelbrot set sounds like, now you know.

---

## Reddit Posts

### r/generative

**Title:** Sacred Geometry Vol. 1 — a 9-track album generated entirely from mathematical patterns

I built a deterministic composition engine in Python and used it to
create a full album. Each track maps a different mathematical structure
(Fibonacci, Mandelbrot, Rössler attractor, etc.) to pitch, rhythm,
and dynamics, then applies classical music constraints so it sounds
like actual music.

The engine evaluates each composition against 14 music-theory metrics
and scores it. All 9 tracks pass with zero rule violations.

[link] | Code is open source.

### r/algorave

**Title:** Deterministic generative album — 9 math patterns, classical constraints, reproducible from a JSON seed file

Not quite algorave (it's deterministic, not live), but thought this
community would appreciate the approach. Built a Python engine that
turns mathematical sequences into constrained classical compositions.
Fibonacci, chaos theory, fractals, power laws → violin and cello.

The "Goosebump Engine" on Track 6 deliberately places an appoggiatura
at the golden-section climax based on music psychology research.

### r/musictheory

**Title:** I built a system that generates music from math equations while following voice-leading rules — here's what I learned about why constraints make generative music better

The interesting finding: unconstrained mathematical patterns sound
terrible as music. But apply classical constraints (no parallel fifths,
leap recovery, phrase boundaries, cadence placement) and the same
patterns become surprisingly listenable. The constraints don't fight
the math — they channel it.

Album has 9 tracks, each from a different equation. All pass a 14-metric
evaluation framework with zero rule violations.
