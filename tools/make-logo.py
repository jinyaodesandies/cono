#!/usr/bin/env python3
"""Regenerate brand/ — the Cono logo as standalone files for Canva and Figma.

Traces the header cone + "Cono" wordmark from index.html (Avenir Next Demi
Bold, 19px, cone 17x19 + 8px gap) into SVGs with the text outlined, so they
never fall back to another font. The cone is drawn at rest, its shade baked
into a solid polygon that reaches the right edge and its rim kept inside the
base, so it holds up at poster size. Renders transparent PNGs with headless
Chrome and lays every variant plus the palette out on one Figma board.

Requires fontTools, shapely, macOS Avenir Next and Google Chrome. The output
is committed, so this only needs rerunning to change the logo itself.

    python3 tools/make-logo.py [out_dir]   # default: brand/
"""
import math, os, re, subprocess, sys, tempfile, pathlib
from fontTools.ttLib import TTCollection
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen
from shapely.geometry import Polygon

OUT = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent / "brand")
OUT.mkdir(parents=True, exist_ok=True)
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PAPER, DESK = "#f4efe4", "#1a1712"
BODY, BASE, SHADE = "#8a6f3c", "#b58b43", "#63502d"  # shade = rgba(26,23,18,.35) over body

# --- font: Avenir Next Demi Bold (CSS weight 600) ---
ttc = TTCollection("/System/Library/Fonts/Avenir Next.ttc")
font = next(f for f in ttc.fonts if f["OS/2"].usWeightClass == 600 and "Italic" not in f["name"].getDebugName(2)
            and "Condensed" not in f["name"].getDebugName(1))
upm = font["head"].unitsPerEm
gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]

# header metrics (px): h1 19px, letter-spacing .01em, cone 17x19 + 8px gap, svg bottom at baseline+2
FS = 19.0
s = FS / upm
cone_scale = min(17/24, 19/27)
cone_w, cone_h = 24*cone_scale, 27*cone_scale
cone_x = (17 - cone_w)/2
baseline = 0.0
cone_top = baseline + 2 - 19 + (19 - cone_h)/2

def text_path(txt, x0):
    pen = SVGPathPen(gs); x = x0
    for ch in txt:
        g = cmap[ord(ch)]
        gs[g].draw(TransformPen(pen, (s, 0, 0, -s, x, baseline)))
        x += hmtx[g][0]*s + 0.01*FS
    return pen.getCommands(), x - 0.01*FS

# --- cone geometry in its own 24x27 viewBox ---
arc = [(12 + 9.6*math.cos(t), 21 + 3.6*math.sin(t)) for t in [i*math.pi/96 for i in range(97)]]
cone_poly = Polygon([(12, 1.5)] + arc)            # apex -> right -> bottom half ellipse -> left
k = math.tan(math.radians(6))
shade_poly = Polygon([(14, 0), (30, 0), (30-27*k, 27), (14-27*k, 27)]).intersection(cone_poly)
def pts(p): return " ".join(f"{x:.3f},{y:.3f}" for x, y in p.exterior.coords[:-1])

def cone_group(rim=True):
    g = [f'<path d="M12 1.5 L21.6 21 A9.6 3.6 0 0 1 2.4 21 Z" fill="{BODY}"/>',
         f'<polygon points="{pts(shade_poly)}" fill="{SHADE}"/>',
         f'<ellipse cx="12" cy="21" rx="9.6" ry="3.6" fill="{BASE}"/>']
    if rim:
        g.append('<ellipse cx="12" cy="21" rx="9.3" ry="3.3" fill="none" stroke="#f2ede3" stroke-opacity="0.25" stroke-width="0.6"/>')
    return "\n    ".join(g)

def svg(w, h, body, bg=None):
    rect = f'<rect width="100%" height="100%" fill="{bg}"/>\n  ' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.3f} {h:.3f}" '
            f'width="{w*40:.0f}" height="{h*40:.0f}">\n  {rect}{body}\n</svg>\n')

def lockup(ink, bg=None, pad=0.0):
    d, tx_end = text_path("Cono", 17 + 8)
    # tight bounds: glyph extents from font bbox of drawn glyphs
    bp = BoundsPen(gs); x = 25
    for ch in "Cono":
        g = cmap[ord(ch)]; gs[g].draw(TransformPen(bp, (s, 0, 0, -s, x, baseline))); x += hmtx[g][0]*s + 0.19
    xmin, ymin, xmax, ymax = bp.bounds
    top = min(ymin, cone_top + 1.5*cone_scale); bot = max(ymax, cone_top + 24.6*cone_scale + 0.3*cone_scale)
    left = cone_x + 2.1*cone_scale; right = xmax
    ox, oy = pad - left, pad - top
    W, H = right - left + 2*pad, bot - top + 2*pad
    body = (f'<g transform="translate({ox:.3f} {oy:.3f})">\n'
            f'  <g transform="translate({cone_x:.3f} {cone_top:.3f}) scale({cone_scale:.5f})">\n    {cone_group()}\n  </g>\n'
            f'  <path d="{d}" fill="{ink}"/>\n</g>')
    return svg(W, H, body, bg)

