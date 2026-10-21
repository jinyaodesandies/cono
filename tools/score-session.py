#!/usr/bin/env python3
"""score-session.py — turn a session bundle's annotations into a config report.

Usage: tools/score-session.py ~/deskcap/session-<ts>/ [...]
Reads session.json (checks + the student's Helped/Didn't/Wrong annotations),
prints per-config and per-dimension tables, and writes scored.md into the
bundle. Pure analysis - no claude calls.
"""
import json, sys
from collections import defaultdict
from pathlib import Path


def rate(rows):
    ann = [r for r in rows if (r.get("annotation") or {}).get("verdict")]
    helped = sum(1 for r in ann if r["annotation"]["verdict"] == "helped")
    wrong = sum(1 for r in ann if r["annotation"]["verdict"] == "wrong")
    lat = [r["latency_ms"] / 1000 for r in rows if r.get("latency_ms")]
    return {"checks": len(rows), "rated": len(ann), "helped": helped, "wrong": wrong,
            "helped_rate": round(helped / len(ann), 2) if ann else None,
            "mean_latency_s": round(sum(lat) / len(lat), 1) if lat else None}


def table(title, groups):
    lines = [f"### by {title}", "",
             "| " + title + " | checks | rated | helped | wrong | helped-rate | mean latency |",
             "|---|---|---|---|---|---|---|"]
    for key, rows in sorted(groups.items()):
        r = rate(rows)
        lines.append(f"| {key} | {r['checks']} | {r['rated']} | {r['helped']} | {r['wrong']} | "
                     f"{r['helped_rate'] if r['helped_rate'] is not None else '—'} | "
                     f"{r['mean_latency_s']}s |")
    return lines + [""]


def main():
    for arg in sys.argv[1:]:
        d = Path(arg).expanduser()
        m = json.loads((d / "session.json").read_text())
        checks = m["checks"]
        out = [f"# Session score — {d.name}",
               f"duration {m['duration_s']}s · {len(checks)} checks · camera {m.get('camera_label', '?')}",
               f"stuck: {m['annotations'].get('stuck', '')!r} · wanted: {m['annotations'].get('wanted', '')!r}", ""]
        overall = rate(checks)
        out.append(f"**Overall:** {overall['helped']}/{overall['rated']} helped "
                   f"({overall['helped_rate']}), {overall['wrong']} wrong, "
                   f"mean latency {overall['mean_latency_s']}s")
        out.append("")
        for dim, key in (("style", lambda c: c.get("config", {}).get("style", c.get("style", "?"))),
                         ("structure", lambda c: c.get("config", {}).get("structure", "?")),
                         ("width", lambda c: c.get("config", {}).get("width", "?")),
                         ("contrast", lambda c: c.get("contrast", "?")),
                         ("reason", lambda c: c.get("reason", "?"))):
            groups = defaultdict(list)
            for c in checks:
                groups[key(c)].append(c)
            out += table(dim, groups)
        stages = defaultdict(list)          # where does check latency live?
        for c in checks:
            for s in c.get("stages") or []:
                stages[s["stage"]].append(s["ms"])
        if stages:
            out += ["### stage timing (ms from check start)", "",
                    "| stage | n | mean | max |", "|---|---|---|---|"]
            for name, ms in sorted(stages.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
                out.append(f"| {name} | {len(ms)} | {round(sum(ms) / len(ms))} | {max(ms)} |")
            out.append("")
        notes = [(c["snap"], c["annotation"]["note"]) for c in checks
                 if (c.get("annotation") or {}).get("note")]
        if notes:
            out.append("### student notes")
            out += [f"- **{s}**: {n}" for s, n in notes] + [""]
        text = "\n".join(out)
        (d / "scored.md").write_text(text)
        print(text)
        print(f"\nwritten: {d / 'scored.md'}\n")


if __name__ == "__main__":
    main()
