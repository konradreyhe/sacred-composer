// Sacred Composer — Enhanced Three.js Sacred Pattern Visualizations
// Fibonacci → Phyllotaxis Sphere | Golden → Flower of Life | Harmonic → Cymatics
// Logistic → Lorenz Attractor | Thue-Morse → Fractal Tree | Mandelbrot → Terrain
//
// Enhanced: starfield, camera breathing, progress ring, glow auras,
//           sacred connections, vertex-colored cymatics, ambient particles

(() => {
'use strict';

var GOLDEN_ANGLE = 2.39996323;
var GOLD_HEX = 0xd4aa30;
var GOLD_DIM_HEX = 0x8a7025;
var BG_HEX = 0x08080d;
var TWO_PI = Math.PI * 2;

var renderer, scene, camera, clock;
var currentViz = null;
var vizReady = false;

// Persistent scene elements (survive pattern switches)
var starfield = null;
var progressRing = null;
var connectionLines = null;
var glowSprites = []; // reusable glow meshes for active notes

// ------------------------------------------------------------------ Init
function initRenderer() {
    var canvas = document.getElementById('vizCanvas');
    if (!canvas) return;
    renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(BG_HEX);
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
    camera.position.set(0, 0, 6);
    camera.lookAt(0, 0, 0);
    clock = new THREE.Clock();

    // --- Starfield (persistent) ---
    var starCount = 300;
    var starPositions = new Float32Array(starCount * 3);
    var starColors = new Float32Array(starCount * 3);
    var goldC = new THREE.Color(GOLD_HEX);
    for (var i = 0; i < starCount; i++) {
        // Distribute on a sphere shell
        var phi = Math.acos(1 - 2 * (i + 0.5) / starCount);
        var theta = GOLDEN_ANGLE * i;
        var rad = 12 + Math.sin(i * 7.13) * 4;
        starPositions[i * 3]     = rad * Math.sin(phi) * Math.cos(theta);
        starPositions[i * 3 + 1] = rad * Math.sin(phi) * Math.sin(theta);
        starPositions[i * 3 + 2] = rad * Math.cos(phi);
        var brightness = 0.15 + Math.sin(i * 3.7) * 0.1;
        starColors[i * 3]     = goldC.r * brightness;
        starColors[i * 3 + 1] = goldC.g * brightness;
        starColors[i * 3 + 2] = goldC.b * brightness;
    }
    var starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPositions, 3));
    starGeo.setAttribute('color', new THREE.BufferAttribute(starColors, 3));
    var starMat = new THREE.PointsMaterial({
        size: 0.06, vertexColors: true, transparent: true, opacity: 0.7, sizeAttenuation: true
    });
    starfield = new THREE.Points(starGeo, starMat);
    scene.add(starfield);

    // --- Progress Ring (persistent) ---
    var ringSegments = 128;
    var ringPts = [];
    for (i = 0; i <= ringSegments; i++) {
        var a = (i / ringSegments) * TWO_PI - Math.PI / 2;
        ringPts.push(new THREE.Vector3(Math.cos(a) * 3.2, Math.sin(a) * 3.2, 0));
    }
    var ringGeo = new THREE.BufferGeometry().setFromPoints(ringPts);
    var ringMat = new THREE.LineBasicMaterial({ color: GOLD_HEX, transparent: true, opacity: 0.5 });
    progressRing = new THREE.Line(ringGeo, ringMat);
    progressRing.renderOrder = 999;
    scene.add(progressRing);

    // --- Connection Lines (persistent, reusable) ---
    var connGeo = new THREE.BufferGeometry();
    var connPositions = new Float32Array(30 * 6); // max 30 segments
    connGeo.setAttribute('position', new THREE.BufferAttribute(connPositions, 3));
    connGeo.setDrawRange(0, 0);
    var connMat = new THREE.LineBasicMaterial({ color: GOLD_HEX, transparent: true, opacity: 0.2 });
    connectionLines = new THREE.LineSegments(connGeo, connMat);
    connectionLines.renderOrder = 998;
    scene.add(connectionLines);

    // --- Glow Sprites (reusable pool of 8) ---
    for (i = 0; i < 8; i++) {
        var gGeo = new THREE.SphereGeometry(0.25, 12, 12);
        var gMat = new THREE.MeshBasicMaterial({
            color: GOLD_HEX, transparent: true, opacity: 0,
            blending: THREE.AdditiveBlending, depthWrite: false
        });
        var gMesh = new THREE.Mesh(gGeo, gMat);
        gMesh.renderOrder = 997;
        scene.add(gMesh);
        glowSprites.push(gMesh);
    }

    vizReady = true;
}

