#!/usr/bin/env python3
"""Re-measure the no-page gate (NO_PAGE_AT in `cono`) against the model's own
VISIBILITY on every recorded check in ~/deskcap: session manifests, run logs
(check-*/run.jsonl) and recovered run logs. A safe threshold skips only
frames the model itself scored 0-2/10 and never one it scored 4+.
Needs Pillow. Usage: tools/eval-no-page.py [--deskcap DIR]"""
import importlib.machinery
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("cc", str(HERE / "cono"))
spec = importlib.util.spec_from_loader("cc", loader)
cc = importlib.util.module_from_spec(spec)
loader.exec_module(cc)
if not cc.PIL_OK:
    sys.exit("needs Pillow (pip install pillow)")
root = Path(sys.argv[sys.argv.index("--deskcap") + 1]) if "--deskcap" in sys.argv else Path.home() / "deskcap"

rows = {}                                   # image path -> visibility
for mf in root.glob("session-*/session.json"):
    try:
        for c in json.loads(mf.read_text()).get("checks", []):
            img = mf.parent / "snaps" / c.get("snap", "")
            if c.get("visibility") is not None and img.exists() and not c.get("skipped"):
                rows[img] = c["visibility"]
    except (ValueError, OSError):
        pass
for rl in list(root.glob("check-*/run.jsonl")) + list(root.glob("check-*/recovered/run-recovered.jsonl")):
    for line in rl.read_text().splitlines():
        try:
            c = json.loads(line)
        except ValueError:
            continue
        if c.get("type") != "check" or c.get("visibility") is None or c.get("skipped"):
            continue
        img = rl.parent / (c["images"][0] if c.get("images") else c.get("snap", ""))
        if img.is_file():
            rows[img] = c["visibility"]
if not rows:
    sys.exit(f"no labeled checks found under {root}")
scored = sorted((cc.paper_frac(p), v, p) for p, v in rows.items())
nopage = sum(1 for _, v, _ in scored if v <= 2)
print(f"{len(scored)} labeled checks · {nopage} the model scored 0-2/10 · current NO_PAGE_AT {cc.NO_PAGE_AT}\n")
print(" thresh  skipped  caught(0-2)  FALSE SKIPS (model saw 4+/10)")
for t in (0.05, 0.08, 0.10, 0.12, 0.15, 0.20, 0.25):
    sk = [x for x in scored if x[0] < t]
    bad = [x for x in sk if x[1] >= 4]
    print(f"  {t:.2f}   {len(sk):5d}   {sum(1 for x in sk if x[1] <= 2):5d}/{nopage:<5d}  {len(bad)}"
          + ("" if not bad else "  e.g. " + ", ".join(f"{p.parent.name}/{p.name} vis {v}" for _, v, p in bad[:3])))
low_good = [x for x in scored if x[1] >= 4][:3]
print("\nlowest paper fractions the model could still read (4+/10):")
for f, v, p in low_good:
    print(f"  {f:.3f}  vis {v}  {p}")
