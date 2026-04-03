# Sacred Composer: A Transparent Mathematical Pattern-to-Music System for Composition and Education

**Author:** Konrad Reyhe

**Conference:** BRIDGES 2026 -- Mathematics, Art, Music, Architecture, Culture
**Location:** Galway, Ireland, August 5--8, 2026
**Category:** Regular Paper (6--8 pages)
**Submission Deadline:** February 1, 2026

---

## Abstract

Algorithmic composition has long promised to make the deep relationship between mathematics and music audible, yet current systems fall into two unsatisfying camps. Neural approaches (Magenta, MusicGen, AIVA) produce convincing surfaces but are opaque: no listener can trace a note back to a generative principle. Rule-based systems (Cope's EMI, TidalCycles) offer transparency but encode musical idioms rather than the underlying mathematical structures that give rise to them. Neither camp fulfills the Pythagorean aspiration of hearing mathematics as music in a way that is simultaneously rigorous, traceable, and musically compelling.

We present *Sacred Composer*, an open-source Python library in which mathematical and natural patterns are first-class compositional objects. The system implements 23 pattern generators -- including Fibonacci sequences, harmonic series, Lorenz attractors, cellular automata, golden spirals, L-systems, Euclidean rhythms, and 1/f noise -- each conforming to a common `Pattern` protocol that yields raw numeric values with no inherent musical meaning. Explicit mapper functions (`to_pitch`, `to_rhythm`, `to_dynamics`) project these values into musical parameter spaces, while combiners (`canon`, `phase`, `fractal_form`) assemble multi-voice textures. A constraint-aware voice-leading engine enforces counterpoint rules, and a four-level evaluation framework scores output on rule compliance, statistical quality, structural coherence, and perceptual characteristics. The system is entirely deterministic and GPU-free: every note in the output is traceable to its generating pattern and parameter mapping.

Sacred Composer currently achieves 86.5/100 on its evaluation framework, passes 241 automated tests, and renders to six output formats (MIDI, LilyPond, WAV, orchestral WAV, MusicXML, and performance IR). Beyond Western classical idioms, the system includes seven world-music subsystems spanning Indian raga, Arabic maqam, gamelan (slendro/pelog), Japanese scales, West African polyrhythm, and Balinese kotekan, demonstrating that mathematical pattern-to-music mapping generalizes across tonal traditions.

We argue that this architecture makes Sacred Composer a *mathematical microscope for music*: students can hear Fibonacci as melody, watch a Lorenz attractor become a contour, and feel how 1/f noise produces natural rubato. Every parameter mapping is transparent and adjustable, making the system a powerful tool for teaching the mathematics of music at the intersection where BRIDGES has long operated.

**(397 words)**

---

## Keywords

Algorithmic composition, mathematical patterns, music education, deterministic generative systems, pattern-to-music mapping

---

## Paper Outline (6--8 pages)

### 1. Introduction (1 page)

- The 2,500-year lineage of mathematics in music: Pythagoras, Guido d'Arezzo, Kircher, Mozart (Musikalisches Wurfelspiel), Hiller (Illiac Suite), Xenakis (stochastic music), Norgard (infinity series)
- The gap between mathematical beauty and musical beauty in current systems
- Thesis: a transparent, pattern-first architecture can bridge this gap while serving both compositional and educational goals

### 2. Related Work (1 page)

- **Neural/ML approaches:** Google Magenta, Meta MusicGen, AIVA -- strengths (quality, flexibility) and weaknesses (opacity, GPU dependence, non-traceability)
- **Rule-based/live-coding:** Cope EMI, TidalCycles, Sonic Pi, SuperCollider -- strengths (transparency, real-time) and weaknesses (idiom-bound, limited mathematical vocabulary)
- **Historical algorithmic composition:** Xenakis (UPIC, stochastic), Cage (I Ching operations), Tom Johnson (self-similar melodies)
- **Positioning:** Sacred Composer as the intersection of determinism, traceability, music-theory awareness, built-in evaluation, and multi-format output

### 3. Architecture: The Pattern-Map-Combine-Render Pipeline (1.5 pages)

- **Pattern generators** (23 total): mathematical (Fibonacci, golden spiral, Stern-Brocot tree, digits of pi/e), dynamical systems (Lorenz, logistic map), natural processes (1/f noise, phyllotaxis, flocking), algorithmic (cellular automata, L-systems, Euclidean rhythms)
- **Mappers:** `to_pitch()`, `to_rhythm()`, `to_dynamics()`, `to_form()` -- how raw values become musical parameters; normalization and quantization strategies
- **Combiners:** `layer`, `canon`, `phase`, `fractal_form` -- temporal assembly of multi-voice textures
- **Constraint engine:** parallel fifth/octave avoidance, voice crossing prevention, leap recovery, range enforcement
- Diagram: full data-flow from pattern to rendered output
- Code example: a complete 4-voice composition in 8 lines of Python

### 4. Implementation Details (1 page)

- Pure Python + NumPy/SciPy; no neural networks, no training data, no GPU
- Constraint-aware voice leading: how musical rules interact with mathematical patterns without destroying their character
- Four-level evaluation framework: rule compliance (gate), statistical quality, structural coherence, perceptual characteristics
- World music systems: raga grammar (arohana/avarohana, gamakas), maqam (24-TET via pitch bend), gamelan colotomic structure, kotekan interlocking, polyrhythm timelines

### 5. Results and Composition Examples (1.5 pages)

- Evaluation scores: 86.5/100 overall; breakdown by category
- 241 automated tests covering generators, mappers, constraints, rendering, and world music
- Composition examples with annotated score excerpts (LilyPond output):
  - Fibonacci canon in C minor (Western classical)
  - Lorenz attractor melody over golden-spiral harmonic rhythm
  - Raga Bhairav with gamaka ornaments
  - Data sonification: climate temperature series as melody
- Perceptual analysis: tension curves, dynamic range, textural variety
- Brief listener feedback (informal evaluation)

### 6. Educational Applications (0.5--1 page)

- "Mathematical microscope for music": making abstract patterns audible and tangible
- Interactive Streamlit playground: select a pattern, adjust parameters, hear the result instantly
- Classroom use cases: teaching Fibonacci, chaos theory, fractal geometry, and acoustics through music
- Alignment with BRIDGES mission: connecting mathematical understanding to artistic experience

### 7. Conclusion and Future Work (0.5 page)

- Summary of contributions: transparent pattern-to-music architecture, evaluation framework, cross-cultural applicability, educational utility
- Future directions: Bayesian parameter optimization (Optuna), Neo-Riemannian harmonic transitions, spectral interpolation, real-time web interface, multi-sensory installation with visualization
- Invitation to the BRIDGES community: the system is open-source and designed for extension

### References (0.5 page)

- Xenakis, *Formalized Music* (1992)
- Norgard, "Infinity Series" (1959--)
- Sethares, *Tuning, Timbre, Spectrum, Scale* (2005)
- Cope, *Experiments in Musical Intelligence* (1996)
- Lerdahl & Jackendoff, *A Generative Theory of Tonal Music* (1983)
- McLean & Dean, *Oxford Handbook of Algorithmic Music* (2018)
- Toussaint, *The Geometry of Musical Rhythm* (2013)

---

## Submission Notes

- **Category:** Regular Paper (6--8 pages) -- the system's breadth and educational angle warrant a full paper rather than a short paper or workshop proposal
- **BRIDGES fit:** Sacred Composer sits exactly at the mathematics-music-education intersection that defines BRIDGES; the pattern-traceability angle is novel in this community
- **Supplementary material:** Consider submitting audio examples and a link to the open-source repository as supplementary material; BRIDGES encourages multimedia
- **Deadline:** February 1, 2026 (paper), camera-ready after acceptance notification
