# Notes for Claude

## Development standard (Yao, 2026-10-23) — governs every change

- **Target client:** a college student who is overstimulated and expects
  a convenient, accurate solution to their study problems. Every feature
  defaults to zero-config convenience and accuracy — if it needs
  explaining or fiddling, it belongs in dev mode, not study mode.
- **Two modes, one truth:** study mode (default) shows only the product —
  twin, problem card, relations, page, map, dialogue, cone. Dev mode
  (`--dev` or the quiet "dev" switch) reveals the instrumentation
  together: stage trace, clarity cycler, latency/config tags, session
  internals. Modes change what is SHOWN, never what is logged — recording
  and per-check metadata run in both.
- **Design language:** chat INTERACTION patterns are fine and encouraged —
  message threads, bubbles, an input box, the mechanics students already
  know from tools they use. What must never be chatbotty is the design
  LANGUAGE: no generic-AI-assistant aesthetic (sparkle/robot iconography,
  purple-gradient AI-product styling), no "AI is thinking…" theater, no
  assistant-persona voice. This reads as a study tool that watches paper,
  with its own identity: the cone, the lamp palette, the desk.

- **Every feature change updates README.md in the same change.** The
  README is the product's front door: if you touch flags, modes, the
  pipeline, requirements, or the UI's behavior, fix the README before
  you're done. Keep its usage examples matching the docstring in
  `cono` — they drift independently otherwise.
- The one-line try in the README (`cono demo`) must keep working
  for a fresh clone with only Python 3 + the `claude` CLI: no camera, no
  Xcode, no pip installs, no JS build step.
- Live capture is browser-side (getUserMedia + client gating); the
  server only receives snaps and runs `claude`. Keep gating thresholds
  in index.html and cono in sync (DIRTY_AT 0.20 / STABLE_AT 0.10,
  GATE_SPREAD 100, the skin-hold floor +0.03 / 15 s timeout).
- **Never binarize** a snap in any clarity pass — thresholding breaks
  faint graphite (measured; standing constraint from report 18 / the
  photo-pipeline harness). Clarity passes stay grayscale/continuous.
  And never send the model images wider than ~1280 px: the API clamps
  at ~1.15 MP, so wider frames get resampled twice and read WORSE.
- If the check prompt or gating thresholds change, rerun
  `tools/make-sample.py` only if the sample itself needs to change — the
  committed frames are the stable test fixture (`sample/` math,
  `sample-chem/` chemistry via tools/make-chem-sample.py).
- The model reply contract is VISIBILITY / WORKING ON / PROBLEM / ON PAGE /
  TALLY / CHECK / KIND(confirm|fix|idle|setup) / GRID / EQUATIONS, in that
  order — fast fields first, because the reply streams (claude -p
  stream-json both ways, partial messages on, MAX_THINKING_TOKENS=0; the
  TALLY line replaces thinking for counting accuracy and CHECK must agree
  with it). The UI renders no dialogue message for idle/setup — the quiet
  line and readability map carry them. CHECK language rules live in
  `../plans/feedback-policy.md` (private repo) — change prompts there
  first, then compile into CHECK_STYLES.
- The twin state (problem card, question registry STATE.questions —
  ground truth once registered, occlusion never rewrites it — per-problem
  threads + explicit-ask ladder counts, Next pin, grid, equations) lives
  in STATE and reaches the browser via /state polls plus /events SSE
  deltas. Chat is /chat with semantic anchors ({kind: line|equation|
  problem|region}; region anchors get a sips full-res crop), Next is
  /next. Default port is 8764 (variant T installs beside the other
  variant).
- Checks remember the page via STATE.last_on_page/last_checks; stuck
  nudges fire after STUCK_S (env CONO_STUCK_S for tests) of quiet.
- `cono doctor` is the preflight; keep it passing after changes.
  `tools/selftest.py` (offline, no `claude` calls) must pass too.
- Nothing the student does may go unlogged: RUNLOG (check-*/run.jsonl)
  receives every check record, chat, rating, suggestion and UI event in
  every mode, independent of SESSION. `SESSION.event()` writes both;
  add new events through it. In-place ratings go through /rate and land
  in the run log, STATE.ratings, and the session manifest's annotation.
- Live streams render per id (`live` Map in index.html): never go back
  to a single shared slot — two checkers + chat stream concurrently.
- The no-page gate (NO_PAGE_AT, paper_frac) only skips automatic checks
  and was set from data; re-measure with `tools/eval-no-page.py` before
  touching it. Skipping on "unchanged page" pixel diffs was measured and
  rejected (new ink is a ~3% diff; a moved page is larger).
- The executable is `cono` (renamed from `cono-check`, 2026-10-27).
  `cono-check` is a committed deprecation shim that execs `cono` —
  keep it working until collaborators' rigs have migrated. Machine-compat
  names stay stable through the rename: CONO_* env vars, session bundle
  field names, and `~/deskcap` paths are unchanged.
- Test end-to-end cheaply: `cono demo` / `demo chem`, POST session
  snaps from `~/deskcap/session-*/snaps/` to /snap, and the stub capture
  tool pattern (CONO_DESKCAP env) for deskview flows.
- This directory is its own git repo (published separately); the
  surrounding `cono/` repo holds private research and captures that must
  never be committed here.
