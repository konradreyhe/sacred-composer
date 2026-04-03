// Sacred Composer — Client-side Generative Composition Engine

// --- Seed & Hashing ---

function hashString(str) {
    let hash = 0;
    for (const c of str) {
        hash = ((hash << 5) - hash) + c.charCodeAt(0);
        hash |= 0; // Convert to 32-bit integer
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

// C minor pentatonic across several octaves
const SCALE_DEGREES = [0, 3, 5, 7, 10]; // semitone offsets
const BASE_OCTAVE = 3;

function midiToNote(midi) {
    const names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const octave = Math.floor(midi / 12) - 1;
    return names[midi % 12] + octave;
}

function scaleNote(index) {
    const degree = SCALE_DEGREES[((index % SCALE_DEGREES.length) + SCALE_DEGREES.length) % SCALE_DEGREES.length];
    const octaveShift = Math.floor(index / SCALE_DEGREES.length);
    return 12 * (BASE_OCTAVE + 1) + degree + octaveShift * 12; // MIDI number
}

// --- Fibonacci Sequence ---

function fibonacci(n) {
    const seq = [0, 1];
    for (let i = 2; i < n; i++) seq.push(seq[i - 1] + seq[i - 2]);
    return seq;
}

// --- Euclidean Rhythm ---

function euclidean(k, n) {
    // Bjorklund's algorithm: distribute k hits across n steps
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

    // Derive musical parameters from seed
    const fibCount = 13 + Math.floor(rng() * 8); // 13-20 Fibonacci terms
    const fib = fibonacci(fibCount);
    const eucHits = 3 + Math.floor(rng() * 6);   // 3-8 hits
    const eucSteps = 8 + Math.floor(rng() * 9);   // 8-16 steps
    const rhythm = euclidean(eucHits, eucSteps);

    const tempoBase = [72, 80, 88, 96, 108, 120];
    const tempo = tempoBase[Math.floor(rng() * tempoBase.length)];

    const keys = ['C', 'D', 'E', 'F', 'G', 'A', 'B'];
    const keyName = keys[seed % keys.length] + ' minor pentatonic';

    // Build note sequence from Fibonacci mapped to scale
    const noteIndices = fib.slice(2).map(f => f % (SCALE_DEGREES.length * 3));
    const durations = ['8n', '4n', '4n', '4n.', '2n'];
    const velocities = [0.4, 0.55, 0.65, 0.75, 0.6];

    const notes = [];
    let rhythmIdx = 0;
    for (let i = 0; i < noteIndices.length; i++) {
        const rStep = rhythm[rhythmIdx % rhythm.length];
        rhythmIdx++;

        if (rStep === 0) {
            // Rest
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
        pattern: `Fibonacci(${fibCount}) + Euclidean(${eucHits},${eucSteps})`,
        noteCount: notes.filter(n => !n.rest).length,
        durationSec,
        notes
    };
}

// --- Tone.js Playback ---

let currentPart = null;
let isPlaying = false;

async function playComposition(comp, onProgress, onDone) {
    await Tone.start();
    stopPlayback();

    Tone.Transport.bpm.value = comp.tempo;
    Tone.Transport.position = 0;

    const synth = new Tone.PolySynth(Tone.Synth, {
        oscillator: { type: 'triangle8' },
        envelope: { attack: 0.05, decay: 0.3, sustain: 0.4, release: 1.2 },
        volume: -8
    }).toDestination();

    const reverb = new Tone.Reverb({ decay: 3, wet: 0.3 }).toDestination();
    synth.connect(reverb);

    // Schedule notes
    let time = 0;
    const events = [];
    for (const n of comp.notes) {
        if (!n.rest) {
            events.push({ time: `0:0:${time}`, note: n.note, dur: n.duration, vel: n.velocity });
        }
        const d = n.duration.replace('.', '');
        const base = parseInt(d.replace('n', ''));
        const beats = 4 / base;
        time += (n.duration.includes('.') ? beats * 1.5 : beats) * 2; // in sixteenths
    }

    const totalSixteenths = time;
    const totalSeconds = (totalSixteenths / 4) * (60 / comp.tempo);

    const part = new Tone.Part((time, value) => {
        synth.triggerAttackRelease(value.note, value.dur, time, value.vel);
    }, events.map(e => [e.time, { note: e.note, dur: e.dur, vel: e.vel }]));

    part.start(0);
    currentPart = part;
    isPlaying = true;

    // Progress tracking
    const startTime = Date.now();
    const progressInterval = setInterval(() => {
        if (!isPlaying) {
            clearInterval(progressInterval);
            return;
        }
        const elapsed = (Date.now() - startTime) / 1000;
        const pct = Math.min(elapsed / totalSeconds, 1);
        if (onProgress) onProgress(pct);
        if (pct >= 1) {
            clearInterval(progressInterval);
            setTimeout(() => {
                stopPlayback();
                if (onDone) onDone();
            }, 500);
        }
    }, 100);

    Tone.Transport.start();
}

function stopPlayback() {
    if (currentPart) {
        currentPart.stop();
        currentPart.dispose();
        currentPart = null;
    }
    Tone.Transport.stop();
    Tone.Transport.cancel();
    isPlaying = false;
}
