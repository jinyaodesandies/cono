# Cono check

Point a camera at your handwritten work and get it checked as you go.
Cono shows live video of your page, waits until you pause writing, reads
what you actually wrote (your errors included), and leaves a note: where
the mistake is and a question to get you moving — never the corrected
answer.

This is the checking component of Cono, an AI study tutor that watches
paper while you work. It runs locally: your browser does the watching,
and a small Python server runs the reading through the `claude` CLI.

## Try it in one line

No camera needed — this replays a bundled sample session (a student
factoring a quadratic, with a mistake in it) through the full pipeline:

```bash
git clone https://github.com/jinyaodesandies/cono-check && cono-check/cono-check demo
```

Your browser opens to the session; within a minute the first check
appears in the margin, and it should point at the factoring error
without giving away the fix. There's a chemistry version too —
`cono-check demo chem` replays a stoichiometry page with a mis-balanced
equation and a significant-figures slip.

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
your terminal app needs camera permission — macOS asks once. If the build
fails, `cono-check doctor` prints the compiler's actual complaint and the
fix — usually a stale file left behind by an older Command Line Tools
install. The page
shows live video streamed from the tool, so framing the page is easy —
the video is display-only and never leaves your machine. An iPhone Desk
View drops out whenever the phone is unlocked or picked up; Cono says so
over the video and picks up again by itself once the phone is locked and
back on the lid — no restart needed. A Reconnect button on that notice
relaunches the capture if you'd rather not wait. "Re-frame Desk View"
opens Apple's Desk View window in its set-up mode — drag the trapezoid
around your page and start Desk View — and Cono resumes with the new
crop; macOS owns that framing, so this is also the way to reset it.

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

**Browser mode** (`cono-check browser`) is the fallback for Macs without
Desk View — it works with any camera the browser can see:
the built-in one (hold the page up facing the screen), a webcam, or an
iPhone near your Mac via Continuity Camera — pick one from the camera
menu under the video. If the picture keeps cropping to your face, turn
off Center Stage in Control Center → Video Effects.

Either way: when you pause writing, Cono snaps one frame and checks it.
There's a "Check now" button when you don't want to wait, and a "Pause
camera" button that turns the camera fully off — in Desk View mode it
stops the capture tool, and Continue starts it again.

Before taking it somewhere that matters (class, a tutoring session),
run `cono-check doctor` — a ten-second preflight that verifies the
`claude` CLI, the capture tool, Desk View, and camera permission, with
a fix suggestion for anything that fails.

Other flags:

```bash
cono-check --model opus          # pick the model (default: sonnet)
cono-check --replay DIR          # replay any recorded session directory
cono-check --port 9000           # serve somewhere else (default: 8763)
cono-check --no-open             # don't open the browser automatically
```

## Record a 10-minute session

```bash
cono-check session               # uses Desk View; `cono-check session live` for a browser camera
```

For developing the checking itself: a consented, contained recording of
one real work session. After you click "Start recording," Cono saves a
photo of your page every 3 seconds for 10 minutes — plus every snapshot
it reads, every note it writes (each check rotates through four feedback
styles so sessions also measure what kind of help works), the page-change
signal, and your button presses — into one local folder
(`~/deskcap/session-<timestamp>/`, with a `session.json` manifest). When
the clock runs out you rate each note (Helped / Didn't help / Wrong) and
answer two questions; one click deletes the whole folder if you want it
gone. Nothing records before the consent click, and nothing leaves the
machine beyond the normal snapshot path. The same flow starts from the
"Record a 10-minute session" button under the video in normal live mode.

When the session ends it prints a one-line config sweep command:
`tools/experiment.py` replays the recording through a matrix of snap
frequencies, image preprocessing (contrast/sharpen, downscale,
grayscale), and prompt structures (literal line-numbered transcription,
transcribe-then-reason), and writes a side-by-side `report.md` — every
config judged against the same ten minutes of real work. Needs Pillow
(`pip install pillow`); costs real `claude` calls.

Handy: symlink it onto your PATH so it's one word from anywhere:
`ln -s "$PWD/cono-check/cono-check" /opt/homebrew/bin/cono-check`

## What gets sent where

The live video is for your eyes only — it's never recorded, uploaded,
or shown to the AI. Frames are compared locally, and only when your page
has changed and settled does one snapshot go to the local server, which
reads it through your own `claude` login — never more than one every
5 seconds, and typically just a few per problem. Every check in the
margin shows a thumbnail of exactly the frame that was read.

Every check answers visibly: real feedback arrives as a note card, and
"nothing new" or "fix the framing" results appear as a quiet one-line
acknowledgement, so the margin never goes silent. Two checks can run at
once — a slow one never holds up the next.

Checks work across STEM subjects — math derivations, chemistry
(balancing, units, significant figures, subscripts read as written),
and biology worksheets — and they remember the page: feedback covers
only what's new since the last look, in at most two sentences, using
the worksheet's own question labels. Press "Check now" twice on the
same problem and the hint escalates: guiding question first, then a
worked step, then the answer with an offered explain-back. Snapshots are kept on your machine in
`~/deskcap/check-<timestamp>/`. Pause camera stops the device entirely.

## How it works

The page downsizes each video frame to 160×120 and measures how much
changed since the last look, four times a second. Change above 20% means
you're writing; once it drops below 10% the page has settled, and the
full-resolution frame goes to Claude, which replies in three parts —
what the camera can see (visibility n/10), a faithful transcription that
preserves your errors, and the hint-first check. The server
(`cono-check`, one Python file, stdlib only) stores snaps, runs the
`claude` CLI, and serves the page. The sample session in `sample/` was
generated by `tools/make-sample.py`.
