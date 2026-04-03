"""
Sacred Composer — Fibonacci to Music Animation
Render: manim -pql manim_fibonacci.py FibonacciReveal
        manim -pql manim_fibonacci.py PatternToMusic
        manim -pql manim_fibonacci.py MultiplePatterns
"""
from manim import *
import numpy as np

DARK_BG = "#1a1a2e"
GOLD = "#FFD700"
WARM_GOLD = "#FFC125"
NOTE_BLUE = "#4FC3F7"
SOFT_WHITE = "#E0E0E0"


class FibonacciReveal(Scene):
    def construct(self):
        self.camera.background_color = DARK_BG
        fibs = [1, 1, 2, 3, 5, 8, 13, 21, 34]
        note_names = ["C4", "C4", "D4", "E4", "G4", "C5", "F5", "C6", "B6"]

        title = Text("Fibonacci → Music", font_size=48, color=GOLD)
        title.to_edge(UP, buff=0.4)
        self.play(Write(title), run_time=1)

        # Staff lines
        staff = VGroup()
        for i in range(5):
            line = Line(LEFT * 5, RIGHT * 5, stroke_width=1, color=SOFT_WHITE)
            line.shift(DOWN * 0.8 + UP * i * 0.25)
            staff.add(line)
        self.play(Create(staff), run_time=0.8)

        # Golden spiral (quarter arcs building up)
        spiral_group = VGroup()
        spiral_center = np.array([3.5, 1.5, 0])
        angle_offset = 0
        scale_factor = 0.04

        # Number display area
        num_row = VGroup()
        for idx, f in enumerate(fibs):
            num = Text(str(f), font_size=36, color=GOLD)
            num.move_to(LEFT * 4.5 + RIGHT * idx * 1.1 + UP * 2.2)
            note = Text(note_names[idx], font_size=24, color=NOTE_BLUE)
            note.next_to(num, DOWN, buff=0.15)

            # Spiral arc for this Fibonacci number
            arc_radius = f * scale_factor
            arc = Arc(
                radius=arc_radius,
                start_angle=angle_offset,
                angle=PI / 2,
                color=WARM_GOLD,
                stroke_width=2,
            ).move_arc_center_to(spiral_center)
            angle_offset += PI / 2

            # Note on staff — vertical position maps pitch
            note_y = -0.8 + (idx / len(fibs)) * 1.0
            note_dot = Dot(
                point=[LEFT * 4.5 + RIGHT * idx * 1.1][0][0] * RIGHT + note_y * UP,
                radius=0.1,
                color=NOTE_BLUE,
            )

            self.play(
                FadeIn(num, shift=UP * 0.3),
                FadeIn(note, shift=DOWN * 0.2),
                Create(arc),
                GrowFromCenter(note_dot),
                run_time=0.6,
            )
            num_row.add(num, note)
            spiral_group.add(arc)

        # Final flourish
        box = SurroundingRectangle(num_row, color=GOLD, buff=0.2, corner_radius=0.1)
        self.play(Create(box), run_time=0.8)
        self.wait(1.5)


class PatternToMusic(Scene):
    def construct(self):
        self.camera.background_color = DARK_BG
        fibs = [1, 1, 2, 3, 5, 8, 13, 21, 34]

        # Left side — math column
        left_title = Text("Fibonacci", font_size=36, color=GOLD).move_to(LEFT * 4 + UP * 3)
        divider = Line(UP * 3.5, DOWN * 3.5, color=SOFT_WHITE, stroke_width=1)
        right_title = Text("Piano Roll", font_size=36, color=NOTE_BLUE).move_to(RIGHT * 3 + UP * 3)

        self.play(Write(left_title), Write(right_title), Create(divider), run_time=1)

        # Piano roll grid
        grid = VGroup()
        for row in range(9):
            for col in range(9):
                cell = Rectangle(
                    width=0.55, height=0.3,
                    stroke_width=0.5, stroke_color=GRAY,
                ).move_to(RIGHT * (0.8 + col * 0.55) + UP * (2.2 - row * 0.55))
                grid.add(cell)
        self.play(FadeIn(grid), run_time=0.8)

        # Arrow label
        arrow_label = Text("to_pitch()", font_size=20, color=SOFT_WHITE)
        arrow = Arrow(LEFT * 1.8, RIGHT * 0.4, color=WARM_GOLD, stroke_width=2)
        arrow.shift(UP * 0.3)
        arrow_label.next_to(arrow, UP, buff=0.1)
        self.play(GrowArrow(arrow), FadeIn(arrow_label), run_time=0.7)

        # Animate each value
        fib_texts = VGroup()
        for idx, f in enumerate(fibs):
            ft = Text(str(f), font_size=28, color=GOLD)
            ft.move_to(LEFT * 4 + UP * (2.2 - idx * 0.55))
            fib_texts.add(ft)

        for idx, f in enumerate(fibs):
            # Highlight current fib value
            highlight = SurroundingRectangle(fib_texts[idx], color=GOLD, buff=0.08)

            # Piano roll note block — column = time step, row = pitch
            pitch_row = min(f - 1, 8)  # clamp to grid
            note_block = Rectangle(
                width=0.55, height=0.3, fill_color=NOTE_BLUE,
                fill_opacity=0.85, stroke_width=0,
            ).move_to(RIGHT * (0.8 + idx * 0.55) + UP * (2.2 - pitch_row * 0.55))

            self.play(
                FadeIn(fib_texts[idx]),
                Create(highlight),
                FadeIn(note_block),
                run_time=0.5,
            )
            if idx < len(fibs) - 1:
                self.play(FadeOut(highlight), run_time=0.15)

        self.wait(1.5)