function resizeRenderer() {
    var el = renderer.domElement.parentElement;
    var w = el.clientWidth;
    var h = el.clientHeight;
    var pr = renderer.getPixelRatio();
    if (renderer.domElement.width !== Math.floor(w * pr) ||
        renderer.domElement.height !== Math.floor(h * pr)) {
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
}

// ------------------------------------------------------------------ Cleanup
function disposeViz() {
    if (!currentViz) return;
    scene.remove(currentViz.group);
    currentViz.group.traverse(function (obj) {
        if (obj.geometry) obj.geometry.dispose();
        if (obj.material) {
            if (Array.isArray(obj.material)) obj.material.forEach(function (m) { m.dispose(); });
            else obj.material.dispose();
        }
    });
    currentViz = null;
}

// ------------------------------------------------------------------ Helpers
function hueFromMidi(midi) { return ((midi - 48) / 36) * 280 + 30; }

function noteColor(midi, bright) {
    var c = new THREE.Color();
    c.setHSL(hueFromMidi(midi) / 360, bright ? 0.9 : 0.45, bright ? 0.68 : 0.32);
    return c;
}

function noteColorVibrant(midi) {
    var c = new THREE.Color();
    c.setHSL(hueFromMidi(midi) / 360, 0.95, 0.75);
    return c;
}

function getActiveSet(activeNotes) {
    return new Set((activeNotes || []).map(function (a) { return a.note; }));
}

// Enhanced note mesh updater with glow tracking
function updateNoteMeshes(meshes, notes, progress, activeNotes, t, group) {
    var aSet = getActiveSet(activeNotes);
    var played = Math.floor(progress * notes.length);
    var glowIdx = 0;

    for (var i = 0; i < meshes.length; i++) {
        var m = meshes[i];
        var n = notes[i];
        var active = aSet.has(n.note);
        if (active) {
            m.material.color.copy(noteColorVibrant(n.midi));
            m.material.opacity = 1;
            m.scale.setScalar(2.5 + Math.sin(t * 10) * 0.5);
            // Position a glow sprite here
            if (glowIdx < glowSprites.length) {
                var gs = glowSprites[glowIdx];
                var wp = new THREE.Vector3();
                m.getWorldPosition(wp);
                gs.position.copy(wp);
                gs.material.color.copy(noteColorVibrant(n.midi));
                gs.material.opacity = 0.25 + Math.sin(t * 8) * 0.1;
                gs.scale.setScalar(1.5 + Math.sin(t * 6) * 0.4);
                glowIdx++;
            }
        } else if (i < played) {
            m.material.color.copy(noteColor(n.midi, true));
            m.material.opacity = 0.8;
            m.scale.setScalar(1.3);
        } else {
            m.material.color.copy(noteColor(n.midi, false));
            m.material.opacity = 0.45;
            m.scale.setScalar(1 + Math.sin(t * 0.4 + i * 0.7) * 0.08);
        }
    }
    return glowIdx;
}

// Update sacred connection lines between active notes
function updateConnections(meshes, notes, activeNotes) {
    var aSet = getActiveSet(activeNotes);
    var activePositions = [];
    for (var i = 0; i < meshes.length; i++) {
        if (aSet.has(notes[i].note)) {
            var wp = new THREE.Vector3();
            meshes[i].getWorldPosition(wp);
            activePositions.push(wp);
        }
    }
    var posArr = connectionLines.geometry.attributes.position.array;
    var segCount = 0;
    // Draw lines between all pairs (sacred geometry connections)
    for (var a = 0; a < activePositions.length && segCount < 30; a++) {
        for (var b = a + 1; b < activePositions.length && segCount < 30; b++) {
            var off = segCount * 6;
            posArr[off]     = activePositions[a].x;
            posArr[off + 1] = activePositions[a].y;
            posArr[off + 2] = activePositions[a].z;
            posArr[off + 3] = activePositions[b].x;
            posArr[off + 4] = activePositions[b].y;
            posArr[off + 5] = activePositions[b].z;
            segCount++;
        }
    }
    connectionLines.geometry.attributes.position.needsUpdate = true;
    connectionLines.geometry.setDrawRange(0, segCount * 2);
}

// Create ambient dust particles for a pattern group
function addDust(group, count, radius, seed) {
    var positions = new Float32Array(count * 3);
    var sizes = new Float32Array(count);
    for (var i = 0; i < count; i++) {
        var a1 = Math.sin(i * 127.1 + seed * 311.7) * 0.5 + 0.5;
        var a2 = Math.sin(i * 269.5 + seed * 183.3) * 0.5 + 0.5;
        var a3 = Math.sin(i * 419.2 + seed * 97.1) * 0.5 + 0.5;
        positions[i * 3]     = (a1 - 0.5) * radius * 2;
        positions[i * 3 + 1] = (a2 - 0.5) * radius * 2;
        positions[i * 3 + 2] = (a3 - 0.5) * radius * 2;
        sizes[i] = 0.015 + a1 * 0.02;
    }
    var dustGeo = new THREE.BufferGeometry();
    dustGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    var dustMat = new THREE.PointsMaterial({
        color: GOLD_HEX, size: 0.02, transparent: true, opacity: 0.2,
        sizeAttenuation: true, blending: THREE.AdditiveBlending, depthWrite: false
    });
    var dust = new THREE.Points(dustGeo, dustMat);
    dust.userData.isDust = true;
    group.add(dust);
    return dust;
}

// ==================================================================
// 1. PHYLLOTAXIS SPHERE (Fibonacci)
//    Enhanced: golden logarithmic spiral, dual icosahedra, dust
// ==================================================================
function buildPhyllotaxis(comp) {
    var group = new THREE.Group();
    var notes = comp.notes.filter(function (n) { return !n.rest; });
    var N = notes.length;
    var meshes = [];

    for (var i = 0; i < N; i++) {
        var y = 1 - (2 * i + 1) / N;
        var r = Math.sqrt(1 - y * y);
        var theta = GOLDEN_ANGLE * i;
        var x = r * Math.cos(theta);
        var z = r * Math.sin(theta);
        var size = 0.05 + notes[i].velocity * 0.07;
        var geo = new THREE.SphereGeometry(size, 8, 8);
        var mat = new THREE.MeshBasicMaterial({
            color: noteColor(notes[i].midi, false), transparent: true, opacity: 0.5
        });
        var mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(x * 2.2, y * 2.2, z * 2.2);
        group.add(mesh);
        meshes.push(mesh);
    }

    // Golden spiral line
    var pts = meshes.map(function (m) { return m.position.clone(); });
    var lineGeo = new THREE.BufferGeometry().setFromPoints(pts);
    var lineMat = new THREE.LineBasicMaterial({ color: GOLD_HEX, transparent: true, opacity: 0.12 });
    group.add(new THREE.Line(lineGeo, lineMat));

    // Dual nested icosahedra
    var c1Geo = new THREE.IcosahedronGeometry(0.25, 1);
    var c1Mat = new THREE.MeshBasicMaterial({ color: GOLD_HEX, wireframe: true, transparent: true, opacity: 0.3 });
    var center1 = new THREE.Mesh(c1Geo, c1Mat);
    group.add(center1);

    var c2Geo = new THREE.IcosahedronGeometry(0.45, 0);
    var c2Mat = new THREE.MeshBasicMaterial({ color: GOLD_DIM_HEX, wireframe: true, transparent: true, opacity: 0.12 });
    var center2 = new THREE.Mesh(c2Geo, c2Mat);
    group.add(center2);

    // Equatorial ring
    var eqPts = [];
    for (i = 0; i <= 64; i++) {
        var ea = (i / 64) * TWO_PI;
        eqPts.push(new THREE.Vector3(Math.cos(ea) * 2.3, 0, Math.sin(ea) * 2.3));
    }
    var eqGeo = new THREE.BufferGeometry().setFromPoints(eqPts);
    var eqMat = new THREE.LineBasicMaterial({ color: GOLD_HEX, transparent: true, opacity: 0.08 });
    group.add(new THREE.Line(eqGeo, eqMat));

    addDust(group, 60, 3, comp.seed);

    return {
        pattern: 'fibonacci', seed: comp.seed, group: group, meshes: meshes, notes: notes,
        update: function (progress, activeNotes, t) {
            group.rotation.y = t * 0.12;
            group.rotation.x = Math.sin(t * 0.07) * 0.15;
            center1.rotation.x = t * 0.35;
            center1.rotation.z = t * 0.25;
            center2.rotation.y = -t * 0.15;
            center2.rotation.x = t * 0.1;
            var usedGlows = updateNoteMeshes(meshes, notes, progress, activeNotes, t, group);
            updateConnections(meshes, notes, activeNotes);
            return usedGlows;
        }
    };
}

// ==================================================================
// 2. FLOWER OF LIFE (Golden Spiral)
//    Enhanced: 3 ring layers, vesica piscis highlights, dust
// ==================================================================
function buildFlowerOfLife(comp) {
    var group = new THREE.Group();
    var notes = comp.notes.filter(function (n) { return !n.rest; });
    var N = notes.length;
    var R = 0.72;

    // 3 layers: center + inner 6 + outer 6
    var centers = [[0, 0]];
    var i, a;
    for (i = 0; i < 6; i++) {
        a = i * Math.PI / 3;
        centers.push([R * Math.cos(a), R * Math.sin(a)]);
    }
    for (i = 0; i < 6; i++) {
        a = i * Math.PI / 3 + Math.PI / 6;
        centers.push([R * Math.sqrt(3) * Math.cos(a), R * Math.sqrt(3) * Math.sin(a)]);
    }
    // Third ring
    for (i = 0; i < 6; i++) {
        a = i * Math.PI / 3;
        centers.push([2 * R * Math.cos(a), 2 * R * Math.sin(a)]);
    }

    var rings = [];
    centers.forEach(function (c, idx) {
        var geo = new THREE.TorusGeometry(R, 0.03, 12, 64);
        var ringLayer = idx === 0 ? 0 : (idx <= 6 ? 1 : (idx <= 12 ? 2 : 3));
        var baseOpacity = [0.4, 0.35, 0.2, 0.12][ringLayer];
        var mat = new THREE.MeshBasicMaterial({
            color: GOLD_DIM_HEX, transparent: true, opacity: baseOpacity
        });
        var mesh = new THREE.Mesh(geo, mat);
        mesh.position.set(c[0], c[1], 0);
        group.add(mesh);
        rings.push({ mesh: mesh, layer: ringLayer, baseOpacity: baseOpacity });
    });

    // Outer boundary (double ring)
    var outerGeo1 = new THREE.TorusGeometry(R * 3.2, 0.035, 12, 96);
    var outerMat1 = new THREE.MeshBasicMaterial({ color: GOLD_HEX, transparent: true, opacity: 0.18 });
    group.add(new THREE.Mesh(outerGeo1, outerMat1));
    var outerGeo2 = new THREE.TorusGeometry(R * 3.35, 0.015, 8, 96);
    var outerMat2 = new THREE.MeshBasicMaterial({ color: GOLD_DIM_HEX, transparent: true, opacity: 0.08 });
    group.add(new THREE.Mesh(outerGeo2, outerMat2));

    // Vesica piscis highlights — 6 almond shapes at intersections
    for (i = 0; i < 6; i++) {
        a = i * Math.PI / 3;
        var vx = R * 0.5 * Math.cos(a);
        var vy = R * 0.5 * Math.sin(a);
        var vGeo = new THREE.SphereGeometry(0.06, 8, 8);
        var vMat = new THREE.MeshBasicMaterial({
            color: GOLD_HEX, transparent: true, opacity: 0.15,
            blending: THREE.AdditiveBlending, depthWrite: false
        });
        var vm = new THREE.Mesh(vGeo, vMat);
        vm.position.set(vx, vy, 0.02);
        group.add(vm);
    }

    // Note dots on golden-angle spiral
    var noteMeshes = [];
    for (i = 0; i < N; i++) {
        var angle = GOLDEN_ANGLE * i;
        var r = 0.2 + (i / N) * 2.1;
        var nGeo = new THREE.SphereGeometry(0.035 + notes[i].velocity * 0.045, 8, 8);
        var nMat = new THREE.MeshBasicMaterial({
            color: noteColor(notes[i].midi, false), transparent: true, opacity: 0.5
        });
        var nm = new THREE.Mesh(nGeo, nMat);
        nm.position.set(r * Math.cos(angle), r * Math.sin(angle), 0.06);
        group.add(nm);
        noteMeshes.push(nm);
    }

    group.scale.setScalar(1.05);
    addDust(group, 50, 3, comp.seed);

    return {
        pattern: 'golden', seed: comp.seed, group: group, meshes: noteMeshes, notes: notes,
        update: function (progress, activeNotes, t) {
            group.rotation.x = Math.sin(t * 0.1) * 0.15;
            group.rotation.y = t * 0.06;

            rings.forEach(function (r, idx) {
                var phase = idx / rings.length;
                var near = Math.abs(progress - phase) < 0.1;
                if (near && progress > 0) {
                    r.mesh.material.opacity = 0.75;
                    r.mesh.material.color.setHex(GOLD_HEX);
                } else {
                    r.mesh.material.opacity = r.baseOpacity + Math.sin(t * 0.3 + idx * 0.8) * 0.05;
                    r.mesh.material.color.setHex(GOLD_DIM_HEX);
                }
            });

            var usedGlows = updateNoteMeshes(noteMeshes, notes, progress, activeNotes, t, group);
            updateConnections(noteMeshes, notes, activeNotes);
            return usedGlows;
        }
    };
}

// ==================================================================
// 3. CYMATICS (Harmonic Series) — ENHANCED
//    Vertex-colored Chladni plate, dual wave modes, particle sand,
//    solid + wireframe layers, more detailed mesh
// ==================================================================
function buildCymatics(comp) {
    var group = new THREE.Group();
    var notes = comp.notes.filter(function (n) { return !n.rest; });
    var N = notes.length;

    // Higher-res mesh for more detailed patterns
    var segments = 96;
    var geo = new THREE.PlaneGeometry(5, 5, segments, segments);
    var posAttr = geo.attributes.position;
    var basePos = new Float32Array(posAttr.array.length);
    basePos.set(posAttr.array);

    // Vertex colors (will be updated per frame)
    var vColors = new Float32Array(posAttr.count * 3);
    geo.setAttribute('color', new THREE.BufferAttribute(vColors, 3));

    // Solid surface with vertex colors
    var solidMat = new THREE.MeshBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.55, side: THREE.DoubleSide
    });
    var solidPlane = new THREE.Mesh(geo, solidMat);
    solidPlane.rotation.x = -Math.PI * 0.38;
    group.add(solidPlane);

    // Wireframe overlay
    var wireGeo = geo.clone();
    var wireMat = new THREE.MeshBasicMaterial({
        color: GOLD_HEX, wireframe: true, transparent: true, opacity: 0.12
    });
    var wirePlane = new THREE.Mesh(wireGeo, wireMat);
    wirePlane.rotation.x = -Math.PI * 0.38;
    group.add(wirePlane);

    // Particle sand — settles on wave nodes
    var sandCount = 200;
    var sandPositions = new Float32Array(sandCount * 3);
    var sandGeo = new THREE.BufferGeometry();
    sandGeo.setAttribute('position', new THREE.BufferAttribute(sandPositions, 3));
    var sandMat = new THREE.PointsMaterial({
        color: 0xffe0a0, size: 0.03, transparent: true, opacity: 0.5,
        sizeAttenuation: true, blending: THREE.AdditiveBlending, depthWrite: false
    });
    var sand = new THREE.Points(sandGeo, sandMat);
    sand.rotation.x = -Math.PI * 0.38;
    group.add(sand);

    // Note particles floating above
    var noteMeshes = [];
    for (var i = 0; i < N; i++) {
        var angle = GOLDEN_ANGLE * i;
        var r = (i / N) * 2.0;
        var nGeo = new THREE.SphereGeometry(0.04 + notes[i].velocity * 0.05, 8, 8);
        var nMat = new THREE.MeshBasicMaterial({
            color: noteColor(notes[i].midi, false), transparent: true, opacity: 0.5
        });
        var nm = new THREE.Mesh(nGeo, nMat);
        nm.position.set(r * Math.cos(angle), 0.5, r * Math.sin(angle));
        group.add(nm);
        noteMeshes.push(nm);
    }

    // Color helpers
    var peakCol = new THREE.Color(0xffd866); // warm gold peaks
    var nodeCol = new THREE.Color(0x1a2040); // dark blue nodes
    var midCol = new THREE.Color(GOLD_DIM_HEX);

    return {
        pattern: 'harmonic', seed: comp.seed, group: group, meshes: noteMeshes, notes: notes,
        update: function (progress, activeNotes, t) {
            group.rotation.y = t * 0.05;

            // Dual Chladni mode: primary + secondary harmonic
            var n1 = 2 + Math.floor(progress * 6);
            var m1 = 3 + Math.floor(progress * 5);
            var n2 = n1 + 1;
            var m2 = m1 + 2;
            var activeCount = (activeNotes && activeNotes.length) || 0;
            var amp = 0.15 + activeCount * 0.06;
            var breathe = Math.sin(t * 0.5) * 0.03;
            var secondaryMix = 0.3 + activeCount * 0.05;
            var L = 2.5;

            for (var i = 0; i < posAttr.count; i++) {
                var bx = basePos[i * 3];
                var by = basePos[i * 3 + 1];
                // Primary Chladni pattern
                var c1 = Math.cos(n1 * Math.PI * bx / L) * Math.cos(m1 * Math.PI * by / L) -
                         Math.cos(m1 * Math.PI * bx / L) * Math.cos(n1 * Math.PI * by / L);
                // Secondary harmonic
                var c2 = Math.cos(n2 * Math.PI * bx / L) * Math.cos(m2 * Math.PI * by / L) -
                         Math.cos(m2 * Math.PI * bx / L) * Math.cos(n2 * Math.PI * by / L);
                var combined = c1 * (1 - secondaryMix) + c2 * secondaryMix;
                var displacement = combined * (amp + breathe);
                posAttr.array[i * 3 + 2] = displacement;

                // Color by displacement: peaks = warm gold, nodes = dark blue
                var normDisp = (displacement / (amp + 0.1) + 1) * 0.5; // 0..1
                var col;
                if (normDisp > 0.5) {
                    col = midCol.clone().lerp(peakCol, (normDisp - 0.5) * 2);
                } else {
                    col = nodeCol.clone().lerp(midCol, normDisp * 2);
                }
                vColors[i * 3]     = col.r;
                vColors[i * 3 + 1] = col.g;
                vColors[i * 3 + 2] = col.b;
            }
            posAttr.needsUpdate = true;
            geo.attributes.color.needsUpdate = true;

            // Update wireframe too
            var wirePos = wireGeo.attributes.position;
            wirePos.array.set(posAttr.array);
            wirePos.needsUpdate = true;

            // Sand particles settle on nodal lines (where displacement ≈ 0)
            var sandIdx = 0;
            var step = Math.max(1, Math.floor(posAttr.count / sandCount));
            for (i = 0; i < posAttr.count && sandIdx < sandCount; i += step) {
                var dz = Math.abs(posAttr.array[i * 3 + 2]);
                if (dz < amp * 0.15) { // near nodal line
                    sandPositions[sandIdx * 3]     = posAttr.array[i * 3] + Math.sin(t + i) * 0.02;
                    sandPositions[sandIdx * 3 + 1] = posAttr.array[i * 3 + 1] + Math.cos(t * 0.7 + i) * 0.02;
                    sandPositions[sandIdx * 3 + 2] = posAttr.array[i * 3 + 2] + 0.01;
                    sandIdx++;
                }
            }
            // Fill remaining with offscreen
            for (; sandIdx < sandCount; sandIdx++) {
                sandPositions[sandIdx * 3] = 0;
                sandPositions[sandIdx * 3 + 1] = 0;
                sandPositions[sandIdx * 3 + 2] = -10;
            }
            sandGeo.attributes.position.needsUpdate = true;

            // Notes
            var aSet = getActiveSet(activeNotes);
            var played = Math.floor(progress * N);
            for (var j = 0; j < noteMeshes.length; j++) {
                var m = noteMeshes[j];
                var note = notes[j];
                var active = aSet.has(note.note);
                m.position.y = 0.35 + Math.sin(t * 0.3 + j) * 0.08 + (active ? 0.5 : 0);
                if (active) {
                    m.material.color.copy(noteColorVibrant(note.midi));
                    m.material.opacity = 1;
                    m.scale.setScalar(2.8);
                } else if (j < played) {
                    m.material.color.copy(noteColor(note.midi, true));
                    m.material.opacity = 0.7;
                    m.scale.setScalar(1.2);
                } else {
                    m.material.color.copy(noteColor(note.midi, false));
                    m.material.opacity = 0.4;
                    m.scale.setScalar(1 + Math.sin(t * 0.4 + j * 0.5) * 0.06);
                }
            }
            updateConnections(noteMeshes, notes, activeNotes);
        }
    };
}

