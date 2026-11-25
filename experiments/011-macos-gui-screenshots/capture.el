;;; capture.el --- Screenshot the real Wave client in a GUI frame (macOS) -*- lexical-binding: nil -*-
;; Usage: Emacs.app -Q -l /abs/path/experiments/011-macos-gui-screenshots/capture.el
;; Env: WAVE_SHOT_DIR (default docs/screenshots), WAVE_ID (default localhost!w+abc123)

(require 'cl)
;; Emacs.app starts in ~, not the shell's cwd: anchor on this file instead.
(defvar capture-root
  (expand-file-name "../.." (file-name-directory (or load-file-name buffer-file-name))))
(setq default-directory (file-name-as-directory capture-root))
(add-to-list 'load-path (expand-file-name "lisp" capture-root))
(require 'wave-client)
(require 'wave-client-websocket)
(require 'wave-list)
(require 'wave-display)
(require 'wave-ui)

(setq wave-client-connection-method 'websocket
      wave-client-ws-url "ws://localhost:9898/ws"
      wave-client-user "alice@localhost"
      wave-ui-server "http://localhost:9898"
      wave-client-domain "localhost"
      inhibit-startup-screen t
      ring-bell-function #'ignore)

(defvar capture-dir (expand-file-name (or (getenv "WAVE_SHOT_DIR") "docs/screenshots")))
(defvar capture-log nil)

(defun capture-step (what)
  "Append WHAT to capture-steps.log, so a hang shows where it stopped."
  (make-directory capture-dir t)
  (write-region (format "%s %s\n" (format-time-string "%T") what) nil
                (expand-file-name "capture-steps.log" capture-dir) t 'silent))

(defun capture-frame (name)
  "Write the selected frame to CAPTURE-DIR/NAME.png with screencapture."
  (message nil)
  (redisplay t)
  (sit-for 0.8)
  (redisplay t)
  (let* ((edges (frame-edges nil 'outer-edges))
         (region (format "%d,%d,%d,%d" (nth 0 edges) (nth 1 edges)
                         (- (nth 2 edges) (nth 0 edges))
                         (- (nth 3 edges) (nth 1 edges))))
         (file (expand-file-name (concat name ".png") capture-dir))
         (_ (capture-step (format "screencapture %s %s" name region)))
         (status (call-process "screencapture" nil nil nil "-x" "-o" "-R" region file)))
    (push (format "%s region=%s status=%s size=%s" name region status
                  (file-attribute-size (file-attributes file)))
          capture-log)))

(defun capture-open (title-fragment)
  "Open the row in *Wave* whose text contains TITLE-FRAGMENT."
  (switch-to-buffer "*Wave*")
  (wave-ui-refresh)
  (goto-char (point-min))
  (search-forward title-fragment)
  (wave-ui-open)
  (goto-char (point-min)))

(defun capture-run ()
  (make-directory capture-dir t)
  (tool-bar-mode -1)
  (set-frame-font "Menlo 14" nil t)
  (load-theme 'modus-operandi t)
  (set-frame-size nil 118 34)
  (set-frame-position nil 80 60)
  (raise-frame)
  (select-frame-set-input-focus (selected-frame))
  (capture-step "frame ready")
  (setq auth-sources nil)
  (delete-other-windows)
  (wave)
  (goto-char (point-min))
  (capture-step (format "inbox rendered: %d rows" (length wave-ui-rows)))
  (capture-frame "wave-inbox")
  (capture-open "Google I/O")
  (capture-frame "wave-detail")
  (capture-open "New to Wave")
  (capture-frame "wave-gadget")
  (wave-ui-playback)
  (delete-other-windows)
  (wave-ui-playback-next) (wave-ui-playback-next) (wave-ui-playback-next)
  (capture-frame "wave-playback")
  (switch-to-buffer "*Wave*")
  (wave-ui-contacts)
  (delete-other-windows)
  (capture-frame "wave-contacts")
  (with-temp-file (expand-file-name "capture.log" capture-dir)
    (insert (mapconcat #'identity (nreverse capture-log) "\n") "\n"))
  (kill-emacs 0))

(defun capture-run-safely ()
  (condition-case err
      (capture-run)
    (error
     (make-directory capture-dir t)
     (with-temp-file (expand-file-name "capture.log" capture-dir)
       (insert (mapconcat #'identity (nreverse capture-log) "\n")
               (format "\nERROR: %S\n" err)))
     (kill-emacs 1))))

;; Not emacs-startup-hook: it has already run by the time -l files load.
(run-with-timer 1.5 nil #'capture-run-safely)
