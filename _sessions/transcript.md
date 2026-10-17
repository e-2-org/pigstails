# Pig's Tails in HTML - session transcript

Transcript of the Pig's Tails part of a Claude Code session on 2026-10-13. Earlier in the same session, Tome, Word Perhect, Adelaide, A House Is Not A Home and Now Here / Nowhere were worked on; those parts are in their repositories' `_sessions` folders. Tool calls are shown as one-line notes; their output is omitted. Message times weren't recorded, so only the date is given. Claude's longer replies are shortened where they repeat what the summary records.

---

## User - 2026-10-13

One last one - repos/pigstails. I never actually knew how this worked, what the control buttons do or how it was put together. It looks simple, but it may be broken in ruffle? Again, a html port of this piece would be amazing - primarily using SVG I guess?

## Claude

> *Bash: Survey the pigstails repo*

> *Bash: Read the pages and compare the SWFs*

Here's how it worked, from the pages alone. A frameset put the map (`map.swf`) above a strip of controls (`controls.swf`). The controls never touch the picture directly: each button sends an `FSCommand` (`home`, `zoom`, `panx` or `pany`) to JavaScript in `controls.htm`, which reaches across into the other frame and calls the Flash plugin's own scripting methods on the map movie, `Zoom(percent)` and `Pan(x, y, 0)`. Ruffle doesn't support those old plugin methods, so the buttons would do nothing there. `pigstails.swf` is byte-for-byte the same as `map.swf`.

> *Bash: Dump both SWFs to XML and count tags*

> *Bash: Decode button and frame actions*

`controls.swf` decodes into seven buttons: home (`zoom 0`), zoom in (`zoom 50`), zoom out (`zoom 200`) and four pans of 50 pixels. In `map.swf`, three frame actions make up the timeline flow, and 51 buttons have no actions.

> *Bash: Inspect one map button definition*

> *Bash: Render sample map frames and the controls*

A blurry video still of a market stall full of red chillies is "un-picked": flat colour shapes are laid over it piece by piece, the photo then disappears to leave only the shapes on green, and the shapes are taken away one by one until the frame is empty. Then it loops. The controls are seven pale yellow dots, barely visible on the cream background.

> *Bash: List every placement in both movies*

Nothing in either movie moves or changes colour: everything is a static shape or button, placed at one frame and removed at another. The control dots, left to right, are pan left, pan up, zoom out, home, zoom in, pan down and pan right.

> *Bash: List every button's states*

While the photo shows, invisible buttons show a colour patch only under the pointer. Once patches are laid down, they're buttons with no "over" state, so hovering makes one vanish to show the photo, and pressing brings it back. A few states are offset from their hit areas.

> *Bash: Export shapes and the bitmap with FFDec*

> *Bash: Render the control button state shapes*

The control dots are a hidden interface: under the pointer each turns into a blue symbol (a boxed minus for home, a plus, a minus and four arrows).

> *Bash: Check Ruffle for legacy Zoom/Pan methods*

> *Bash: Search the Ruffle package for legacy methods*

> *Bash: Look at Ruffle's legacy API and FSCommand handling*

> *Bash: List Ruffle's public player methods*

Ruffle 0.7.1 provides `PercentLoaded()` but not `Zoom` or `Pan`. So in Ruffle the pictures and their rollovers can work, but the control dots can't.

> *Bash: Inspect shape SVG structure*

> *Bash: Check bitmap fills used by the patch shapes*

All 22 bitmap fills use the same photo: shapes 75–95 are pieces of it cut to the patches' outlines. I'll reference the original JPEG once.

> *Write: _scripts/build.py*

> *Bash: Run the Pig's Tails build*

> *Bash: Capture map frames and compare with FFDec*

> *Bash: Stack reference and port frames*

The photo is identical apart from JPEG decoding and resampling, which explains the steady 2–3% RMSE; the timeline frames match.

> *Bash: Test rollovers and the zoom and pan controls (the first run picked a button not on screen; fixed)*

> *Bash: Rerun the interaction test*

Everything works: hidden patches appear on hover, laid-down patches vanish on hover and come back when pressed, each dot shows its symbol, and zoom, pan and home change the view as Flash's `Zoom`/`Pan` would.

> *Bash: Remove old pages and update the README (killed by its own `pkill`, which matched its command line)*

> *Bash: Check what the killed command changed*

> *Bash: Remove old pages and update the README*

> *Write: _sessions/2026-10-13-summary.md*

> *Write: _sessions/2026-10-13-transcript.md*

Pig's Tails now runs as a single page, `index.html`, built from the original movies, and the session notes are in `pigstails/_sessions/`.
