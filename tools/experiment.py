#!/usr/bin/env python3
"""experiment.py — replay a recorded capture through a matrix of configs.

A live session can only test what the student experiences (feedback style,
timing). Everything else — snap frequency, image preprocessing, prompt
structure — is better tested offline: same recorded frames, every config,
directly comparable. This runs that matrix against any capture directory
(a deskcap dir with log.csv, the bundled sample, or a session bundle's
frames) and writes a side-by-side report.

Usage:
  tools/experiment.py DIR [DIR2 …] [--model sonnet] [--workers 4]
                      [--configs baseline,enhance,…] [--out DIR]

Costs real `claude` calls: roughly (configs × ~3 snaps) per input dir.
"""
import argparse, concurrent.futures, csv, json, re, statistics, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

VISIBILITY_AND_ONPAGE = """VISIBILITY: n/10 - one line: what the camera sees; whether a page is in frame and which edges are cut off; whether small details (exponents, subscripts, fraction bars) are readable; note blur or glare.
ON PAGE: transcribe what is written on the page exactly as written, preserving the student's own errors - never silently correct anything. If no page or writing is visible, say what IS visible instead."""

LITERAL_ONPAGE = """VISIBILITY: n/10 - one line: what the camera sees; whether a page is in frame and which edges are cut off; whether small details (exponents, subscripts, fraction bars) are readable; note blur or glare.
ON PAGE: transcribe line by line, numbered L1, L2, L3 … Copy exactly what is written, character for character, preserving the student's own errors - NEVER correct, complete, or normalize anything. Write (?) for any token you cannot read. After transcribing, re-read the image once and fix only your transcription mistakes, never the student's math."""

CHECK_PARA = """CHECK: 1-3 sentences checking the work. If there is a mistake, say exactly where it is (which line or step) and ask a guiding question - do not give the corrected answer. If the work looks right so far, confirm it and suggest the next step. If nothing is readable, give one concrete tip to fix the framing."""

def prompt_current(path):
    return (f"You are Cono, an AI study tutor watching a student's paper through a camera. "
            f"Read the image file: {path}\n\nRespond in EXACTLY this plain-text format, no markdown:\n\n"
            f"{VISIBILITY_AND_ONPAGE}\n{CHECK_PARA}")

def prompt_literal(path):
    return (f"You are Cono, an AI study tutor watching a student's paper through a camera. "
            f"Read the image file: {path}\n\nRespond in EXACTLY this plain-text format, no markdown:\n\n"
            f"{LITERAL_ONPAGE}\n{CHECK_PARA}")

def prompt_transcribe_only(path):
    return (f"You are a transcription engine for a study tutor. Read the image file: {path}\n\n"
            f"Respond in EXACTLY this plain-text format, no markdown:\n\n{LITERAL_ONPAGE}")

def prompt_reason_only(transcript):
    return (f"You are Cono, an AI study tutor. A faithful transcription of the student's "
            f"handwritten page (their own errors preserved) is:\n\n{transcript}\n\n"
            f"Respond in EXACTLY this plain-text format, no markdown:\n\n{CHECK_PARA}")


# ---- image preprocessing ----

def prep_none(img):
    return img

def prep_enhance(img):
    return ImageOps.autocontrast(img, cutoff=1).filter(
        ImageFilter.UnsharpMask(radius=2, percent=120, threshold=3))

def prep_down960(img):
    w, h = img.size
    if w > 960:
        img = img.resize((960, int(h * 960 / w)), Image.LANCZOS)
    return img

def prep_gray(img):
    return ImageOps.autocontrast(img.convert("L"), cutoff=1)


# ---- snap selection (gating simulation over log.csv) ----

