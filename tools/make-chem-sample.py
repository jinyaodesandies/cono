#!/usr/bin/env python3
"""Regenerate sample-chem/ — a synthetic chemistry session for testing.

Eight frames of handwritten chem homework written line by line, with two
planted errors the checks should catch hint-first and one correct final
line they should confirm:
  #1  balancing: C3H8 + 4O2 -> 3CO2 + 4H2O   (4 O2 is wrong; 5 is right)
  #2  sig figs: final answer written 32.86800 g from 3-sig-fig data
log.csv changed_frac values exercise the gating (first look → writing →
settled → writing → settled → writing → settled).

Requires Pillow and a macOS handwriting font. Generated frames are
committed as a stable fixture; rerun only to change the sample itself.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "sample-chem"
W, H = 1920, 1440
FONT = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
INK = (44, 48, 92)
RULE = (170, 190, 215)

# _ before a character renders it as a subscript, ^ as a superscript
LINES = [
    "1. Balance:  C_3H_8 + O_2 -> CO_2 + H_2O",
    "C_3H_8 + 4O_2 -> 3CO_2 + 4H_2O",            # planted error #1 (needs 5 O2)
    "2. grams of CO_2 from 11.0 g C_3H_8?",
    "11.0 g / 44.1 g/mol = 0.249 mol C_3H_8",
    "0.249 mol x 3 = 0.747 mol CO_2",
    "0.747 mol x 44.0 g/mol = 32.86800 g CO_2",  # planted error #2 (sig figs)
    "3. molar mass of H_2O = 18.02 g/mol",       # correct — should be confirmed
]
# (frame, lines shown, changed_frac) — "" = first frame, no diff yet
FRAMES = [(1, 1, ""), (2, 2, "0.3012"), (3, 2, "0.0512"), (4, 3, "0.2764"),
          (5, 5, "0.2688"), (6, 5, "0.0431"), (7, 6, "0.2910"), (8, 7, "0.0489")]


def draw_line(d, text, x, y, size):
    """Render text; _c drops c to a subscript, ^c raises it to a superscript."""
    font = ImageFont.truetype(FONT, size)
    small = ImageFont.truetype(FONT, int(size * 0.62))
    i = 0
    while i < len(text):
        if text[i] in "_^" and i + 1 < len(text):
            dy = size * 0.45 if text[i] == "_" else -size * 0.35
            d.text((x, y + dy), text[i + 1], font=small, fill=INK)
            x += d.textlength(text[i + 1], font=small)
            i += 2
        else:
            d.text((x, y), text[i], font=font, fill=INK)
            x += d.textlength(text[i], font=font)
            i += 1


def page(n_lines):
    img = Image.new("RGB", (W, H), (96, 74, 58))            # desk
    paper = Image.new("RGB", (W - 360, H - 200), (248, 246, 240))
    d = ImageDraw.Draw(paper)
    for y in range(130, paper.height, 95):                   # notebook rules
        d.line([(60, y), (paper.width - 60, y)], fill=RULE, width=3)
    d.line([(170, 0), (170, paper.height)], fill=(230, 160, 160), width=3)
    for i in range(n_lines):
        draw_line(d, LINES[i], 200, 110 + i * 160, 60)
    paper = paper.rotate(-1.6, expand=True, fillcolor=(96, 74, 58),
                         resample=Image.BICUBIC)
    img.paste(paper, (200, 110))
    return img


def main():
    OUT.mkdir(exist_ok=True)
    rows = ["n,timestamp,file,width,height,bytes,changed_frac,mean_abs_diff,frames_seen"]
    for n, n_lines, changed in FRAMES:
        name = f"frame-{n:04d}.jpg"
        page(n_lines).save(OUT / name, quality=82)
        size = (OUT / name).stat().st_size
        mad = "" if changed == "" else f"{float(changed) * 90:.2f}"
        rows.append(f"{n},2026-10-21T12:00:{n * 4:02d}Z,{name},{W},{H},{size},{changed},{mad},{n * 120}")
    (OUT / "log.csv").write_text("\n".join(rows) + "\n")
    print(f"wrote {len(FRAMES)} frames + log.csv to {OUT}")


if __name__ == "__main__":
    main()
