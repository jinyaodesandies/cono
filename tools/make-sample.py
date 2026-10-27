#!/usr/bin/env python3
"""Regenerate sample/ — a synthetic deskcap session for `cono demo`.

Six frames of a student factoring a quadratic on notebook paper, written
line by line, with a planted sign error in the factoring step: the check
should point at it without giving the corrected factors. log.csv's
changed_frac values are chosen to exercise the gating (first look →
writing → settled → writing → settled).

Requires Pillow and a macOS handwriting font. The generated frames are
committed, so this only needs rerunning to change the sample itself.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "sample"
W, H = 1920, 1440
FONT = "/System/Library/Fonts/Supplemental/Bradley Hand Bold.ttf"
INK = (44, 48, 92)
RULE = (170, 190, 215)

LINES = [
    "Solve   x^2 - 5x + 6 = 0",
    "factor the left side:",
    "( x - 2 ) ( x + 3 ) = 0",      # the planted error: should be (x - 3)
    "so  x = 2   or   x = -3",
]
# (frame, lines shown, changed_frac) — "" = first frame, no diff yet
FRAMES = [(1, 1, ""), (2, 2, "0.3012"), (3, 3, "0.2764"),
          (4, 3, "0.0431"), (5, 4, "0.2688"), (6, 4, "0.0512")]


def draw_line(d, text, x, y, size):
    """Render text, raising the character after each ^ as an exponent."""
    font = ImageFont.truetype(FONT, size)
    sup = ImageFont.truetype(FONT, int(size * 0.62))
    i = 0
    while i < len(text):
        if text[i] == "^" and i + 1 < len(text):
            d.text((x, y - size * 0.35), text[i + 1], font=sup, fill=INK)
            x += d.textlength(text[i + 1], font=sup)
            i += 2
        else:
            d.text((x, y), text[i], font=font, fill=INK)
            x += d.textlength(text[i], font=font)
            i += 1


def page(n_lines):
    img = Image.new("RGB", (W, H), (96, 74, 58))            # desk
    paper = Image.new("RGB", (W - 360, H - 200), (248, 246, 240))
    d = ImageDraw.Draw(paper)
    for y in range(140, paper.height, 110):                  # notebook rules
        d.line([(60, y), (paper.width - 60, y)], fill=RULE, width=3)
    d.line([(170, 0), (170, paper.height)], fill=(230, 160, 160), width=3)
    for i in range(n_lines):
        draw_line(d, LINES[i], 210, 150 + i * 220, 74)
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
