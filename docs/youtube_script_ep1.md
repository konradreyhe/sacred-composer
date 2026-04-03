# Episode 1: I Made Music from the Fibonacci Sequence (and it sounds beautiful)

**Channel:** Music from Mathematics
**Format:** 8-10 minute narrated video with screen recordings and visualizations
**Target audience:** Vi Hart / 3Blue1Brown viewers — people who love seeing hidden structure revealed
**Tone:** Conversational, wonder-driven, technically honest. Never condescending.

---

## HOOK (0:00 - 0:30)

**[VISUAL: Black screen. A single piano note fades in. Then another. A melody builds — the Fibonacci Nocturne in C minor.]**

**NARRATION:**

What if I told you that the same pattern that arranges sunflower seeds, shapes hurricane arms, and spirals galaxies... also creates *this*.

**[VISUAL: Cut to the MIDI piano roll as the piece plays. Numbers appear beside each note: 1, 1, 2, 3, 5, 8, 13...]**

Every single note in this piece comes from one mathematical sequence. And you can trace every note back to the number that made it.

No AI prompt. No randomness. Just a pattern from nature, turned into sound.

**[VISUAL: Title card — "Music from Mathematics" — over the continuing melody.]**

> **SPEAKER NOTES:** Keep the hook tight. The music does the selling. Let the Fibonacci Nocturne play for a full 6-8 seconds before speaking over it so the audience hears it first and asks "what is that?" before you explain.
>
> **B-ROLL:** Spiraling sunflower close-up, satellite hurricane footage, galaxy rotation — quick 1-second cuts synced to the beat.

---

## THE PATTERN (0:30 - 2:30)

**[VISUAL: White background. Numbers appear one at a time, hand-drawn style.]**

**NARRATION:**

The Fibonacci sequence. You probably know it. Start with 1 and 1. Add the last two numbers to get the next one.