def icon(bg=None, pad=0.0, square=False):
    x0, y0, x1, y1 = 2.1, 1.5, 21.9, 24.9
    w, h = x1-x0, y1-y0
    if square:
        side = max(w, h) + 2*pad
        ox, oy = (side-w)/2 - x0, (side-h)/2 - y0; W = H = side
    else:
        ox, oy = pad - x0, pad - y0; W, H = w+2*pad, h+2*pad
    body = f'<g transform="translate({ox:.3f} {oy:.3f})">\n    {cone_group()}\n  </g>'
    return svg(W, H, body, bg)

files = {
  "cono-logo-light-ink.svg": lockup(PAPER),              # for dark backgrounds
  "cono-logo-dark-ink.svg": lockup(DESK),                # for light backgrounds
  "cono-logo-on-desk.svg": lockup(PAPER, DESK, pad=6),   # exactly as on the site
  "cono-icon.svg": icon(),
  "cono-icon-square-desk.svg": icon(DESK, pad=5, square=True),  # profile pic / app icon
}
for n, c in files.items():
    (OUT / n).write_text(c)

# --- Figma board: every variant + the palette, one SVG with named layers ---
def inner(name):
    t = (OUT / name).read_text()
    w, h = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', t).groups())
    body = t[t.index(">")+1 : t.rindex("</svg>")].strip().replace('width="100%" height="100%"', f'width="{w}" height="{h}"')
    return body, w, h
def place(name, layer, x, y, width):
    body, w, h = inner(name); k = width/w
    return f'<g id="{layer}" transform="translate({x} {y}) scale({k:.4f})">{body}</g>', h*k
DESK, PAPER, INK = "#1a1712", "#f4efe4", "#3d3426"
W = 1600; out = []
def label(x, y, t, fill=INK, size=18, weight=500):
    return f'<text x="{x}" y="{y}" font-family="Inter" font-size="{size}" font-weight="{weight}" fill="{fill}">{t}</text>'
y = 0
out.append(f'<rect id="Board background" width="{W}" height="1500" fill="#ffffff"/>')
out.append(label(80, 90, "Cono — logo", size=40, weight=700, fill=DESK))
out.append(label(80, 130, "Avenir Next Demi Bold, outlined · traced from the Cono site header", size=18, fill="#7a6f5c"))
# dark panel
out.append(f'<rect id="Panel / dark" x="80" y="180" width="{W-160}" height="380" rx="24" fill="{DESK}"/>')
g, h = place("cono-logo-light-ink.svg", "Cono logo / light ink", 0, 0, 760)
out.append(g.replace('translate(0 0)', f'translate({(W-760)/2} {180+(380-h)/2:.1f})'))
out.append(label(112, 530, "On dark — light ink", fill="#b1a488", size=16))
# light panel
out.append(f'<rect id="Panel / light" x="80" y="600" width="{W-160}" height="380" rx="24" fill="{PAPER}"/>')
g, h = place("cono-logo-dark-ink.svg", "Cono logo / dark ink", 0, 0, 760)
out.append(g.replace('translate(0 0)', f'translate({(W-760)/2} {600+(380-h)/2:.1f})'))
out.append(label(112, 950, "On light — dark ink", fill="#7a6f5c", size=16))
# icons
out.append(f'<rect id="Panel / icon" x="80" y="1020" width="380" height="380" rx="24" fill="{PAPER}"/>')
g, h = place("cono-icon.svg", "Cono icon", 0, 0, 220)
out.append(g.replace('translate(0 0)', f'translate({80+(380-220)/2} {1020+(380-h)/2:.1f})'))
g, h = place("cono-icon-square-desk.svg", "Cono icon / square on desk", 0, 0, 380)
out.append(g.replace('translate(0 0)', 'translate(500 1020)'))
# swatches
sw = [("Desk","#1a1712"),("Paper","#f4efe4"),("Lamp","#f2b32c"),("Cone body","#8a6f3c"),
      ("Cone shade","#63502d"),("Cone base","#b58b43"),("Leaf","#9ecb6b"),("Clay","#d9573c")]
for i,(n,c) in enumerate(sw):
    cx, cy = 940 + (i%4)*150, 1040 + (i//4)*180
    out.append(f'<g id="Swatch / {n}"><rect x="{cx}" y="{cy}" width="120" height="100" rx="14" fill="{c}" stroke="#e4ddd0"/>'
               + label(cx, cy+128, n, fill=DESK, size=15, weight=600) + label(cx, cy+150, c, fill="#7a6f5c", size=14) + '</g>')
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="1500" viewBox="0 0 {W} 1500">\n' + "\n".join(out) + "\n</svg>\n"
(OUT / "cono-logo-figma-board.svg").write_text(svg)

# --- PNGs: transparent, 3000px wide (lockups) / 2048px tall (icons) ---
tmp = pathlib.Path(tempfile.mkdtemp())
for svgf in sorted(OUT.glob("cono-*.svg")):
    if "board" in svgf.name:
        continue
    w, h = map(float, re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svgf.read_text()).groups())
    target = 2048 if "icon" in svgf.name else 3000
    W = target if w >= h else round(target*w/h); H = round(W*h/w)
    html = tmp / "r.html"
    html.write_text(f'<html><body style="margin:0;background:transparent"><img src="file://{svgf.resolve()}" style="display:block;width:{W}px;height:{H}px"></body></html>')
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                    f"--window-size={W},{H}", f"--screenshot={(OUT / svgf.name.replace('.svg', '.png')).resolve()}",
                    f"file://{html}"], capture_output=True, timeout=60)
print("wrote", OUT)
