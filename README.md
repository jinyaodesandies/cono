# Cono check

Point the Mac's Desk View camera at your handwritten work and get a live
**digital twin of your page**: the problem you're on pinned as a card, the
relations it runs on typeset with `?` marking what you haven't found yet,
a page-shaped map of what the camera could and couldn't read, and a
running dialogue about the problem — Cono points at mistakes and asks a
question first; it never blurts the answer. Replies stream in: first
words in about a second, done in a few.

This is the checking component of Cono, an AI study tutor that watches
paper while you work. It runs locally: your browser does the watching,
and a small Python server runs the reading through the `claude` CLI.

## Try it in one line

No camera needed — this replays a bundled sample session (a student
factoring a quadratic, with a mistake in it) through the full pipeline:

```bash
git clone https://github.com/jinyaodesandies/cono-check && cono-check/cono-check demo
```

Your browser opens to the session; within seconds the twin fills in —
problem card, relations, readability map — and the first note lands in
the dialogue, pointing at the factoring error without giving away the
fix. Type back at it, or click a spot on the page image to ask about
exactly that spot. There's a chemistry version too — `cono-check demo
chem` replays a stoichiometry page with a mis-balanced equation and a
significant-figures slip.

You need macOS, Python 3, and the [Claude Code CLI](https://claude.com/claude-code)
installed and logged in (`claude` does the reading — no API key setup).

## Use it on your own work

```bash
cono-check/cono-check            # the Desk View camera — top-down on your page
cono-check/cono-check browser    # fallback: any camera the browser can see
```

**Desk View is the default and the point**: the Mac's top-down desk
camera (built in on M4-and-later Macs) watches the page lying flat where
you naturally write — Cono looks at your desk, not at you.
Browsers can't open that camera, so this mode captures through `deskcap`,
a small Swift tool that builds itself from the bundled source on first
run (needs the Xcode command line tools: `xcode-select --install`), and
your terminal app needs camera permission — macOS asks once. The camera
view sits at the side as a framing aid — the twin is the main event —
and the video is display-only and never leaves your machine.

**Browser mode** (`cono-check browser`) is the fallback for Macs without
Desk View — it works with any camera the browser can see:
the built-in one (hold the page up facing the screen), a webcam, or an
iPhone near your Mac via Continuity Camera — pick one from the camera
menu under the video. If the picture keeps cropping to your face, turn
off Center Stage in Control Center → Video Effects.

Either way: when you pause writing, Cono snaps one frame, reads it, and
the twin updates. There's a "Check now" button when you don't want to
wait, and in browser mode a "Pause camera" button that turns the camera
fully off.

Before taking it somewhere that matters (class, a tutoring session),
run `cono-check doctor` — a ten-second preflight that verifies the
`claude` CLI (and its streaming support), the capture tool, Desk View,
and camera permission, with a fix suggestion for anything that fails.

Other flags:

```bash
cono-check --model opus          # pick the model (default: opus)
cono-check --replay DIR          # replay any recorded session directory
cono-check --port 9000           # serve somewhere else (default: 8764)
cono-check --contrast strong     # writing clarity: off | auto (default) | strong
cono-check --no-contrast         # same as --contrast off
cono-check --no-open             # don't open the browser automatically
```

## The twin

**Problem card.** The question you're currently on, extracted from the
worksheet and pinned at the top with Cono's read of your progress on it.
Questions are remembered: once Cono has read a question clearly it goes
into a per-session registry and becomes ground truth — your hand, your
pen, or a shadow hovering over the printed sheet is never treated as
evidence the question changed, so the card never flickers or subtly
rewords itself mid-problem. Cono's reading effort goes into your new
handwriting, matched against the questions it already knows; a new
question is registered only when the work can't belong to any known one.
The **Next** button tells Cono you're moving on: it identifies the next
problem on the page, gives you a one-line orientation for it, and
**pins the card there** (marked ⦿) — later re-reads of the page can't
snap it back to the problem you left; the pin dissolves on its own once
your handwriting genuinely moves to another problem.

**Relations.** All the equations the current problem runs on (up to
four) — taken from your page when you've written them, otherwise the
standard relations the problem needs — typeset in chem shorthand (H₂O,
SO₄²⁻, →, ⇌) with a highlighted `?` in place of each quantity you
haven't found yet. The "what am I even solving" scaffold. The same
typesetting applies everywhere math appears — the problem card, Cono's
notes, the transcription — and anything it can't recognize passes
through as plain text rather than being dropped.

**On the page.** Cono's latest transcription of your handwriting, line
by line, right in the twin — your page, reborn as text it can talk
about.

**Readability map.** A page-shaped grid, updated with every snapshot:
green cells the model could read, red cells where something's there but
too blurry, small, or cut off to read, dark cells blank paper. This is
the framing indicator — a red band means reposition that part of the
page. The camera n/10 chip next to it links to the exact frame read.

Feeding the map: every snap gets a **writing-clarity pass** before the
model reads it, with three strengths you can switch mid-session from
the "writing clarity" button under the camera (or `--contrast MODE` at
start — handy when experimenting with different pens and pencils):

- **auto** (default) — a global histogram stretch: a near-no-op on a
  well-lit page, a real lift on faint pencil in dim classroom light.
- **strong** — goes after faint strokes specifically: uneven lighting is
  flattened first (a heavily blurred copy of the page is subtracted, so
  lamp falloff and page curvature cancel instead of being amplified),
  then the flattened image is contrast-stretched, mid-gray graphite is
  gamma-pushed toward black, and stroke edges get a mild sharpen —
  grayscale output, since color is noise when reading handwriting. In
  testing, a faint-pencil page the model mis-passed raw was caught
  correctly after the strong pass.
- **off** — snaps pass through untouched (`--no-contrast` still works).

Browser-mode snaps are processed on the canvas before upload; Desk View
and replay frames in place by the server when Pillow is installed
(`pip install pillow` — optional, everything works without it, snaps
just pass through unchanged). The stored snapshot, the thumbnail on
each note, and what the model read are always the same pixels, and each
check records which pass its snap got (`canvas-auto` / `canvas-strong` /
`pillow-auto` / `pillow-strong` / `skip` / `off`) so session scores can
compare clarity modes and writing implements across sessions.

**Dialogue.** Every note lands in a chat thread anchored to the current
problem, and you can type back — ask about the question, push back on a
note, or press **explain more**. And the twin itself is the pointing
surface: click a transcribed line, a relation, the problem card, or a
readability-map cell, then ask "what about this?" — the question is
anchored to that exact thing (the model gets the element's own text,
or, for map cells, the page region plus a full-resolution close-up).
Earlier problems keep their own threads; "earlier notes" below the map
holds every check with the exact snapshot and transcription behind it.

**The ladder.** Cono never refuses and never blurts. Unprompted checks
hint first: a guiding question that implies where the error is. Ask
explicitly (type it, press "explain more", or hit "Check now" on the
same mistake) and it gives one worked step; ask a second time and it
gives the full answer plainly, with an offered "want to explain it back
to me on paper?". Direct questions about what a problem means are just
answered — no gatekeeping.

## Latency

The old pipeline averaged 66 s per check in real classroom use. This one
streams: the model's words render as they're generated (first text
≈ 1 s after the snap), the note is complete in ~4–7 s, and the slower
structured parts of the reply (transcription, map, relations) ride along
in the same call, ordered after the text you're waiting on. Three
changes did it: images go to the `claude` CLI inline (no file-read round
trip), extended thinking is off — replaced by a one-line visible "tally"
(atom counts, unit chains, sig figs recomputed digit by digit) that the
feedback must agree with — and frames are downscaled to 960 px for
reading while originals stay on disk. Automatic snaps still never come
faster than one per 5 s.

And the cone: the little 3D cone in the header (Cono, cone) spins while
a check or chat reply is being read and rests when the desk is quiet —
a glanceable "is it thinking" mark, pure inline SVG + CSS.

**Watching where the time goes** (test feature): a small "check stages"
strip in the side column traces each in-flight check or chat reply
through the real stages of the pipeline — contrast, request sent, first
word from the model, then each section of the reply as it streams in
(visibility → working on → problem → page → tally → check → kind → grid
→ equations) — with a live elapsed clock. Every chip lights on a real
server event, never a timer animation, so during head-to-head sessions
you can see exactly which stage is eating the seconds. Hide or show it
with the "stage trace" button; the per-stage timestamps are logged into
every session record and `tools/score-session.py` prints a stage-timing
table from them.

## Every live run is recorded (testdev mode)

Cono is in full test-development mode: **every live run — Desk View or
browser — is recorded locally for development**, from launch until you
press "End & rate" or stop the server. There is no separate session
mode and no timer. While recording, a ● indicator with a running clock
stays visible in the header.

What gets saved, all into one local folder
(`~/deskcap/session-<timestamp>/`, with a `session.json` manifest and
an `events.jsonl` interaction log): a photo of your page every 3
seconds (thinned to every 10 seconds after the first 10 minutes, so a
two-hour class stays in the hundreds of MB — the server prints the
folder size every 10 minutes and at the end), every snapshot read,
every note written (each check rotates through four feedback styles so
sessions also measure what kind of help works), every chat message,
pen-point, Next press and suggestion, per-check latency, stage and
clarity metadata, and the page-change signal.

**"End & rate" is the data engine**: ending the session walks you
through rating each note (Helped / Didn't help / Wrong — skippable) and
two short questions, then offers one-click **Delete this session** (or
"Record again"). Quitting the server mid-session still writes a
complete, scoreable bundle. Nothing leaves this machine beyond the
snapshots Claude already reads through your own login — but if you
don't want a run recorded at all, start with **`--no-record`**.
Demo and replay runs never record.

Afterwards, `tools/score-session.py ~/deskcap/session-<ts>` turns the
ratings into per-style and per-config tables (latency, first-token and
stage-timing columns; unrated sessions still get the latency and stage
tables). `tools/experiment.py` replays a recording through a matrix of
snap frequencies, image preprocessing, and prompt structures and writes
a side-by-side `report.md`; needs Pillow (`pip install pillow`) and
costs real `claude` calls.

Handy: symlink it onto your PATH so it's one word from anywhere:
`ln -s "$PWD/cono-check/cono-check" /opt/homebrew/bin/cono-check`

## What gets sent where

The live video stream itself is never uploaded or shown to the AI —
frames are compared locally. In testdev mode, periodic photos of the
page ARE saved to the local session folder (see above; `--no-record`
opts out), and only when your page has changed and settled does one
snapshot go to the local server, which reads it through your own
`claude` login — never more than one every 5 seconds, and typically
just a few per problem. Every note in the
dialogue and the history shows exactly the frame that was read. When you
send a chat message in browser mode, one fresh snapshot is taken so the
answer matches what's on your desk right now; pen-pointed questions also
send a close-up crop of the spot you clicked.

Every check answers visibly: real feedback lands in the dialogue, and
"nothing new" or "fix the framing" results appear as a quiet one-liner
under it, so the twin never goes silent. Two checks can run at once — a
slow one never holds up the next.

Checks work across STEM subjects — math derivations, chemistry
(balancing, units, significant figures, subscripts read as written),
and biology worksheets — and they remember the page: feedback covers
only what's new since the last look, in at most two sentences of chem/
math shorthand, using the worksheet's own question labels. Snapshots are
kept on your machine in `~/deskcap/check-<timestamp>/`. Pause camera
stops the device entirely.

## How it works

The page downsizes each video frame to 160×120 and measures how much
changed since the last look, four times a second. Change above 20% means
you're writing; once it drops below 10% the page has settled, and the
frame — contrast-normalized unless you turned that off — goes to Claude
inline (base64, downscaled to 960 px) through
`claude -p --input-format stream-json --output-format stream-json
--include-partial-messages`. The reply streams back in fixed field
order — visibility, what you're working on, the problem card, a faithful
transcription that preserves your errors, a one-line tally re-running
any counting the judgment depends on, the hint-first check, the
readability grid, and the relations — and the server parses it
incrementally, pushing partial text and twin updates to the browser over
server-sent events (`/events`). The server (`cono-check`, one Python
file, stdlib only) stores snaps, runs the `claude` CLI, and serves the
page. The sample session in `sample/` was generated by
`tools/make-sample.py`.
