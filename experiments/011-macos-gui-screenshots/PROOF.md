# 011 — Result: held

`gmake screenshots` (dispatches to `screenshots-macos` on Darwin) writes
`docs/screenshots/wave-inbox.png` and `wave-detail.png` from the real client:
`(wave-list)` and `(wave-display …)` against the live server. Inspected:
three inbox rows with creators; conversation with header, participants,
and blips attributed to alice and charlie.

## Two silent hangs on the way (both: GUI waits forever, no error)

1. `-l experiments/…/capture.el` with a relative path: Emacs.app starts with
   `default-directory` = `~`, not the shell's cwd. The load fails, the frame
   sits idle. Fix: absolute `-l` path; the script anchors on `load-file-name`.
2. `(add-hook 'emacs-startup-hook …)` inside a `-l` file: the hook has
   already run by the time `-l` files load, so the callback never fires.
   Fix: `run-with-timer` at load time.

Diagnosed by an `--eval` wrapper that `condition-case`s the load and writes
the error to a file. A GUI Emacs failing at startup tells you nothing unless
you make it write somewhere.

Step log (`capture-steps.log`) is written per step so the next hang shows
where it stopped.
