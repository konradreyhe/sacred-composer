// Sacred Composer — Canvas Visualization
// Golden spiral + note constellation + active note pulses

const PHI = (1 + Math.sqrt(5)) / 2;
const GOLDEN_ANGLE = Math.PI * 2 / (PHI * PHI); // ~137.5 degrees

function drawVisualization(comp, progress, activeNotes) {
    const canvas = document.getElementById('vizCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    // High-DPI support
    const rect = canvas.parentElement.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = rect.width;
    const h = rect.height;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.scale(dpr, dpr);

    const cx = w / 2;
    const cy = h / 2;
    const maxR = Math.min(w, h) * 0.42;

    // Background
    ctx.fillStyle = '#08080d';
    ctx.fillRect(0, 0, w, h);

    // Subtle radial gradient
    const bgGrad = ctx.createRadialGradient(cx, cy, 0, cx, cy, maxR * 1.3);
    bgGrad.addColorStop(0, 'rgba(212, 170, 48, 0.06)');
    bgGrad.addColorStop(1, 'rgba(8, 8, 13, 0)');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, w, h);

    const notes = comp.notes.filter(n => !n.rest);
    const total = notes.length;
    if (total === 0) return;

    // Time for ambient animations
    const t = Date.now() / 1000;

    // Pre-compute note positions on golden spiral
    const positions = [];
    for (let i = 0; i < total; i++) {
        const frac = i / total;
        const angle = i * GOLDEN_ANGLE;
        const r = maxR * Math.sqrt(frac);
        // Subtle ambient drift when idle (not playing)
        const drift = progress === 0 ? Math.sin(t * 0.5 + i * 1.2) * 1.5 : 0;
        const x = cx + r * Math.cos(angle) + drift;
        const y = cy + r * Math.sin(angle) + drift * 0.7;
        positions.push({ x, y, note: notes[i], index: i, frac });
    }

    // Draw spiral path
    ctx.beginPath();
    ctx.strokeStyle = 'rgba(212, 170, 48, 0.15)';
    ctx.lineWidth = 1;
    for (let i = 0; i < positions.length; i++) {
        if (i === 0) ctx.moveTo(positions[i].x, positions[i].y);
        else ctx.lineTo(positions[i].x, positions[i].y);
    }
    ctx.stroke();

    // Draw connections between sequential notes
    ctx.strokeStyle = 'rgba(212, 170, 48, 0.10)';
    ctx.lineWidth = 0.6;
    for (let i = 1; i < positions.length; i++) {
        ctx.beginPath();
        ctx.moveTo(positions[i - 1].x, positions[i - 1].y);
        ctx.lineTo(positions[i].x, positions[i].y);
        ctx.stroke();
    }

    // Active note set for quick lookup
    const activeSet = new Set((activeNotes || []).map(n => n.note));

    // Progress line (which notes have played)
    const playedCount = Math.floor(progress * total);

    // Draw each note dot
    for (let i = 0; i < positions.length; i++) {
        const p = positions[i];
        const n = p.note;
        const played = i < playedCount;
        const active = activeSet.has(n.note);

        // Color based on pitch (hue mapped to MIDI)
        const hue = ((n.midi - 48) / 36) * 280 + 30; // gold → blue range
        const sat = active ? 90 : (played ? 65 : 35);
        const light = active ? 70 : (played ? 50 : 28);
        const alpha = active ? 1.0 : (played ? 0.8 : 0.5);

        // Pulse effect for active notes
        if (active) {
            const pulseR = 12 + Math.sin(Date.now() / 150) * 4;
            ctx.beginPath();
            ctx.arc(p.x, p.y, pulseR, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${hue}, 80%, 55%, 0.20)`;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(p.x, p.y, pulseR * 0.6, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${hue}, 90%, 65%, 0.35)`;
            ctx.fill();
        }

        // Note dot
        const baseSize = 3 + n.velocity * 4;
        const size = active ? baseSize * 1.8 : baseSize;

        // Subtle glow ring around all notes
        if (!active) {
            ctx.beginPath();
            ctx.arc(p.x, p.y, size + 3, 0, Math.PI * 2);
            ctx.fillStyle = `hsla(${hue}, ${sat}%, ${light}%, ${alpha * 0.15})`;
            ctx.fill();
        }

        ctx.beginPath();
        ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hue}, ${sat}%, ${light}%, ${alpha})`;
        ctx.fill();
    }

    // Center decoration: rotating golden ratio symbol
    const idleBreath = 0.5 + 0.5 * Math.sin(t * 0.8); // slow breathing
    const rotAngle = progress > 0 ? progress * Math.PI * 4 : t * 0.15;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate(rotAngle);

    // Phi symbol outline
    const phiAlpha = progress > 0 ? 0.15 + progress * 0.20 : 0.12 + idleBreath * 0.10;
    ctx.strokeStyle = `rgba(212, 170, 48, ${phiAlpha})`;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(0, 0, 18, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(0, -24);
    ctx.lineTo(0, 24);
    ctx.stroke();

    ctx.restore();

    // Playback progress ring
    if (progress > 0) {
        ctx.beginPath();
        ctx.arc(cx, cy, maxR + 8, -Math.PI / 2, -Math.PI / 2 + progress * Math.PI * 2);
        ctx.strokeStyle = `rgba(212, 170, 48, 0.40)`;
        ctx.lineWidth = 2;
        ctx.stroke();
    }
}
