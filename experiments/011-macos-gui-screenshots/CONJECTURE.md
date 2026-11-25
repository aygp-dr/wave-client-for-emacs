# 011 — Screenshot the real client on macOS

## Conjecture

With 009 and 010 in place, the unmodified `wave-list` and `wave-display`
render in a GUI frame, and Emacs.app can screenshot its own frame with
`screencapture -R` from `frame-edges`, with no Xvfb/scrot.
The existing `docs/screenshots/wave-{inbox,detail}.png` are byte-identical
6 KB files rendered from `scripts/wave-screenshot.el`, which hardcodes the
wave detail text; they show nothing about the client.

## Refuted if

- the PNGs come out blank or show the desktop (Screen Recording denied);
- either buffer needs anything beyond the client's own commands.
