#!/usr/bin/env python3
"""Contract regression: the reply keeps its shape at the visibility floor.

Builds a deliberately unreadable frame (a real recorded frame destroyed
by down-and-up scaling - the run1 "total-failure floor"), sends it through
the real check prompt, and asserts the contract holds where it has broken
before (agent-report 14, class C):

  - the reply parses: VISIBILITY present, GRID rows, KIND one of the four
  - ON PAGE at the floor keeps its shape: L-numbered lines (the floor form
    is exactly "L1 (?)"), never prose describing the scene
  - no meta-commentary: no Claude-Code persona, no "this looks like a
    test/demo/sample", no "you uploaded/pasted"

Costs one `claude` call per run; it is a dev/regression tool, not part of
doctor. Usage: tools/regress-contract.py [model] [--frame JPG]   (default:
opus, and the newest frame recorded in ~/deskcap)
"""
import importlib.machinery
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("cc", str(HERE / "cono"))
spec = importlib.util.spec_from_loader("cc", loader)
cc = importlib.util.module_from_spec(spec)
loader.exec_module(cc)

META_RE = re.compile(
    r"claude code|this (message|image|frame) (appears|looks|seems)|"
    r"test[ /-]?(input|capture)|demo input|sample (capture|input|session)|"
    r"tutor prompt|uploaded|pasted|sent (me|you) an? (image|photo)|as an ai", re.I)


def main():
    args = sys.argv[1:]
    src = None
    if "--frame" in args:
        i = args.index("--frame")
        src = Path(args[i + 1]).expanduser()
        del args[i:i + 2]
    model = args[0] if args else "opus"
    if src is None:
        frames = sorted(Path.home().glob("deskcap/*/frame-0001.jpg"), key=lambda p: p.stat().st_mtime)
        if not frames:
            sys.exit("no recorded frame in ~/deskcap — run cono once, or pass --frame JPG")
        src = frames[-1]
    with tempfile.TemporaryDirectory() as td:
        tiny = Path(td) / "tiny.jpg"
        floor = Path(td) / "floor.jpg"
        subprocess.run(["sips", "--resampleWidth", "48", str(src), "--out", str(tiny)],
                       capture_output=True, check=True)
        subprocess.run(["sips", "--resampleWidth", "960", str(tiny), "--out", str(floor)],
                       capture_output=True, check=True)
        prompt = cc.PROMPT.format(context="", check_style=cc.CHECK_STYLES["question"],
                                  no_new_rule=cc.NO_NEW_RULE, escalation="")
        print(f"contract regression ({model}): sending the floor frame…")
        raw, first = cc.claude_stream(
            [{"type": "text", "text": prompt}, cc.img_block(floor)], model)

    r = cc.parse_report(raw)
    fails = []
    if r["visibility"] is None:
        fails.append("VISIBILITY missing or unparsed")
    if r["kind"] not in ("confirm", "fix", "idle", "setup"):
        fails.append(f"KIND out of contract: {r['kind']!r}")
    if not r["grid"]:
        fails.append("GRID rows missing")
    bad_lines = [l for l in r["on_page"].splitlines()
                 if l.strip() and not re.match(r"^L\d+\b", l.strip())]
    if bad_lines:
        fails.append(f"ON PAGE broke shape (prose at the floor): {bad_lines[:2]}")
    m = META_RE.search(raw)
    if m:
        fails.append(f"meta-commentary leaked: …{raw[max(0, m.start() - 20):m.end() + 20]!r}…")

    print(f"  visibility: {r['visibility']}  kind: {r['kind']}  "
          f"on_page: {r['on_page']!r:.60}  grid rows: {len(r['grid'])}")
    if fails:
        print("FAIL")
        for f in fails:
            print("  ✗ " + f)
        sys.exit(1)
    print("PASS - contract shape held at the visibility floor")


if __name__ == "__main__":
    main()
