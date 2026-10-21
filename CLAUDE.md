# Notes for Claude

- **Every feature change updates README.md in the same change.** The
  README is the product's front door: if you touch flags, modes, the
  pipeline, requirements, or the UI's behavior, fix the README before
  you're done. Keep its usage examples matching the docstring in
  `cono-check` — they drift independently otherwise.
- The one-line try in the README (`cono-check demo`) must keep working
  for a fresh clone with only Python 3 + the `claude` CLI: no camera, no
  Xcode, no pip installs, no JS build step.
- Live capture is browser-side (getUserMedia + client gating); the
  server only receives snaps and runs `claude`. Keep gating thresholds
  in index.html and cono-check in sync (DIRTY_AT 0.20 / STABLE_AT 0.10).
- If the check prompt or gating thresholds change, rerun
  `tools/make-sample.py` only if the sample itself needs to change — the
  committed frames are the stable test fixture.
- This directory is its own git repo (published separately); the
  surrounding `cono/` repo holds private research and captures that must
  never be committed here.