class MultiplePatterns(Scene):
    def construct(self):
        self.camera.background_color = DARK_BG

        titles = ["Fibonacci\nSpiral", "Lorenz\nButterfly", "Cellular\nAutomata", "Golden Angle\nPhyllotaxis"]
        colors = [GOLD, "#FF6B6B", "#69F0AE", "#CE93D8"]
        positions = [LEFT * 4.8, LEFT * 1.6, RIGHT * 1.6, RIGHT * 4.8]

        pattern_groups = VGroup()
        for i, (t, c, p) in enumerate(zip(titles, colors, positions)):
            label = Text(t, font_size=18, color=c).move_to(p + UP * 2.8)
            box = Rectangle(width=2.5, height=2.5, stroke_color=c, stroke_width=1.5)
            box.move_to(p + UP * 0.5)

            # Pattern visuals
            visual = self._make_pattern(i, c)
            visual.move_to(box.get_center()).scale_to_fit_width(2.0)

            grp = VGroup(label, box, visual)
            pattern_groups.add(grp)

        self.play(LaggedStart(*[FadeIn(g, shift=UP * 0.3) for g in pattern_groups], lag_ratio=0.25), run_time=2)
        self.wait(0.5)

        # Voice labels
        voice_labels = ["Soprano", "Alto", "Tenor", "Bass"]
        arrows = VGroup()
        for i, (p, c, vl) in enumerate(zip(positions, colors, voice_labels)):
            arr = Arrow(p + DOWN * 0.8, p + DOWN * 1.8, color=c, stroke_width=2)
            vt = Text(vl, font_size=16, color=c).next_to(arr, RIGHT, buff=0.1)
            arrows.add(arr, vt)
        self.play(LaggedStart(*[GrowArrow(arrows[j]) if j % 2 == 0 else FadeIn(arrows[j]) for j in range(len(arrows))], lag_ratio=0.1), run_time=1.2)

        # Combined score bar at bottom
        score_rect = Rectangle(width=12, height=1.2, stroke_color=SOFT_WHITE, stroke_width=1)
        score_rect.move_to(DOWN * 2.8)
        score_label = Text("Sacred Composer — Combined Score", font_size=22, color=GOLD)
        score_label.move_to(score_rect.get_center())

        # Mini note blocks inside score
        notes = VGroup()
        for j in range(32):
            c = colors[j % 4]
            dot = Rectangle(
                width=0.3, height=0.15 + 0.1 * (j % 3),
                fill_color=c, fill_opacity=0.7, stroke_width=0,
            ).move_to(LEFT * 5.5 + RIGHT * j * 0.36 + DOWN * (2.6 + 0.15 * ((j * 7) % 5 - 2)))
            notes.add(dot)

        self.play(Create(score_rect), Write(score_label), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.1) for n in notes], lag_ratio=0.03), run_time=1.5)
        self.wait(1.5)

    def _make_pattern(self, idx, color):
        if idx == 0:  # Fibonacci spiral
            arcs = VGroup()
            fibs = [1, 1, 2, 3, 5, 8]
            a = 0
            for f in fibs:
                arc = Arc(radius=f * 0.08, start_angle=a, angle=PI / 2, color=color, stroke_width=1.5)
                a += PI / 2
                arcs.add(arc)
            return arcs
        elif idx == 1:  # Lorenz-like butterfly
            pts = []
            x, y, z = 0.1, 0, 0
            dt = 0.005
            for _ in range(800):
                dx = 10 * (y - x) * dt
                dy = (x * (28 - z) - y) * dt
                dz = (x * y - 8 / 3 * z) * dt
                x, y, z = x + dx, y + dy, z + dz
                pts.append([x * 0.04, z * 0.04 - 0.8, 0])
            curve = VMobject(color=color, stroke_width=1)
            curve.set_points_smoothly([np.array(p) for p in pts[::4]])
            return curve
        elif idx == 2:  # Cellular automata
            grid = VGroup()
            row = [0] * 15
            row[7] = 1
            for r in range(8):
                for c, v in enumerate(row):
                    if v:
                        sq = Square(side_length=0.12, fill_color=color, fill_opacity=0.8, stroke_width=0)
                        sq.move_to(RIGHT * (c - 7) * 0.14 + DOWN * r * 0.14)
                        grid.add(sq)
                new_row = [0] * 15
                for c in range(1, 14):
                    pat = row[c - 1] * 4 + row[c] * 2 + row[c + 1]
                    new_row[c] = (30 >> pat) & 1  # Rule 30
                row = new_row
            return grid
        else:  # Phyllotaxis
            dots = VGroup()
            golden = (1 + np.sqrt(5)) / 2
            for n in range(80):
                angle = n * 2 * PI / (golden ** 2)
                r = 0.08 * np.sqrt(n)
                d = Dot(
                    point=[r * np.cos(angle), r * np.sin(angle), 0],
                    radius=0.03, color=color,
                )
                dots.add(d)
            return dots