// ==================================================================
// 4. LORENZ ATTRACTOR (Logistic Map)
//    Enhanced: glowing trail, larger head with aura, dust
// ==================================================================
function buildAttractor(comp) {
    var group = new THREE.Group();
    var notes = comp.notes.filter(function (n) { return !n.rest; });
    var N = notes.length;

    var STEPS = 5000;
    var dt = 0.004;
    var sigma = 10, rho = 28, beta = 8 / 3;
    var lx = 0.1, ly = 0, lz = 0;
    var points = [];

    for (var i = 0; i < STEPS; i++) {
        var dx = sigma * (ly - lx);
        var dy = lx * (rho - lz) - ly;
        var dz = lx * ly - beta * lz;
        lx += dx * dt;
        ly += dy * dt;
        lz += dz * dt;
        points.push(new THREE.Vector3(lx * 0.07, (lz - 25) * 0.07, ly * 0.07));
    }

    // Attractor with gradient colors (hue shifts along path)
    var ptsGeo = new THREE.BufferGeometry().setFromPoints(points);
    var colors = new Float32Array(STEPS * 3);
    var goldC = new THREE.Color(GOLD_HEX);
    for (i = 0; i < STEPS; i++) {
        var hue = (30 + (i / STEPS) * 40) / 360; // gold → warm orange
        var c = new THREE.Color();
        c.setHSL(hue, 0.6, 0.2);
        colors[i * 3]     = c.r;
        colors[i * 3 + 1] = c.g;
        colors[i * 3 + 2] = c.b;
    }
    ptsGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    var ptsMat = new THREE.PointsMaterial({
        size: 0.025, vertexColors: true, transparent: true, opacity: 0.7, sizeAttenuation: true
    });
    group.add(new THREE.Points(ptsGeo, ptsMat));

    // Playback head
    var headGeo = new THREE.SphereGeometry(0.1, 12, 12);
    var headMat = new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0 });
    var head = new THREE.Mesh(headGeo, headMat);
    group.add(head);

    // Head aura (additive glow)
    var auraGeo = new THREE.SphereGeometry(0.3, 12, 12);
    var auraMat = new THREE.MeshBasicMaterial({
        color: GOLD_HEX, transparent: true, opacity: 0,
        blending: THREE.AdditiveBlending, depthWrite: false
    });
    var aura = new THREE.Mesh(auraGeo, auraMat);
    group.add(aura);

    // Note spheres
    var noteMeshes = [];
    for (i = 0; i < N; i++) {
        var ptIdx = Math.floor((i / N) * STEPS);
        var nGeo = new THREE.SphereGeometry(0.045 + notes[i].velocity * 0.055, 8, 8);
        var nMat = new THREE.MeshBasicMaterial({
            color: noteColor(notes[i].midi, false), transparent: true, opacity: 0.45
        });
        var nm = new THREE.Mesh(nGeo, nMat);
        nm.position.copy(points[ptIdx]);
        group.add(nm);
        noteMeshes.push(nm);
    }

    addDust(group, 40, 3.5, comp.seed);

    return {
        pattern: 'logistic', seed: comp.seed, group: group, meshes: noteMeshes, notes: notes,
        update: function (progress, activeNotes, t) {
            group.rotation.y = t * 0.1;
            group.rotation.x = Math.sin(t * 0.05) * 0.2;

            if (progress > 0) {
                var idx = Math.floor(progress * (STEPS - 1));
                head.position.copy(points[idx]);
                headMat.opacity = 0.95;
                head.scale.setScalar(1 + Math.sin(t * 6) * 0.3);
                aura.position.copy(points[idx]);
                auraMat.opacity = 0.2 + Math.sin(t * 4) * 0.08;
                aura.scale.setScalar(1.5 + Math.sin(t * 3) * 0.3);
            } else {
                headMat.opacity = 0;
                auraMat.opacity = 0;
            }

            // Gradient brighten along path
            var colorAttr = ptsGeo.getAttribute('color');
            var bright = Math.floor(progress * STEPS);
            for (var i = 0; i < STEPS; i++) {
                var hue = (30 + (i / STEPS) * 40) / 360;
                var lit = i < bright ? 0.55 : 0.2;
                var sat = i < bright ? 0.85 : 0.6;
                var cc = new THREE.Color();
                cc.setHSL(hue, sat, lit);
                colorAttr.array[i * 3]     = cc.r;
                colorAttr.array[i * 3 + 1] = cc.g;
                colorAttr.array[i * 3 + 2] = cc.b;
            }
            colorAttr.needsUpdate = true;

            var usedGlows = updateNoteMeshes(noteMeshes, notes, progress, activeNotes, t, group);
            updateConnections(noteMeshes, notes, activeNotes);
            return usedGlows;
        }
    };
}

