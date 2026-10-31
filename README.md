# Cono

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

## Try it on your own work

Grab whatever you're working on — a problem set, a worksheet, a page of
notes — and a pen.

**What you need**

- A Mac with Python 3 (nothing to `pip install`).
- The [Claude Code CLI](https://claude.com/claude-code), installed and
  logged in — `claude` does the reading, so there's no API key setup.
  Checks run on your own Claude login and count against its usage; the
  default model is opus (`--model sonnet` is lighter).
- A camera that can see your page, one of:
  - **built-in Desk View** (M4-and-later Macs) — the intended setup;
  - **an iPhone as the Desk View camera** via Continuity Camera, on any
    Mac with macOS 13+ ([setup below](#camera-setup));
  - **any other camera** the browser can see, with `cono browser`.

  Desk View needs the Xcode command line tools (`xcode-select --install`)
  to build the small capture tool on first run.

**Three commands**

```bash
git clone https://github.com/jinyaodesandies/cono
cono/cono doctor     # ten-second preflight: claude, camera, Desk View — with a fix for anything missing
cono/cono            # start (or `cono/cono browser` without Desk View)
```

Your browser opens to Cono with the camera view at the side. Frame your
page (the "Re-frame Desk View" button helps), then just work. Each time
you pause writing, Cono reads the page and the twin fills in — the
problem you're on, the relations it runs on, a map of what it could
read — and a note lands in the dialogue when there's something to say:
where a mistake is and a question to get you moving, never the corrected
answer. Type back at it, or click any part of the twin to ask about
exactly that. "Check now" checks immediately; Ctrl-C in the terminal
stops it.

Good to know: Cono is in test-development mode, so every live run keeps
photos of your page and a log of its notes in `~/deskcap/` on your
machine — the snapshots it read and a run log always, plus a full
session recording unless you start with `--no-record` (see
[below](#every-live-run-is-recorded-testdev-mode)). Nothing leaves your
Mac except what's read through your own `claude` login: the snapshots,
close-up crops, and anything you type.

## Camera setup

The camera modes in detail:

```bash
cono/cono            # the Desk View camera — top-down on your page
cono/cono browser    # fallback: any camera the browser can see
```

> **Renamed:** the executable used to be `cono-check`. A deprecated
> compatibility shim with the old name still forwards to `cono` so
> existing scripts and PATH symlinks keep working, but it will be
> removed — switch to `cono`.

**Desk View is the default and the point**: the Mac's top-down desk
camera (built in on M4-and-later Macs) watches the page lying flat where
you naturally write — Cono looks at your desk, not at you.
Browsers can't open that camera, so this mode captures through `deskcap`,
a small Swift tool that builds itself from the bundled source on first
run (needs the Xcode command line tools: `xcode-select --install`), and
your terminal app needs camera permission — macOS asks once. If the build
fails, `cono doctor` prints the compiler's actual complaint and the
fix — usually a stale file left behind by an older Command Line Tools
install. The camera view sits at the side as a framing aid — the twin is
the main event — and the video is display-only and never leaves your
machine. An iPhone Desk View drops out whenever the phone is unlocked or
picked up; Cono says so over the camera view and picks up again by itself
once the phone is locked and back on the lid — no restart needed. A
Reconnect button on that notice relaunches the capture if you'd rather
not wait. "Re-frame Desk View" (under the camera) opens Apple's Desk View
window in its set-up mode — drag the trapezoid around your page and start
Desk View — and Cono resumes with the new crop; macOS owns that framing,
so this is also the way to reset it.

**Using an iPhone as the Desk View camera** (any Mac before M4):

1. Turn on Continuity Camera on the phone (Settings → General →
   AirPlay & Continuity), then lock it and set it on the lid, landscape,
   rear cameras facing you. The phone has to stay locked with the screen
   off — unlock it or pick it up and the feed stops.
2. If the Desk View window opens but shows only black, the phone is
   connected and the video itself is empty. Check that the rear lenses
   are not covered by the mount or a case (Desk View uses the ultra-wide
   lens), and that the phone is not in Low Power Mode or very low on
   battery — it stays listed as a camera but stops sending frames.
3. Still black: toggle Continuity Camera off, lock the phone, wait ten
   seconds, and toggle it back on. To confirm it is the phone and not
   Cono, pick the iPhone as the camera in FaceTime — if that is black
   too, restart both devices with Wi-Fi and Bluetooth on.

**Browser mode** (`cono browser`) is the fallback for Macs without
Desk View — it works with any camera the browser can see:
the built-in one (hold the page up facing the screen), a webcam, or an
iPhone near your Mac via Continuity Camera — pick one from the camera
menu under the video. If the picture keeps cropping to your face, turn
off Center Stage in Control Center → Video Effects.

Either way: when you pause writing, Cono snaps one frame, reads it, and
the twin updates. There's a "Check now" button when you don't want to
wait, and **Pause checking** when you want Cono to stop reading for a
while: the camera picture stays on, but no snapshot is sent until you
press **Resume checking** (Check now and typed questions still work —
they're explicit). If the camera sees no page at all — your lap, your
shirt, a sleeve on the lens — Cono says "No page in view" without
sending anything; that local check never fires on a real page.

Before taking it somewhere that matters (class, a tutoring session),
run `cono doctor` — a ten-second preflight that verifies the
`claude` CLI (and its streaming support), the capture tool, Desk View,
and camera permission, with a fix suggestion for anything that fails.

Other flags:

```bash
cono --model opus          # pick the model (default: opus)
cono --replay DIR          # replay any recorded session directory
cono --port 9000           # serve somewhere else (default: 8764)
cono --contrast strong     # writing clarity: off | auto (default) | strong
cono --no-contrast         # same as --contrast off
cono --no-record           # testdev opt-out: run live without recording
cono --dev                 # start in dev mode (show instrumentation)
cono --view ambient        # start in the ambient face (default: twin)
cono --no-open             # don't open the browser automatically
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
about. Readings are sticky: ink that hasn't changed keeps its earlier
transcription verbatim (the same discipline the question registry applies
to printed text), so a line you wrote ten minutes ago can't quietly
re-roll into a different reading on every check.

**Readability map.** A page-shaped grid, updated with every snapshot:
green cells the model could read, red cells where something's there but
too blurry, small, or cut off to read, dark cells blank paper. This is
the framing indicator — a red band means reposition that part of the
page. The camera n/10 chip next to it links to the exact frame read.
And when the same detail stays unreadable two checks in a row, the next
check automatically carries a full-resolution close-up of that region —
Cono zooms in itself instead of asking you to read your own page to it.

Feeding the map: every snap gets a **writing-clarity pass** before the
model reads it, with three strengths you can switch mid-session from
the "writing clarity" button (dev mode; `--contrast MODE` at start —
handy when experimenting with different pens and pencils):

- **auto** (default) — an adaptive gate, measured on the photo-pipeline
  harness: a well-lit page gets a global histogram stretch (a near-no-op
  on good light, a real lift on faint pencil), while a dim or flat frame
  (luminance spread below the gate threshold) gets **waterfill**
  illumination flattening — a published water-filling pass that rescues
  dim pencil without thinning the strokes of bright pages the way the
  strong pass does. The gate's decision is logged with every check.
- **strong** — the manual heavy option (dev mode): uneven lighting is
  flattened first (a heavily blurred copy of the page is subtracted, so
  lamp falloff and page curvature cancel instead of being amplified),
  then the flattened image is contrast-stretched, mid-gray graphite is
  gamma-pushed toward black, and stroke edges get a mild sharpen —
  grayscale output, since color is noise when reading handwriting.
- **off** — snaps pass through untouched (`--no-contrast` still works).

Every pass keeps continuous tones — nothing is ever binarized
(thresholding destroys faint graphite; a standing, measured constraint).
Browser-mode snaps are processed on the canvas before upload; Desk View
and replay frames in place by the server when Pillow is installed
(`pip install pillow` — optional, everything works without it, snaps
just pass through unchanged; `numpy`, also optional, enables the
waterfill pass server-side — without it the gate falls back to strong).
The stored snapshot, the thumbnail on each note, and what the model read
are always the same pixels, and each check records which pass its snap
got (`canvas-auto` / `canvas-waterfill` / `canvas-strong` /
`pillow-auto` / `pillow-waterfill` / `pillow-strong` / `skip` / `off`)
so session scores can compare clarity modes and writing implements
across sessions — and validate the gate itself on live data.

**Dialogue.** Every note lands in a chat thread anchored to the current
problem, and you can type back — ask about the question, push back on a
note, or press **explain more**. And the twin itself is the pointing
surface: click a transcribed line, a relation, the problem card, or a
readability-map cell, then ask "what about this?" — the question is
anchored to that exact thing (the model gets the element's own text,
or, for map cells, the page region plus a full-resolution close-up).
Pointing also offers the obvious ask as one tap — **Define & explain**
on a relation, **Check this line**, **What is it asking?**, **What's
written here?** — and two buttons under the box ask about the whole
sheet: **Trick questions?** (reads every printed question at full
resolution and flags the ones with a trap — an exception to the trend,
a reversed order, a units or sign trap — by label, without answers) and
**Review concepts** (a short review of the background the sheet relies
on). Earlier problems keep their own threads; "earlier notes" below the
map holds every check with the exact snapshot and transcription behind
it. Replies stream in place, each in its own bubble, so a check and a
chat answer arriving at once never overwrite each other's words.

**The ladder.** Cono never refuses and never blurts. Unprompted checks
hint first: a guiding question that implies where the error is. Ask
explicitly (type it, press "explain more", or hit "Check now" on the
same mistake) and it gives one worked step; ask a second time and it
gives the full answer plainly, with an offered "want to explain it back
to me on paper?" — after which checks stop hinting toward that answer
and only verify what you write against it. Direct questions about what
a problem means, a definition, or how something works are just answered,
answer first ("No — …", "It doesn't, because …") — no gatekeeping.

**It never argues with your page.** Two trust rules run server-side on
every note. Cono doesn't repeat itself: every piece of advice it gives is
registered, a reworded repeat makes the next check escalate to one worked
step (or drop the point if it can't re-verify it from the image), and a
third identical nudge is suppressed into a quiet line. And your reading
of your own page wins: if you tell Cono the sheet says something
different from what it read — or it keeps pushing advice you're visibly
not taking — the next reply re-reads the disputed spot from a
full-resolution copy, and if that still can't settle it, Cono concedes
and builds on your version instead of telling you to "re-read" your own
paper. Checks that would only announce "nothing new" never become note
cards (a quiet line at most), and a "nothing new" claim that contradicts
the camera's own change signal is suppressed outright and logged as a
misfire.

**Ambient view.** The Twin / Ambient toggle in the header flips the same
session into a second face: the camera becomes the hero, Cono's notes sit
in the margin next to it, and the analytical panels (relations, the
transcribed page) rest until you switch back. Same plumbing, same
recording, same readability map — only what leads changes. Your choice
sticks across launches; `--view ambient` starts there.

## Latency

The old pipeline averaged 66 s per check in real classroom use. This one
streams: the model's words render as they're generated (first text
≈ 1 s after the snap), the note is complete in ~4–7 s, and the slower
structured parts of the reply (transcription, map, relations) ride along
in the same call, ordered after the text you're waiting on. Three
changes did it: images go to the `claude` CLI inline (no file-read round
trip), extended thinking is off — replaced by a one-line visible "tally"
(atom counts, unit chains, sig figs recomputed digit by digit) that the
feedback must agree with — and frames are downscaled to 1280 px for
reading (wider is pointless: the API resamples anything past ~1.15 MP,
and 1280 fixed a live row-binding misread that 960 produced) while
originals stay on disk. Automatic snaps still never come faster than one
per 5 s, they wait for your hand to clear the page (never more than
15 s — a resting hand doesn't block checks), and a check that has
produced nothing for 20 seconds is killed and retried once — one slow
outlier never becomes a 39-second wait.

And the cone: the little 3D cone in the header (Cono, cone) spins while
a check or chat reply is being read and rests when the desk is quiet —
a glanceable "is it reading" mark, pure inline SVG + CSS.

## Logo

The header cone and "Cono" wordmark are also exported as standalone files
in `brand/`, for Canva, Figma, or anywhere outside the page:

| File | Use |
|---|---|
| `cono-logo-light-ink` | cone + wordmark, cream text, for dark backgrounds |
| `cono-logo-dark-ink` | cone + wordmark, near-black text, for light backgrounds |
| `cono-logo-on-desk` | exactly as in the header, on the desk brown |
| `cono-icon` | cone only, transparent |
| `cono-icon-square-desk` | cone on desk brown, square (profile pic, app icon) |
| `cono-logo-figma-board.svg` | every variant plus the palette on one board |

Each comes as SVG (sharp at any size, recolorable) and transparent PNG
(3000 px wide; icons 2048 px tall). The wordmark is outlined Avenir Next
Demi Bold, so it never falls back to another font. In Canva: Uploads →
Upload files. In Figma: drag the board in, or copy its SVG text and paste
— either gives editable vector layers named "Cono logo / light ink",
"Swatch / Lamp", and so on.

The palette is the page's own: desk `#1a1712`, paper `#f4efe4`, lamp
`#f2b32c`, cone body `#8a6f3c` / shade `#63502d` / base `#b58b43`, leaf
`#9ecb6b`, clay `#d9573c`.

`tools/make-logo.py` regenerates `brand/` from the header's geometry
(needs fontTools, shapely and Chrome). The cone is drawn at rest, with
the shade extended to the cone's right edge and the rim kept inside the
base: invisible at 17 px, but cleaner at poster size.

## Study mode and dev mode

The page opens in **study mode**: just the twin and its dialogue, with
automatic defaults (writing clarity on auto, map and cone doing their
jobs) — nothing to configure. The quiet **dev** switch under the camera
(or starting with `--dev`) reveals the test instrumentation together:
the check-stages trace, the writing-clarity cycler, per-check latency
and clarity tags in the history, the session bundle path on the ●
indicator, and **rating pills on every note and reply** (helped /
didn't help / wrong, wrong → misread page / advice wrong), saved the
moment you click — no need to end the session to rate. Modes only change
what is shown — recording and per-check metadata are always captured in
both.

**Suggest an improvement** (both modes): a small box under the history
takes one-line suggestions mid-use ("this hint was too wordy", "the map
lags"). Each entry is timestamped and captured with its context — the
active problem, the last check, the current frame and mode/clarity
config, and the run it came from — into the run log, the session
bundle when one is recording, and a cumulative local file,
`~/deskcap/suggestions.jsonl`, that survives individual sessions. The
box confirms each one with "✓ saved" (dev mode lists the files).

**Watching where the time goes** (test feature): a small "check stages"
strip in the side column traces each in-flight check or chat reply
through the real stages of the pipeline — contrast, request sent, first
word from the model, then each section of the reply as it streams in
(visibility → working on → problem → page → tally → check → kind → grid
→ equations) — with a live elapsed clock. Every chip lights on a real
server event, never a timer animation, so during head-to-head sessions
you can see exactly which stage is eating the seconds. It lives in dev
mode (with its own "stage trace" toggle there); the per-stage
timestamps are logged into every session record in both modes, and
`tools/score-session.py` prints a stage-timing table from them.

## Every live run is recorded (testdev mode)

Cono is in full test-development mode: **every live run — Desk View or
browser — is recorded locally for development**, from launch until you
press "End & rate" or stop the server. There is no separate session
mode and no timer. While recording, a ● indicator with a running clock
stays visible in the header; when not recording, the header says ○ not
recording and a **Start recording** button sits where End & rate was.

**The run log never stops.** Separately from the session bundle, every
run writes `~/deskcap/check-<timestamp>/run.jsonl` beside its frames:
every check (with the model's raw reply), chat message and reply,
rating, suggestion, pause and button press, in every mode, recording or
not. Ending a session early can no longer lose what happened after it.

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
through rating each note (pre-filled with anything you rated in place;
Helped / Didn't help / Wrong — skippable;
Wrong takes a one-tap sublabel, "misread the page" or "read it fine,
advice wrong", so misreads become labeled ground truth instead of
free-text notes) and
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
costs real `claude` calls. `tools/eval-no-page.py` re-measures the
no-page check against every labeled check in `~/deskcap`, and
`tools/selftest.py` runs the offline logic checks (no camera, no
`claude` calls).

**Working with shared recordings.** Collaborators get a curated set of
real sessions privately from Yao (it isn't in this repo: the photos show
a real desk). Ask for access, then download it into `~/deskcap` — the
same folder and layout Cono records into — and every tool above reads it
as if you'd recorded it yourself. The shared copy leaves out raw camera
frames, so `--replay` needs a full recording.

Handy: symlink it onto your PATH so it's one word from anywhere:
`ln -s "$PWD/cono/cono" /opt/homebrew/bin/cono`

## What gets sent where

The live video stream itself is never uploaded or shown to the AI —
frames are compared locally. In testdev mode, periodic photos of the
page ARE saved to the local session folder (see above; `--no-record`
opts out), and only when your page has changed and settled does one
snapshot go to the local server, which reads it through your own
`claude` login — never more than one every 5 seconds, and typically
just a few per problem (none while checking is paused, and none when no
page is in view). Every note in the
dialogue and the history shows exactly the frame that was read. When you
send a chat message in browser mode, one fresh snapshot is taken so the
answer matches what's on your desk right now; pen-pointed questions also
send a close-up crop of the spot you clicked, and the whole-sheet asks
(Trick questions? / Review concepts) send a full-resolution copy.

Every check answers visibly: real feedback lands in the dialogue, and
"nothing new" or "fix the framing" results appear as a quiet one-liner
under it, so the twin never goes silent. Two checks can run at once — a
slow one never holds up the next.

Checks work across STEM subjects — math derivations, chemistry
(balancing, units, significant figures, subscripts read as written),
and biology worksheets — and they remember the page: feedback covers
only what's new since the last look, in at most two sentences of chem/
math shorthand, using the worksheet's own question labels. Snapshots are
kept on your machine in `~/deskcap/check-<timestamp>/`, with the run
log beside them. When nothing new is on the page, the reply skips
re-deriving the relations ("EQUATIONS: same") — about a quarter less
output on the ~70% of checks that are "nothing new".

## How it works

The page downsizes each video frame to 160×120 and measures how much
changed since the last look, four times a second. Change above 20% means
you're writing; once it drops below 10% the page has settled, and the
frame — contrast-normalized unless you turned that off — goes to Claude
inline (base64, downscaled to 1280 px) through
`claude -p --input-format stream-json --output-format stream-json
--include-partial-messages`. The reply streams back in fixed field
order — visibility, what you're working on, the problem card, a faithful
transcription that preserves your errors, a one-line tally re-running
any counting the judgment depends on, the hint-first check, the
readability grid, and the relations — and the server parses it
incrementally, pushing partial text and twin updates to the browser over
server-sent events (`/events`). The server (`cono`, one Python
file, stdlib only) stores snaps, runs the `claude` CLI, and serves the
page.
