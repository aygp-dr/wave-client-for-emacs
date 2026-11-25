// Print the CoreGraphics window numbers of the normal-layer windows owned by
// a process id (argv[0]), so screencapture -l can grab a window even when
// another app is in front of it.  Usage: osascript -l JavaScript window-id.js PID
ObjC.import('CoreGraphics');
function run(argv) {
  const pid = parseInt(argv[0], 10);
  const list = ObjC.castRefToObject($.CGWindowListCopyWindowInfo($.kCGWindowListOptionAll, 0));
  const ids = [];
  for (let i = 0; i < list.count; i++) {
    const w = list.objectAtIndex(i);
    if (w.objectForKey('kCGWindowOwnerPID').js === pid && w.objectForKey('kCGWindowLayer').js === 0)
      ids.push(w.objectForKey('kCGWindowNumber').js);
  }
  return ids.join(' ');
}