def load_rows(d):
    """[(t_seconds, filename, changed_frac)] from a capture dir or session bundle."""
    if (d / "frames").is_dir():                      # 10-min session bundle
        frames = sorted((d / "frames").glob("frame-*.jpg"))
        sig = []
        if (d / "signal.csv").exists():
            with open(d / "signal.csv") as f:
                next(f, None)
                sig = [(int(a) / 1000, float(b))
                       for a, b in (l.strip().split(",") for l in f if l.strip())]
        dense = 3.0
        rows = []
        for i, p in enumerate(frames):
            t = i * dense
            window = [cf for ts, cf in sig if t - dense < ts <= t]
            rows.append((t, f"frames/{p.name}", max(window) if window else None))
        return rows
    log = d / "log.csv"
    if log.exists():
        rows = []
        t0 = None
        with open(log, newline="") as f:
            for r in csv.DictReader(f):
                if not r.get("file"):
                    continue
                ts = datetime.fromisoformat(r["timestamp"].replace("Z", "+00:00")).timestamp()
                t0 = t0 if t0 is not None else ts
                cf = float(r["changed_frac"]) if r.get("changed_frac") else None
                rows.append((ts - t0, r["file"], cf))
        return rows
    sys.exit(f"{d}: no log.csv")

def pick_gated(rows, gap_s, dirty_at=0.20, stable_at=0.10, max_dirty_s=20):
    picks = [(rows[0][1], "first look")]
    last = rows[0][0]
    dirty, dirty_since = False, 0
    for t, name, cf in rows[1:]:
        if cf is not None and cf > dirty_at:
            if not dirty:
                dirty_since = t
            dirty = True
        settled = cf is not None and cf < stable_at
        overdue = dirty and t - dirty_since > max_dirty_s
        if dirty and (settled or overdue) and t - last >= gap_s:
            picks.append((name, "page settled" if settled else "checking in"))
            dirty, last = False, t
    return picks

def pick_fixed(rows, every_s):
    picks, last = [], -1e9
    for t, name, cf in rows:
        if t - last >= every_s:
            picks.append((name, f"every {every_s}s"))
            last = t
    return picks

def cap_picks(picks, n=12):
    """Keep cost bounded on long sessions: first look + an even spread."""
    if len(picks) <= n:
        return picks
    rest = picks[1:]
    step = len(rest) / (n - 1)
    return [picks[0]] + [rest[int(i * step)] for i in range(n - 1)]


CONFIGS = {
    #  name:       (picker,                      prep,         mode)
    "baseline":   (lambda r: pick_gated(r, 5),   prep_none,    "current"),
    "gated15":    (lambda r: pick_gated(r, 15),  prep_none,    "current"),
    "fixed15":    (lambda r: pick_fixed(r, 15),  prep_none,    "current"),
    "enhance":    (lambda r: pick_gated(r, 5),   prep_enhance, "current"),
    "down960":    (lambda r: pick_gated(r, 5),   prep_down960, "current"),
    "gray":       (lambda r: pick_gated(r, 5),   prep_gray,    "current"),
    "literal":    (lambda r: pick_gated(r, 5),   prep_none,    "literal"),
    "twopass":    (lambda r: pick_gated(r, 5),   prep_none,    "twopass"),
}


def run_claude(prompt, model, allow_read=True):
    cmd = ["claude", "-p", "--model", model]
    if allow_read:
        cmd.append("--allowedTools=Read")
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=240)
    return r.stdout.strip() or r.stderr.strip() or "(no response)"


def parse(text):
    out = {"visibility": None, "on_page": "", "check": ""}
    field = None
    for line in text.splitlines():
        m = re.match(r"\s*(VISIBILITY|ON PAGE|CHECK)\s*:\s*(.*)", line, re.I)
        if m:
            field, rest = m.group(1).upper(), m.group(2)
            if field == "VISIBILITY":
                s = re.match(r"\s*(\d+)\s*/\s*10", rest)
                out["visibility"] = int(s.group(1)) if s else None
            elif field == "ON PAGE":
                out["on_page"] = rest.strip()
            else:
                out["check"] = rest.strip()
        elif field == "ON PAGE":
            out["on_page"] += "\n" + line
        elif field == "CHECK":
            out["check"] += "\n" + line
    out["on_page"], out["check"] = out["on_page"].strip(), out["check"].strip()
    return out