// ==================================================================
// 5. FRACTAL TREE (Thue-Morse)
//    Enhanced: pollen particles, wind sway, color-gradient branches
// ==================================================================
function buildFractalTree(comp) {
    var group = new THREE.Group();
    var notes = comp.notes.filter(function (n) { return !n.rest; });
    var N = notes.length;

    var tm = [0];
    while (tm.length < 512) {
        var inv = tm.map(function (b) { return 1 - b; });
        for (var k = 0; k < inv.length && tm.length < 512; k++) tm.push(inv[k]);
    }

    var branches = [];
    var leaves = [];

    function branch(bx, by, angle, length, depth, tmIdx) {
        if (depth > 8 || length < 0.04) return;
        var ex = bx + Math.cos(angle) * length;
        var ey = by + Math.sin(angle) * length;
        branches.push({ x1: bx, y1: by, x2: ex, y2: ey, depth: depth });
        if (depth >= 5) leaves.push({ x: ex, y: ey, depth: depth });
        var spread = 0.42 + tm[tmIdx % tm.length] * 0.28;
        var shrink = 0.67 + tm[(tmIdx + 1) % tm.length] * 0.08;
        branch(ex, ey, angle + spread, length * shrink, depth + 1, tmIdx * 2 + 1);
        branch(ex, ey, angle - spread, length * shrink, depth + 1, tmIdx * 2 + 2);
    }
    branch(0, -2.4, Math.PI / 2, 1.15, 0, 0);

    // Color-gradient branches (trunk=dark gold, tips=bright)
    var branchLines = [];
    branches.forEach(function (b) {
        var bGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(b.x1, b.y1, 0),
            new THREE.Vector3(b.x2, b.y2, 0)
        ]);
        var depthFrac = b.depth / 9;
        var bCol = new THREE.Color();
        bCol.setHSL(0.1 + depthFrac * 0.05, 0.5 + depthFrac * 0.3, 0.2 + depthFrac * 0.15);
        var opacity = 0.15 + (1 - depthFrac) * 0.3;
        var bMat = new THREE.LineBasicMaterial({
            color: bCol, transparent: true, opacity: opacity
        });
        var line = new THREE.Line(bGeo, bMat);
        group.add(line);
        branchLines.push({ line: line, depth: b.depth, baseColor: bCol.clone() });
    });

    // Leaf particles with color variety
    var leafMeshes = [];
    leaves.forEach(function (l, idx) {
        var lGeo = new THREE.SphereGeometry(0.025, 6, 6);
        var lCol = new THREE.Color();
        lCol.setHSL(0.08 + (idx * 0.01) % 0.15, 0.6, 0.4);
        var lMat = new THREE.MeshBasicMaterial({
            color: lCol, transparent: true, opacity: 0.4
        });
        var lm = new THREE.Mesh(lGeo, lMat);
        lm.position.set(l.x, l.y, 0);
        group.add(lm);
        leafMeshes.push(lm);
    });

    // Pollen/firefly particles floating up from canopy
    var pollenCount = 40;
    var pollenPositions = new Float32Array(pollenCount * 3);
    for (var p = 0; p < pollenCount; p++) {
        var pl = leaves[Math.floor(Math.sin(p * 47.3 + comp.seed) * 0.5 * leaves.length + leaves.length * 0.5) % leaves.length];
        pollenPositions[p * 3] = pl.x + Math.sin(p * 127.1) * 0.3;
        pollenPositions[p * 3 + 1] = pl.y + Math.sin(p * 269.5) * 0.3;
        pollenPositions[p * 3 + 2] = Math.sin(p * 419.2) * 0.2;
    }
    var pollenGeo = new THREE.BufferGeometry();
    pollenGeo.setAttribute('position', new THREE.BufferAttribute(pollenPositions, 3));
    var pollenMat = new THREE.PointsMaterial({
        color: 0xffe8a0, size: 0.035, transparent: true, opacity: 0.4,
        sizeAttenuation: true, blending: THREE.AdditiveBlending, depthWrite: false
    });
    var pollen = new THREE.Points(pollenGeo, pollenMat);
    group.add(pollen);

    // Note spheres
    var noteMeshes = [];
    for (var i = 0; i < N; i++) {
        var leafIdx = Math.min(Math.floor((i / N) * leaves.length), leaves.length - 1);
        var l = leaves[leafIdx];
        var jx = Math.sin(i * 127.1 + comp.seed * 311.7) * 0.12;
        var jy = Math.sin(i * 269.5 + comp.seed * 183.3) * 0.12;
        var nGeo = new THREE.SphereGeometry(0.045 + notes[i].velocity * 0.055, 8, 8);
        var nMat = new THREE.MeshBasicMaterial({
            color: noteColor(notes[i].midi, false), transparent: true, opacity: 0.5
        });
        var nm = new THREE.Mesh(nGeo, nMat);
        nm.position.set(l.x + jx, l.y + jy, 0.05);
        group.add(nm);
        noteMeshes.push(nm);
    }

    group.position.y = 0.5;

    return {
        pattern: 'thue_morse', seed: comp.seed, group: group, meshes: noteMeshes, notes: notes,
        update: function (progress, activeNotes, t) {
            // Wind sway
            group.rotation.z = Math.sin(t * 0.2) * 0.03 + Math.sin(t * 0.53) * 0.01;
            group.rotation.y = Math.sin(t * 0.08) * 0.3;

            var maxLitDepth = progress > 0 ? Math.floor(progress * 9) : -1;
            branchLines.forEach(function (bl) {
                if (bl.depth <= maxLitDepth) {
                    bl.line.material.color.setHex(GOLD_HEX);
                    bl.line.material.opacity = 0.5 + (1 - bl.depth / 9) * 0.45;
                } else {
                    bl.line.material.color.copy(bl.baseColor);
                    bl.line.material.opacity = 0.12 + Math.sin(t * 0.3 + bl.depth) * 0.03;
                }
            });

            // Leaves breathe + drift
            leafMeshes.forEach(function (lm, idx) {
                lm.scale.setScalar(1 + Math.sin(t * 0.5 + idx * 0.3) * 0.15);
                lm.position.x += Math.sin(t * 0.3 + idx * 1.7) * 0.0003;
            });

            // Pollen floats upward slowly
            var pArr = pollenGeo.attributes.position.array;
            for (var pi = 0; pi < pollenCount; pi++) {
                pArr[pi * 3 + 1] += 0.003; // drift up
                pArr[pi * 3] += Math.sin(t * 0.5 + pi * 2.7) * 0.002; // sway
                // Reset when too high
                if (pArr[pi * 3 + 1] > 2) {
                    var rl = leaves[pi % leaves.length];
                    pArr[pi * 3] = rl.x + Math.sin(t + pi * 127) * 0.2;
                    pArr[pi * 3 + 1] = rl.y;
                    pArr[pi * 3 + 2] = Math.sin(t + pi * 49) * 0.1;
                }
            }
            pollenGeo.attributes.position.needsUpdate = true;
            pollenMat.opacity = 0.3 + ((activeNotes && activeNotes.length) || 0) * 0.05;

            var usedGlows = updateNoteMeshes(noteMeshes, notes, progress, activeNotes, t, group);
            updateConnections(noteMeshes, notes, activeNotes);
            return usedGlows;
        }
    };
}

