"""
Sacred Geometry Vol. 1 — Album Cover Art Generator

Renders a 3000x3000 Mandelbrot set visualization zoomed into the
seahorse valley, using a black/gold/deep-red color scheme.
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# === Parameters ===
SIZE = 3000
MAX_ITER = 512

# Seahorse valley — a visually striking region of the Mandelbrot boundary
CENTER_RE = -0.7463
CENTER_IM = 0.1102
ZOOM = 0.005  # half-width in complex plane

# Color palette
BLACK = np.array([10, 8, 12], dtype=np.float64)       # near-black with slight warmth
GOLD = np.array([201, 168, 76], dtype=np.float64)      # #C9A84C
DEEP_RED = np.array([139, 0, 0], dtype=np.float64)     # #8B0000
DARK_RED = np.array([60, 0, 0], dtype=np.float64)      # transition color


def mandelbrot_smooth(c: np.ndarray, max_iter: int) -> np.ndarray:
    """Compute smooth iteration counts for the Mandelbrot set."""
    z = np.zeros_like(c)
    counts = np.zeros(c.shape, dtype=np.float64)
    mask = np.ones(c.shape, dtype=bool)

    for i in range(max_iter):
        z[mask] = z[mask] * z[mask] + c[mask]
        escaped = mask & (np.abs(z) > 256)
        # Smooth coloring: fractional escape count
        counts[escaped] = i + 1 - np.log2(np.log2(np.abs(z[escaped])))
        mask[escaped] = False

    # Points inside the set get -1
    counts[mask] = -1
    return counts


def colorize(counts: np.ndarray, max_iter: int) -> np.ndarray:
    """Map smooth iteration counts to RGB using black/gold/deep-red palette."""
    h, w = counts.shape
    img = np.zeros((h, w, 3), dtype=np.uint8)

    # Interior of the set: pure black
    interior = counts < 0
    img[interior] = BLACK.astype(np.uint8)

    # Exterior: smooth gradient
    exterior = ~interior
    # Normalize to [0, 1]
    t = counts[exterior] / max_iter

    # Multi-stop gradient for visual richness:
    #   0.0       -> black (far from boundary)
    #   0.02      -> dark red
    #   0.06      -> deep red (near boundary glow)
    #   0.12      -> gold (boundary highlight)
    #   0.25      -> deep red (secondary band)
    #   0.5+      -> fades to black

    r = np.zeros(t.shape, dtype=np.float64)
    g = np.zeros_like(r)
    b = np.zeros_like(r)

    # Use a cyclic-ish scheme based on a sine wave modulated by t
    # This gives natural banding with smooth transitions
    phase = np.log1p(t * 80) * 3.0  # log scaling compresses far-field

    # Gold channel (peaks periodically)
    gold_weight = np.exp(-((np.sin(phase) - 1.0) ** 2) * 4.0)
    # Red channel (broader peaks, offset)
    red_weight = np.exp(-((np.sin(phase * 0.7 + 1.0) - 1.0) ** 2) * 2.0)
    # Brightness envelope: bright near boundary, fades far away
    envelope = np.clip(1.0 - t * 2.5, 0, 1) ** 0.6

    r = (GOLD[0] * gold_weight + DEEP_RED[0] * red_weight) * envelope
    g = (GOLD[1] * gold_weight + DEEP_RED[1] * red_weight) * envelope
    b = (GOLD[2] * gold_weight + DEEP_RED[2] * red_weight) * envelope

    # Add a subtle dark-red base glow near boundary
    base_glow = np.clip(1.0 - t * 8, 0, 1) ** 2
    r += DARK_RED[0] * base_glow * 0.5
    g += DARK_RED[1] * base_glow * 0.5
    b += DARK_RED[2] * base_glow * 0.5

    img[exterior, 0] = np.clip(r, 0, 255).astype(np.uint8)
    img[exterior, 1] = np.clip(g, 0, 255).astype(np.uint8)
    img[exterior, 2] = np.clip(b, 0, 255).astype(np.uint8)

    return img


def add_title(img: Image.Image) -> Image.Image:
    """Add album title at the bottom of the image."""
    draw = ImageDraw.Draw(img)
    w, h = img.size

    # Title text
    title = "SACRED GEOMETRY"
    subtitle = "VOL. 1"

    # Load fonts — use arial, scale to image size
    try:
        font_title = ImageFont.truetype("arial.ttf", size=120)
        font_sub = ImageFont.truetype("arial.ttf", size=72)
    except OSError:
        font_title = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Gold color for text
    text_color = (201, 168, 76)  # #C9A84C
    shadow_color = (30, 24, 10)

    # Position: centered, bottom area
    y_title = h - 340
    y_sub = h - 200

    # Draw shadow for readability (offset by 3px)
    for dx, dy in [(3, 3), (-1, -1), (2, 0), (0, 2)]:
        draw.text((w // 2 + dx, y_title + dy), title, font=font_title,
                  fill=shadow_color, anchor="mm")
        draw.text((w // 2 + dx, y_sub + dy), subtitle, font=font_sub,
                  fill=shadow_color, anchor="mm")

    # Draw text
    draw.text((w // 2, y_title), title, font=font_title,
              fill=text_color, anchor="mm")
    draw.text((w // 2, y_sub), subtitle, font=font_sub,
              fill=text_color, anchor="mm")

    # Thin gold line separator
    line_y = y_title + 70
    line_half = 300
    draw.line([(w // 2 - line_half, line_y), (w // 2 + line_half, line_y)],
              fill=text_color, width=2)

    return img


def main():
    print(f"Generating {SIZE}x{SIZE} Mandelbrot set...")
    print(f"  Region: seahorse valley ({CENTER_RE}, {CENTER_IM}i), zoom={ZOOM}")

    # Build complex plane grid
    re = np.linspace(CENTER_RE - ZOOM, CENTER_RE + ZOOM, SIZE)
    im = np.linspace(CENTER_IM - ZOOM, CENTER_IM + ZOOM, SIZE)
    re_grid, im_grid = np.meshgrid(re, im)
    c = re_grid + 1j * im_grid

    print(f"  Computing {MAX_ITER} iterations...")
    counts = mandelbrot_smooth(c, MAX_ITER)

    print("  Colorizing...")
    rgb = colorize(counts, MAX_ITER)

    # Convert to PIL
    img = Image.fromarray(rgb, mode="RGB")

    print("  Adding title...")
    img = add_title(img)

    # Save
    out_path = "examples/album/cover_art.jpg"
    img.save(out_path, "JPEG", quality=95)
    print(f"  Saved: {out_path}")
    print(f"  Size: {img.size[0]}x{img.size[1]}")


if __name__ == "__main__":
    main()