def run_one(src_dir, cfg_name, out_dir, snap, reason, model):
    picker, prep, mode = CONFIGS[cfg_name]
    img_dir = out_dir / cfg_name
    img_dir.mkdir(parents=True, exist_ok=True)
    img = prep(Image.open(src_dir / snap).convert("RGB"))
    p = img_dir / Path(snap).name
    img.convert("RGB").save(p, quality=85)
    w, h = img.size
    est_tokens = round(w * h / 750)
    t0 = time.time()
    if mode == "twopass":
        t1 = parse(run_claude(prompt_transcribe_only(p), model))
        r2 = run_claude(prompt_reason_only(t1["on_page"] or "(nothing transcribed)"), model, allow_read=False)
        result = {"visibility": t1["visibility"], "on_page": t1["on_page"],
                  "check": parse(r2)["check"] or r2, "calls": 2}
    else:
        pr = prompt_literal(p) if mode == "literal" else prompt_current(p)
        result = {**parse(run_claude(pr, model)), "calls": 1}
    result.update(snap=snap, reason=reason, latency_s=round(time.time() - t0, 1),
                  image_px=f"{w}x{h}", image_kb=p.stat().st_size // 1024,
                  est_image_tokens=est_tokens)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--configs", default=",".join(CONFIGS))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    cfgs = [c for c in args.configs.split(",") if c in CONFIGS]
    out = Path(args.out) if args.out else \
        Path.home() / "deskcap" / "experiments" / datetime.now().strftime("%Y-%m-%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)

    all_results = {}
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(args.workers) as ex:
        for d in args.dirs:
            d = Path(d).expanduser()
            rows = load_rows(d)
            for cfg in cfgs:
                picks = cap_picks(CONFIGS[cfg][0](rows))
                for snap, reason in picks:
                    jobs.append((d.name, cfg, ex.submit(
                        run_one, d, cfg, out / d.name, snap, reason, args.model)))
        total = len(jobs)
        print(f"{total} checks across {len(cfgs)} configs → {out}")
        done = 0
        for dname, cfg, fut in jobs:
            try:
                r = fut.result()
            except Exception as e:
                r = {"error": str(e), "snap": "?", "reason": "?"}
            all_results.setdefault(dname, {}).setdefault(cfg, []).append(r)
            done += 1
            print(f"  [{done}/{total}] {dname}/{cfg}/{r.get('snap')}  "
                  f"vis={r.get('visibility')}  {r.get('latency_s', '?')}s")

    (out / "results.json").write_text(json.dumps(all_results, indent=1))

    # report
    lines = [f"# Experiment report — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}Z",
             f"model: {args.model}", ""]
    for dname, by_cfg in all_results.items():
        lines += [f"## {dname}", "",
                  "| config | snaps | calls | mean vis | mean latency | img tokens/snap |",
                  "|---|---|---|---|---|---|"]
        for cfg, rs in by_cfg.items():
            ok = [r for r in rs if "error" not in r]
            vis = [r["visibility"] for r in ok if r.get("visibility") is not None]
            lines.append("| {} | {} | {} | {} | {}s | {} |".format(
                cfg, len(rs), sum(r.get("calls", 1) for r in ok),
                round(statistics.mean(vis), 1) if vis else "—",
                round(statistics.mean([r["latency_s"] for r in ok]), 1) if ok else "—",
                ok[0]["est_image_tokens"] if ok else "—"))
        lines.append("")
        for cfg, rs in by_cfg.items():
            lines.append(f"### {dname} / {cfg}")
            for r in rs:
                if "error" in r:
                    lines.append(f"- ERROR: {r['error']}")
                    continue
                lines += [f"**{r['snap']}** ({r['reason']}, vis {r.get('visibility')}, {r['latency_s']}s, {r['image_px']}, {r['image_kb']}KB)",
                          "", "```", (r.get("on_page") or "(no transcription)")[:600], "```",
                          f"> {r.get('check', '')[:400]}", ""]
    (out / "report.md").write_text("\n".join(lines))
    print(f"\nreport: {out}/report.md")


if __name__ == "__main__":
    main()