// ==================================================================
// 6. MANDELBROT TERRAIN (Mandelbrot)
//    Enhanced: banded coloring, edge glow, higher res, dust
// ==================================================================
function buildMandelbrot(comp) {
    var group = new THREE.Group();
    var notes = comp.notes.filter(function (n) { return !n.rest; });
    var N = notes.length;

    var size = 80;
    var geo = new THREE.PlaneGeometry(5, 5, size - 1, size - 1);
    var posAttr = geo.attributes.position;

    var maxIter = 64;
    var escapes = [];
    for (var j = 0; j < size; j++) {
        for (var i = 0; i < size; i++) {
            var cr = -2.0 + (i / (size - 1)) * 3.0;
            var ci = -1.2 + (j / (size - 1)) * 2.4;
            var zr = 0, zi = 0, iter = 0;
            while (zr * zr + zi * zi < 4 && iter < maxIter) {
                var tmp = zr * zr - zi * zi + cr;
                zi = 2 * zr * zi + ci;
                zr = tmp;
                iter++;
            }
            escapes.push(iter);
        }
    }

    for (i = 0; i < posAttr.count; i++) {
        posAttr.setZ(i, (escapes[i] / maxIter) * 1.3);
    }
    geo.computeVertexNormals();

    // Banded coloring (more vivid)
    var vColors = new Float32Array(posAttr.count * 3);
    for (i = 0; i < posAttr.count; i++) {
        var f = escapes[i] / maxIter;
        var c = new THREE.Color();
        if (f >= 0.99) {
            c.set(0x050510); // inside set = near black
        } else {
            // Banded gradient: dark purple → gold → white
            var band = (escapes[i] % 8) / 8;
            c.setHSL(0.08 + band * 0.06, 0.7 + f * 0.3, 0.15 + f * 0.5);
        }
        vColors[i * 3]     = c.r;
        vColors[i * 3 + 1] = c.g;
        vColors[i * 3 + 2] = c.b;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(vColors, 3));

    var terrainMat = new THREE.MeshBasicMaterial({
        vertexColors: true, transparent: true, opacity: 0.75, side: THREE.DoubleSide
    });
    var terrain = new THREE.Mesh(geo, terrainMat);
    terrain.rotation.x = -Math.PI * 0.45;
    group.add(terrain);

    // Wireframe
    var wireMat = new THREE.MeshBasicMaterial({
        color: GOLD_HEX, wireframe: true, transparent: true, opacity: 0.06
    });
    var wire = new THREE.Mesh(geo.clone(), wireMat);
    wire.rotation.x = -Math.PI * 0.45;
    group.add(wire);

    // Edge glow — particles along the boundary (where escape iterations transition)
    var edgePts = [];
    for (j = 1; j < size - 1; j++) {
        for (i = 1; i < size - 1; i++) {
            var idx = j * size + i;
            var esc = escapes[idx];
            var neighbors = [escapes[idx - 1], escapes[idx + 1], escapes[idx - size], escapes[idx + size]];
            var isEdge = neighbors.some(function (ne) { return Math.abs(ne - esc) > 5; });
            if (isEdge && edgePts.length < 150) {
                edgePts.push(new THREE.Vector3(
                    posAttr.getX(idx),
                    posAttr.getY(idx),
                    posAttr.getZ(idx) + 0.05
                ));
            }
        }
    }
    if (edgePts.length > 0) {
        var edgeGeo = new THREE.BufferGeometry().setFromPoints(edgePts);
        var edgeMat = new THREE.PointsMaterial({
            color: 0xffd866, size: 0.04, transparent: true, opacity: 0.5,
            sizeAttenuation: true, blending: THREE.AdditiveBlending, depthWrite: false
        });
        var edgeParticles = new THREE.Points(edgeGeo, edgeMat);
        edgeParticles.rotation.x = -Math.PI * 0.45;
        group.add(edgeParticles);
    }

    // Note spheres
    var noteMeshes = [];
    for (i = 0; i < N; i++) {
        var angle = GOLDEN_ANGLE * i;
        var r = (i / N) * 1.8;
        var nGeo = new THREE.SphereGeometry(0.045 + notes[i].velocity * 0.055, 8, 8);
        var nMat = new THREE.MeshBasicMaterial({
            color: noteColor(notes[i].midi, false), transparent: true, opacity: 0.5
        });
        var nm = new THREE.Mesh(nGeo, nMat);
        nm.position.set(r * Math.cos(angle), 0.9, r * Math.sin(angle));
        group.add(nm);
        noteMeshes.push(nm);
    }

    group.position.y = -0.3;
    addDust(group, 50, 3.5, comp.seed);

    return {
        pattern: 'mandelbrot', seed: comp.seed, group: group, meshes: noteMeshes, notes: notes,
        update: function (progress, activeNotes, t) {
            group.rotation.y = t * 0.07;

            var aSet = getActiveSet(activeNotes);
            var played = Math.floor(progress * N);
            for (var i = 0; i < noteMeshes.length; i++) {
                var m = noteMeshes[i];
                var n = notes[i];
                var active = aSet.has(n.note);
                m.position.y = 0.8 + Math.sin(t * 0.3 + i * 0.5) * 0.08 + (active ? 0.45 : 0);
                if (active) {
                    m.material.color.copy(noteColorVibrant(n.midi));
                    m.material.opacity = 1;
                    m.scale.setScalar(2.8);
                } else if (i < played) {
                    m.material.color.copy(noteColor(n.midi, true));
                    m.material.opacity = 0.7;
                    m.scale.setScalar(1.2);
                } else {
                    m.material.color.copy(noteColor(n.midi, false));
                    m.material.opacity = 0.4;
                    m.scale.setScalar(1 + Math.sin(t * 0.4 + i * 0.5) * 0.06);
                }
            }
            updateConnections(noteMeshes, notes, activeNotes);
            terrainMat.opacity = 0.65 + ((activeNotes && activeNotes.length) || 0) * 0.04;
        }
    };
}