**[VISUAL: 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144... each number pops in as it's spoken.]**

One, one, two, three, five, eight, thirteen, twenty-one...

Now here's where it gets interesting. Divide each number by the one before it.

**[VISUAL: Fractions appear — 1/1, 2/1, 3/2, 5/3, 8/5, 13/8 — converging toward 1.618...]**

The ratio converges. It settles on 1.618... — the golden ratio. Phi.

**[VISUAL: Animated golden rectangle subdividing, golden spiral emerging.]**

This ratio is everywhere. Not because the universe is mystical — because it's a consequence of growth by addition. Things that grow by adding what came before end up here.

**[VISUAL: Quick montage — sunflower seed head with spiral lines overlaid, pinecone top-down with Fibonacci spirals counted, nautilus shell cross-section.]**

Sunflower seeds: 34 spirals one way, 55 the other. Both Fibonacci numbers. Pinecones: 8 and 13. The pattern isn't imposed — it emerges, because this is how efficient packing works.

**[Beat. Music fades back in underneath.]**

But here's the question nobody seems to ask: can you *hear* it?

> **SPEAKER NOTES:** This section needs to feel brisk, not like a lecture. The audience likely knows Fibonacci already. The goal is to move quickly enough that they don't feel talked down to, but slowly enough that the golden ratio convergence lands. The "can you hear it?" is the pivot — lean into it.
>
> **B-ROLL:** Nature footage (sunflowers, pinecones, nautilus). For the ratio convergence, animate a number line with the fractions bouncing back and forth, narrowing toward phi. Consider a Manim-style animation here.

---

## MAKING IT MUSIC (2:30 - 5:00)

**[VISUAL: Screen recording — a clean terminal or VS Code. The font is large enough to read on mobile.]**

**NARRATION:**

Alright, let's turn it into music. I built a Python library called Sacred Composer. Here's what it looks like.

**[VISUAL: Type out the code as it's narrated. Each line appears, then its output.]**

```python
from sacred_composer import *

fib = FibonacciSequence()
values = fib.generate(16)
print(values)
```

**[VISUAL: Output appears — `[1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]`]**

Sixteen Fibonacci numbers. Just raw data. Now I map them to pitch.

```python
melody = to_pitch(values, scale="D_minor", octave_range=(4, 5))
```

**[VISUAL: The numbers transform into note names — D4, D4, E4, F4, A4, C5... A piano roll lights up the notes.]**

Each value wraps into a D minor scale. Small numbers cluster near the bottom; as Fibonacci grows, the melody reaches upward. That's not me choosing notes — that's the sequence deciding.

Now rhythm. Fibonacci controls *when* notes play, not just *which* notes.

```python
durations = to_rhythm(values, strategy="proportional", base_duration=0.5)
```

**[VISUAL: A timeline appears. Short notes for 1, 1, 2. Longer notes for 8, 13. The proportions are visible.]**

Small Fibonacci numbers are quick. Large ones sustain. The rhythm breathes the way the sequence breathes — slowly accelerating, then stretching.

And form. The *structure* of the piece is also Fibonacci.

```python
sections = to_form(values, total_bars=34)
```

**[VISUAL: A colored bar chart shows sections — 1 bar, 1 bar, 2 bars, 3 bars, 5 bars, 8 bars, 13 bars. The bars light up as each section plays.]**

Sections of 1, 1, 2, 3, 5, 8, and 13 bars. Thirty-four bars total — itself a Fibonacci number. Bartok did this in 1936 with Music for Strings, Percussion and Celesta. Same idea. But now the code does it for you.

**[VISUAL: Piece plays in full. MIDI piano roll scrolls. Section boundaries are marked. 8-10 seconds of uninterrupted listening.]**

Let it play. That's Fibonacci. Every note traceable. Every duration justified. Every section boundary mathematically determined.

> **SPEAKER NOTES:** This is the core of the video and the most likely moment for viewer drop-off. Keep the energy moving by making each code block feel like a reveal, not a tutorial. The code is minimal on purpose — three lines to go from numbers to music. Pause after "let it play" and give the music 8-10 full seconds. Silence from the narrator here is powerful.
>
> **B-ROLL:** Screen recording of actual Sacred Composer code running. Use a dark theme editor. Overlay the piano roll visualization (the `viz/` module or a DAW view). For the form section, animate a horizontal bar chart in Fibonacci colors.

---

## GOING DEEPER (5:00 - 7:00)

**[VISUAL: The Fibonacci piano roll shrinks into a corner. New visualizations appear.]**

**NARRATION:**

But Fibonacci is just one pattern. Sacred Composer has twenty-three generators. Let me show you two more.

**[VISUAL: A Lorenz attractor — the butterfly shape — draws itself in 3D. Points trace the two lobes.]**

This is the Lorenz attractor. It's from chaos theory — a system of three differential equations that Edward Lorenz discovered in 1963 while modeling weather. The trajectory never repeats, but it's completely deterministic. Same starting point, same path every time.

```python
lorenz = LorenzAttractor(sigma=10, rho=28, beta=8/3)
pitches = to_pitch(lorenz.generate(200), scale="A_minor")
```

**[VISUAL: The 3D attractor rotates slowly. As each point lights up, a note plays. The melody swoops between two pitch regions — mirroring the two lobes of the attractor.]**

Hear how the melody orbits between two pitch centers? That's the two lobes of the butterfly. The music literally traces the shape of chaos.

**[VISUAL: Transition — a grid of black and white cells appears. Rule 110 cellular automaton evolves row by row.]**

Now cellular automata. Simple rules, complex behavior. Each row is a generation. Black cell or white cell — alive or dead.

```python
ca = CellularAutomata(rule=110)
texture = to_pitch(ca.generate(64), scale="C_minor")
```

**[VISUAL: The automaton grid grows. Each row triggers a chord or cluster. The texture is dense, shimmering, unpredictable but structured.]**

Rule 110 is Turing complete — it can compute anything. And it sounds like *this*. Emergent complexity from one rule and two states.

> **SPEAKER NOTES:** The Lorenz section is the visual highlight. If budget allows, render a proper 3D attractor (Manim or Blender) and sync the note triggers to the point positions. For cellular automata, show the grid building in real time, row by row, with sound on each row. The contrast between Lorenz (smooth, swooping) and CA (pointillistic, grid-like) should be audible.
>
> **B-ROLL:** Lorenz attractor 3D render (colored by velocity or time). CA grid animation. Weather radar imagery (brief) when mentioning Lorenz's weather modeling.

---

## THE BIG PICTURE (7:00 - 8:30)

**[VISUAL: A grid of eight album-cover-style cards, each representing a showcase composition. Each card shows the pattern name and a small visualization.]**

**NARRATION:**

This is Sacred Composer. An open-source Python library I built where the code *is* the score.

**[VISUAL: The showcase grid. Each card briefly highlights — "Harmony Cathedral: Infinity Series + Golden Spiral," "Mandelbrot Meditation: Fractal Boundary Walk + Cantor Set Rhythm," etc.]**

Eight showcase compositions. Each one uses different patterns. The Infinity Series — Per Norgard's fractal sequence from his symphonies. Mandelbrot boundary walks. Rossler attractors. L-system grammars. Pink noise. Euclidean rhythms.

**[VISUAL: A scrolling list of all 23 pattern generators, with tiny icons — spirals, fractals, grids, waveforms.]**

Twenty-three pattern generators in total. Fibonacci, Lorenz, cellular automata — those you've seen. But also: the digits of pi as melody. Shakespeare's vowel patterns as rhythm. Planetary orbital periods as polyrhythm. Indian ragas. Arabic maqam. Gamelan tunings. Tuvan throat singing overtone series.

**[VISUAL: A short montage — 2 seconds each — of different compositions playing, each with its pattern visualization beside the piano roll.]**

The same architecture handles all of them. Generate raw values, map to pitch or rhythm or dynamics, combine into voices, render to MIDI or audio. And every note in every piece traces back to the pattern that made it.

**[VISUAL: A dependency graph — Pattern -> Mapper -> Combiner -> Renderer — animates into place.]**

No black boxes. No hidden randomness. The code is the composition, and the composition is the code.

> **SPEAKER NOTES:** This section sells the scope without getting lost in details. The grid of eight compositions is the visual anchor — it says "this isn't a one-trick demo, it's a real system." Don't linger on any single piece; the montage should feel abundant. The architecture diagram at the end is for the programmers in the audience — keep it on screen only briefly.
>
> **B-ROLL:** Showcase MIDI files playing in a DAW. Pattern visualizations from the `viz/` module. GitHub repo scrolling (briefly). The architecture diagram as a clean animated graphic.

---

## CALL TO ACTION (8:30 - 9:00)

**[VISUAL: Terminal — `pip install sacred-composer`. Then the Streamlit playground loading in a browser.]**

**NARRATION:**

You can try it right now.

```
pip install sacred-composer
```

Or play with it in your browser — there's a Streamlit playground where you can pick a pattern, tweak the parameters, and hear the result instantly.

**[VISUAL: Quick demo of the playground — select "Fibonacci," drag a slider, hit play, hear the change.]**

Everything is on GitHub. Every note is traceable. Every composition is reproducible. The code is the score.

**[VISUAL: Channel subscribe animation. End screen with two video placeholders.]**

Next episode: what happens when you feed a Lorenz attractor into a string quartet? Spoiler — it sounds like weather feels.

**[VISUAL: The Fibonacci Nocturne fades back in as the end screen appears. Hold for 15 seconds.]**

> **SPEAKER NOTES:** Keep the CTA fast and non-pushy. The "pip install" line and the playground are the two conversion points — make sure both are clearly visible. The teaser for Episode 2 should be genuinely intriguing, not clickbait. Let the music carry the outro.
>
> **B-ROLL:** Terminal recording of the install. Streamlit playground screen capture (pre-record a smooth demo, don't do it live). GitHub repo page. End screen template with subscribe button and next-episode placeholder.

---

## PRODUCTION NOTES

**Total runtime:** ~9 minutes
**Word count (narration):** ~1,450 words at natural pacing

### Music needed
- **Fibonacci Nocturne in C minor** — the primary piece. Generate at tempo 60, 32 bars, using `CompositionBuilder` with Fibonacci melody, harmonic series bass. This must sound polished; consider rendering through a decent piano VST.
- **Lorenz piece in A minor** — 15-20 second excerpt. Swooping, two-center melody.
- **Cellular automata texture in C minor** — 10-15 second excerpt. Dense, pointillistic.
- **Showcase montage clips** — 2-3 seconds each of 4-5 different compositions.

### Visuals needed
- Fibonacci sequence animation (Manim or After Effects)
- Golden ratio convergence animation
- Nature footage: sunflower, pinecone, nautilus (stock or CC-licensed)
- Lorenz attractor 3D render (Manim, Blender, or matplotlib)
- Rule 110 cellular automaton grid animation
- Screen recordings of Sacred Composer code running
- MIDI piano roll visualizations for each piece
- Showcase composition grid (8 cards, designed)
- Pattern generator list (23 items, scrolling)
- Architecture diagram animation
- Streamlit playground demo recording

### Episode 2 teaser setup
The Lorenz attractor piece should sound incomplete or transitional at the end of its brief appearance here, creating genuine curiosity about what a full Lorenz composition sounds like with orchestral voices.
