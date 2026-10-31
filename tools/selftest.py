#!/usr/bin/env python3
"""Offline self-test: no camera, no `claude` calls, stdlib only (the no-page
gate check is skipped without Pillow). Covers the pure logic the 2026-10-29
round added: the EQUATIONS "same" token saver, the answered-problem note,
page-level messages staying in view, the no-page gate, and the run log. Usage: tools/selftest.py"""
import importlib.machinery
import importlib.util
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
loader = importlib.machinery.SourceFileLoader("cc", str(HERE / "cono"))
spec = importlib.util.spec_from_loader("cc", loader)
cc = importlib.util.module_from_spec(spec)
loader.exec_module(cc)

fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  ({extra})" if extra else ""))
    if not cond:
        fails.append(name)


REPLY = """VISIBILITY: 8/10 - flat sheet
WORKING ON: nothing new
PROBLEM: a | Maximum electrons in an atom with n = 4 | summed to 34
ON PAGE: a
L1 = 34
TALLY: none
CHECK: Part a still reads 34.
KIND: idle
GRID:
2222
0000
EQUATIONS: same"""

r = cc.parse_report(REPLY)
check("EQUATIONS: same parses as keep, not as a relation", r.get("equations_same") and r["equations"] == [])
with cc.STATE.lock:
    cc.STATE.problem = {"label": "a", "question": "q", "progress": ""}
    cc.STATE.equations = [{"eq": "N = 2n^2", "name": "shell capacity"}]
    cc.absorb_twin({**r, "time": "00:00"}, "s1.jpg")
    check("same on the same problem keeps the relations", len(cc.STATE.equations) == 1)
    r2 = {**r, "time": "00:00", "problem": {"label": "b", "question": "q2", "progress": ""}}
    cc.absorb_twin(r2, "s2.jpg")
    check("same on a different problem never shows stale relations", cc.STATE.equations == [])
    cc.STATE.problem = {"label": "a", "question": "q", "progress": ""}
    cc.STATE.answered["a"] = True
    check("answered problem: checks are told not to re-hint", "already given the student the full answer" in cc.build_context())
    cc.STATE.answered.clear()
    check("unanswered problem: no such note", "already given the student" not in cc.build_context())
    cc.STATE.threads = {"page": [{"who": "you", "text": "early", "id": 1}],
                        "a": [{"who": "cono", "text": "note", "id": 2}]}
    check("page-level messages stay in the problem's thread", [m["id"] for m in cc.STATE.thread()] == [1, 2])
    p = cc.CHAT_PROMPT.format(anchor_note="", problem="", last_on_page="", last_checks="", thread="",
                              asks=1, text="x", intent_note=cc.CHAT_INTENTS["tricks"][1])
    check("trick-question scan note reaches the chat prompt", "page scan" in p and "opens with the answer" in p)

if cc.PIL_OK:
    # real recorded pages are measured by tools/eval-no-page.py; here, a plain
    # paper-colored frame stands in for "a page is in view"
    with tempfile.TemporaryDirectory() as d:
        page = Path(d) / "page.jpg"
        cc._PILImage.new("RGB", (640, 480), (244, 239, 228)).save(page)
        check("no-page gate never fires on a frame full of paper", cc.paper_frac(page) >= cc.NO_PAGE_AT)
        dark = Path(d) / "lap.jpg"
        cc._PILImage.new("RGB", (640, 480), (150, 40, 40)).save(dark)
        check("no-page gate fires on a frame with no paper", cc.paper_frac(dark) < cc.NO_PAGE_AT)
else:
    print("skip  no-page gate checks (Pillow not installed: the gate is off, nothing is skipped)")

with tempfile.TemporaryDirectory() as d:
    cc.RUNLOG.path = Path(d) / "run.jsonl"
    cc.SESSION.event("suggestion", text="t")      # no session active: still logged
    rec = json.loads(cc.RUNLOG.path.read_text().splitlines()[-1])
    check("run log records events with no session recording", rec["type"] == "suggestion" and rec["session"] is None)

print(f"\n{'all passed' if not fails else str(len(fails)) + ' failed'}")
sys.exit(1 if fails else 0)