// ==================================================================
// DISPATCHER & MAIN API
// ==================================================================
var builders = {
    fibonacci:  buildPhyllotaxis,
    golden:     buildFlowerOfLife,
    harmonic:   buildCymatics,
    logistic:   buildAttractor,
    thue_morse: buildFractalTree,
    mandelbrot: buildMandelbrot
};

window.drawVisualization = function (comp, progress, activeNotes) {
    if (!vizReady) {
        initRenderer();
        if (!vizReady) return;
    }
    resizeRenderer();

    var patternKey = comp.patternKey || selectedPattern || 'fibonacci';

    if (!currentViz || currentViz.pattern !== patternKey || currentViz.seed !== comp.seed) {
        disposeViz();
        var builder = builders[patternKey] || builders.fibonacci;
        currentViz = builder(comp);
        scene.add(currentViz.group);
    }

    var t = clock.getElapsedTime();

    // --- Camera breathing ---
    camera.position.z = 6 + Math.sin(t * 0.3) * 0.15;
    camera.position.x = Math.sin(t * 0.07) * 0.1;
    camera.position.y = Math.sin(t * 0.11) * 0.08;
    camera.lookAt(0, 0, 0);

    // --- Starfield rotation ---
    if (starfield) {
        starfield.rotation.y = t * 0.008;
        starfield.rotation.x = t * 0.003;
    }

    // --- Progress ring ---
    if (progressRing) {
        if (progress > 0) {
            progressRing.geometry.setDrawRange(0, Math.floor(progress * 129));
            progressRing.material.opacity = 0.45 + Math.sin(t * 2) * 0.1;
            progressRing.visible = true;
        } else {
            progressRing.visible = false;
        }
    }

    // --- Update pattern viz ---
    var usedGlows = currentViz.update(progress, activeNotes, t);

    // --- Hide unused glow sprites ---
    for (var g = usedGlows || 0; g < glowSprites.length; g++) {
        glowSprites[g].material.opacity = 0;
    }

    renderer.render(scene, camera);
};

})();
