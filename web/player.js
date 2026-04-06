// Sacred Composer — Client-side Generative Composition Engine

// --- Seed & Hashing ---

function hashString(str) {
    let hash = 0;
    for (const c of str.toUpperCase()) {
        hash = ((hash << 5) - hash) + c.charCodeAt(0);
        hash |= 0;
    }
    return Math.abs(hash);
}

// Seeded PRNG (mulberry32)
function makeRng(seed) {
    let s = seed | 0;
    return function () {
        s = (s + 0x6D2B79F5) | 0;
        let t = Math.imul(s ^ (s >>> 15), 1 | s);
        t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
        return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
}

// --- Musical Building Blocks ---

const SCALE_DEGREES = [0, 3, 5, 7, 10]; // C minor pentatonic
const BASE_OCTAVE = 3;

function midiToNote(midi) {
    const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const octave = Math.floor(midi / 12) - 1;
    return names[midi % 12] + octave;
}

function scaleNote(index) {
    const degree = SCALE_DEGREES[((index % SCALE_DEGREES.length) + SCALE_DEGREES.length) % SCALE_DEGREES.length];
    const octaveShift = Math.floor(index / SCALE_DEGREES.length);
    return 12 * (BASE_OCTAVE + 1) + degree + octaveShift * 12;
}

// --- Fibonacci Sequence ---

function fibonacci(n) {
    const seq = [0, 1];
    for (let i = 2; i < n; i++) seq.push(seq[i - 1] + seq[i - 2]);
    return seq;
}

// --- Euclidean Rhythm ---

function euclidean(k, n) {
    if (k >= n) return new Array(n).fill(1);
    if (k === 0) return new Array(n).fill(0);

    let pattern = [];
    for (let i = 0; i < n; i++) pattern.push(i < k ? [1] : [0]);

    let level = 0;
    while (true) {
        const counts = {};
        for (const p of pattern) {
            const key = p.join(',');
            counts[key] = (counts[key] || 0) + 1;
        }
        if (Object.keys(counts).length <= 1) break;

        const groups = {};
        for (const p of pattern) {
            const key = p.join(',');
            if (!groups[key]) groups[key] = [];
            groups[key].push(p);
        }

        const sorted = Object.values(groups).sort((a, b) => b.length - a.length);
        if (sorted.length < 2) break;

        const longer = sorted[0];
        const shorter = sorted[1];
        const merged = [];
        const minLen = Math.min(longer.length, shorter.length);

        for (let i = 0; i < minLen; i++) {
            merged.push([...longer[i], ...shorter[i]]);
        }
        for (let i = minLen; i < longer.length; i++) merged.push(longer[i]);
        for (let i = minLen; i < shorter.length; i++) merged.push(shorter[i]);

        pattern = merged;
        level++;
        if (level > 32) break;
    }

    return pattern.flat();
}

// --- Composition Generator ---

function generateComposition(seed) {
    const rng = makeRng(seed);

    const fibCount = 28 + Math.floor(rng() * 12); // 28-39 terms
    const fib = fibonacci(fibCount);
    const eucHits = 5 + Math.floor(rng() * 5);  // 5-9 hits (denser)
    const eucSteps = 8 + Math.floor(rng() * 6);  // 8-13 steps
    const rhythm = euclidean(eucHits, eucSteps);

    const tempoBase = [66, 72, 80, 88, 96, 108];
    const tempo = tempoBase[Math.floor(rng() * tempoBase.length)];

    const keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
    const keyName = keys[seed % keys.length] + ' minor pentatonic';

    const noteIndices = fib.slice(2).map(f => f % (SCALE_DEGREES.length * 3));
    const durations = ['8n', '8n', '4n', '4n', '4n.', '2n'];
    const velocities = [0.35, 0.45, 0.55, 0.60, 0.65, 0.70];

    const notes = [];
    let rhythmIdx = 0;
    for (let i = 0; i < noteIndices.length; i++) {
        const rStep = rhythm[rhythmIdx % rhythm.length];
        rhythmIdx++;

        if (rStep === 0) {
            notes.push({ rest: true, duration: '4n' });
        } else {
            const midi = scaleNote(noteIndices[i]);
            const dur = durations[Math.floor(rng() * durations.length)];
            const vel = velocities[Math.floor(rng() * velocities.length)];
            notes.push({
                rest: false,
                note: midiToNote(midi),
                midi: midi,
                duration: dur,
                velocity: vel
            });
        }
    }

    const totalBeats = notes.reduce((sum, n) => {
        const d = n.duration.replace('.', '');
        const base = parseInt(d.replace('n', ''));
        const beats = 4 / base;
        return sum + (n.duration.includes('.') ? beats * 1.5 : beats);
    }, 0);
    const durationSec = Math.round((totalBeats / tempo) * 60);

    return {
        seed,
        tempo,
        key: keyName,
        pattern: 'Fibonacci(' + fibCount + ') + Euclidean(' + eucHits + ',' + eucSteps + ')',
        noteCount: notes.filter(n => !n.rest).length,
        durationSec,
        notes
    };
}

// --- Tone.js Playback ---

let currentPart = null;
let padSynth = null;
let isPlaying = false;

async function playComposition(comp, onProgress, onDone) {
    await Tone.start();
    stopPlayback();

    Tone.Transport.bpm.value = comp.tempo;
    Tone.Transport.position = 0;

    // Main melodic synth — warm triangle with filter
    const synth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'triangle8' },
        envelope: { attack: 0.04, decay: 0.25, sustain: 0.5, release: 1.5 },
        volume: -10
    });

    // Pad layer — slow attack, wide, adds depth
    padSynth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'sine' },
        envelope: { attack: 0.3, decay: 0.5, sustain: 0.6, release: 2.0 },
        volume: -22
    });

    // Effects chain
    const reverb = new Tone.Reverb({ decay: 4, wet: 0.35 }).toDestination();
    const delay = new Tone.FeedbackDelay({ delayTime: '8n', feedback: 0.15, wet: 0.12 }).connect(reverb);
    const filter = new Tone.Filter({ frequency: 3000, type: 'lowpass' }).connect(delay);

    synth.connect(filter);
    padSynth.connect(reverb);

    // Schedule notes
    let time = 0;
    const events = [];
    const noteTimings = []; // For tracking active notes

    for (const n of comp.notes) {
        const d = n.duration.replace('.', '');
        const base = parseInt(d.replace('n', ''));
        const beats = 4 / base;
        const durBeats = n.duration.includes('.') ? beats * 1.5 : beats;

        if (!n.rest) {
            events.push({
                time: '0:0:' + time,
                note: n.note,
                midi: n.midi,
                dur: n.duration,
                vel: n.velocity,
                sixteenths: time,
                durSixteenths: durBeats * 2
            });
        }
        time += durBeats * 2;
    }

    const totalSixteenths = time;
    const totalSeconds = (totalSixteenths / 4) * (60 / comp.tempo);

    const activeNotes = [];

    const part = new Tone.Part((time, value) => {
        synth.triggerAttackRelease(value.note, value.dur, time, value.vel);
        // Pad plays every other note, one octave down
        if (value.midi > 48) {
            const padNote = midiToNote(value.midi - 12);
            padSynth.triggerAttackRelease(padNote, '2n', time, value.vel * 0.4);
        }
    }, events.map(e => [e.time, e]));

    part.start(0);
    currentPart = part;
    isPlaying = true;

    const startTime = Date.now();
    const progressInterval = setInterval(() => {
        if (!isPlaying) { clearInterval(progressInterval); return; }

        const elapsed = (Date.now() - startTime) / 1000;
        const pct = Math.min(elapsed / totalSeconds, 1);
        const currentSixteenth = pct * totalSixteenths;

        // Find active notes
        const active = events.filter(e =>
            currentSixteenth >= e.sixteenths &&
            currentSixteenth < e.sixteenths + e.durSixteenths
        );

        if (onProgress) onProgress(pct, active);

        if (pct >= 1) {
            clearInterval(progressInterval);
            setTimeout(() => {
                stopPlayback();
                if (onDone) onDone();
            }, 800);
        }
    }, 50); // 20fps for smooth visualization

    Tone.Transport.start();
}

function stopPlayback() {
    if (currentPart) {
        currentPart.stop();
        currentPart.dispose();
        currentPart = null;
    }
    if (padSynth) {
        padSynth.releaseAll();
        padSynth = null;
    }
    Tone.Transport.stop();
    Tone.Transport.cancel();
    isPlaying = false;
}
