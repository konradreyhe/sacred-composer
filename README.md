# MUSIK! -- AI Classical Music Composition System

A compiler-architecture system that generates classical music as MIDI from natural-language text prompts. No neural networks, no training data -- just music theory encoded as algorithms: counterpoint rules, galant schemata, voice leading, form templates, and orchestration heuristics.

## Quick Start

```bash
pip install music21 midiutil numpy scipy
python composer.py
python composer.py "A piano sonata exposition in C minor, heroic character, 40 bars"
```

## Architecture: The 9-Pass Compiler Pipeline

A text prompt flows through nine sequential compiler passes, each refining an intermediate representation (IR):

| Pass | Name | What It Does |
|------|------|-------------|
| 1 | **Plan** | Parses prompt into a `FormIR` (form type, key, sections, bar counts) |
| 2 | **Schema** | Fills sections with galant schemata (Do-Re-Mi, Prinner, Romanesca, etc.) |
| 3 | **Harmony** | Realizes schemata into concrete chord progressions via context-free grammar |
| 4 | **Melody** | Generates melodic lines over the harmony using motif-based development |
| 5 | **Counterpoint** | Adds inner voices with voice-leading rules (parallel fifths, resolution, etc.) |
| 6 | **Orchestration** | Assigns voices to instrument tracks based on ensemble and register |
| 7 | **Expression** | Adds dynamics, articulations, phrasing arcs |
| 8 | **Humanization** | Applies timing jitter, velocity curves, rubato to avoid mechanical playback |
| 9 | **Validation** | Checks rule compliance and produces a quality report |

## Files

| File | Description |
|------|-------------|
| `composer.py` | Main pipeline -- the `compose()` function that runs all 9 passes end-to-end |
| `classical_music_gen.py` | Core music theory toolkit: ChordGrammar, VoiceLeader, MelodyGenerator, CounterpointSolver, AlbertiBass, OrchestrationMapper, FormEngine |
| `SYSTEM_ARCHITECTURE.py` | IR data structures, token enums (FormType, SectionType, CadenceType, etc.), and schema realizations |
| `prompt_template_library.py` | Prompt templates for using Claude as a composition planner (two-pass: Claude generates JSON plan, Python realizes it as MIDI) |
| `evaluation_framework.py` | Multi-level scoring system (rule compliance, statistical quality, structural quality, perceptual quality) producing a 0-100 score |
| `test_compositions.py` | Stress tests: D minor string quartet sonata, F major piano variations, Bb minor orchestral ternary form |
| `KNOWLEDGE_BASE.md` | 36-part reference covering music theory, neuroscience, orchestration, history, and AI composition techniques |
| `LISTENING_GUIDE.md` | What to listen for in the stress-test compositions |
| `PRINCIPLES.md` | Engineering principles governing the codebase |

## The Knowledge Base

`KNOWLEDGE_BASE.md` is a 36-part reference document (~325 KB) that serves as the theoretical foundation. Topics include:

- Why classical music is code (Part 1), mathematical foundations including golden ratio and fractal self-similarity (Part 2)
- Counterpoint and harmony rules engine (Part 3), melody/rhythm/form (Part 4), orchestration (Part 5)
- The emotion engine (Part 6), toolchain (Part 7), neuroscience of musical perception (Parts 10, 16)
- Composer technique reverse-engineering (Part 13), galant schemata (Part 24), masterwork analysis (Part 33)
- AI music generation state of the art (Part 15), end-to-end composition systems (Part 26)
- The 50 essential rules (Part 34), the philosophy of taste (Part 35), timbral composition (Part 36)

## Usage

```python
from composer import compose

# Sonata exposition
perf, form, report = compose(
    "A dramatic sonata exposition in C minor, heroic, 40 bars, for piano",
    "output.mid"
)

# Theme and variations
perf, form, report = compose(
    "A lyrical theme and 3 variations in G major, 32 bars, for string quartet",
    "output.mid"
)
```

Supported forms: sonata, ternary (ABA), binary (AB), theme and variations, rondo, minuet and trio, fugue.

Supported ensembles: piano, string quartet, orchestra.

## Evaluation

Score any generated MIDI file on a 0-100 scale:

```python
from evaluation_framework import evaluate_midi

report = evaluate_midi("output.mid")
```

The evaluation has four levels:

1. **Rule Compliance** (gate) -- parallel fifths/octaves, voice crossing, range violations. If this fails, score is capped at 40.
2. **Statistical Quality** (0-100) -- pitch/rhythm distributions, interval patterns compared to corpus norms.
3. **Structural Quality** (0-100) -- harmonic rhythm, phrase structure, cadence placement, motivic coherence.
4. **Perceptual Quality** (0-100) -- tension curve shape, dynamic range, textural variety.

Additional dependency for evaluation: `pip install scipy`

## Current Status

**What works:**
- Full 9-pass pipeline from text prompt to MIDI file
- Sonata exposition, ternary form, theme and variations
- Piano, string quartet, and orchestral ensembles
- Galant schemata realization, motivic development, SATB voice leading
- Automated evaluation framework with detailed scoring breakdown

**Known limitations:**
- No real-time Claude API integration yet (prompt templates are defined but the pipeline uses deterministic algorithms)
- Fugue generation is rudimentary
- Development sections (sonata form) lack true motivic fragmentation
- No audio rendering -- output is MIDI only

## The 12 Principles

From `PRINCIPLES.md`, the engineering principles guiding this codebase:

1. **KISS** -- The simplest solution that works is the best solution
2. **DRY** -- Every piece of knowledge should have a single, unambiguous representation
3. **YAGNI** -- Only implement features you actually need right now
4. **SRP** -- Each function/class should have one, and only one, reason to change
5. **High Cohesion / Low Coupling** -- Related functionality grouped together; modules minimize dependencies
6. **Composition over Inheritance** -- Favor composition for code reuse; no deep inheritance hierarchies
7. **Law of Demeter** -- Objects should only talk to their direct friends
8. **Clean/Hexagonal Architecture** -- Business logic independent of frameworks and infrastructure
9. **Explicit over Implicit** -- No magic behavior; clear function signatures with types
10. **Fail Fast** -- Detect errors early and explicitly; no swallowed exceptions
11. **Documentation as Code** -- Documentation lives next to the code it describes
12. **Consistency over Preference** -- Follow established patterns even when you prefer something different

## License

Not yet specified.
