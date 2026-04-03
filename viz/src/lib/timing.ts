export interface NoteData {
  pitch: number;
  velocity: number;
  startBeat: number;
  durationBeat: number;
  startSec: number;
  durationSec: number;
  pitchBend: number | null;
  voiceIndex?: number;
}

export interface VoiceData {
  name: string;
  instrument: string;
  channel: number;
  notes: NoteData[];
}

export interface FormSection {
  label: string;
  startBar: number;
  endBar: number;
  bars: number;
}

export interface CompositionData {
  meta: {
    title: string;
    tempo: number;
    durationBeats: number;
    durationSec: number;
    fps: number;
  };
  voices: VoiceData[];
  formSections: FormSection[];
}

const VOICE_COLORS = [
  "#E8A838", // gold
  "#4FC3F7", // sky blue
  "#EF5350", // coral red
  "#66BB6A", // green
  "#AB47BC", // purple
  "#FF7043", // deep orange
  "#26C6DA", // cyan
  "#EC407A", // pink
];

/** Return all notes sounding at the given time in seconds. */
export function getActiveNotes(
  voices: VoiceData[],
  currentTimeSec: number
): NoteData[] {
  const active: NoteData[] = [];
  voices.forEach((voice, vi) => {
    for (const n of voice.notes) {
      if (
        currentTimeSec >= n.startSec &&
        currentTimeSec < n.startSec + n.durationSec
      ) {
        active.push({ ...n, voiceIndex: vi });
      }
    }
  });
  return active;
}

/** Convert a beat position to a frame number. */
export function beatsToFrame(
  beats: number,
  tempo: number,
  fps: number
): number {
  const seconds = beats / (tempo / 60);
  return Math.round(seconds * fps);
}

/** Get a consistent colour for a voice index. */
export function getNoteColor(voiceIndex: number): string {
  return VOICE_COLORS[voiceIndex % VOICE_COLORS.length];
}

/** Current playback time in seconds for a given frame. */
export function frameToSec(frame: number, fps: number): number {
  return frame / fps;
}
