;;; capture.el --- Screenshot the real Wave client in a GUI frame (macOS) -*- lexical-binding: nil -*-
;; Usage: Emacs.app -Q -l /abs/path/experiments/011-macos-gui-screenshots/capture.el
;; Env: WAVE_SHOT_DIR (default docs/screenshots), WAVE_SHOT_PORT (default 9898),
;;      WAVE_SHOT_USER (default alice), WAVE_SHOT_SCENE (tour, the default; inbox; or bus:
;;      the user's inbox and the "Agent bus" wave from scripts/agent-bus.py)

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

(defvar capture-port (or (getenv "WAVE_SHOT_PORT") "9898"))
(setq wave-client-connection-method 'websocket
      wave-client-ws-url (format "ws://localhost:%s/ws" capture-port)
      wave-client-user (concat (or (getenv "WAVE_SHOT_USER") "alice") "@localhost")
      wave-ui-user (or (getenv "WAVE_SHOT_USER") "alice")
      wave-ui-server (format "http://localhost:%s" capture-port)
      wave-client-domain "localhost"
      inhibit-startup-screen t
      ring-bell-function #'ignore)

(defvar capture-dir (expand-file-name (or (getenv "WAVE_SHOT_DIR") "docs/screenshots")))
(defvar capture-log nil)
(defvar capture-window-id nil "CoreGraphics number of this Emacs frame's window.")

(defun capture-find-window-id ()
  (let ((ids (split-string (shell-command-to-string
                            (format "osascript -l JavaScript %s %d"
                                    (shell-quote-argument
                                     (expand-file-name "experiments/011-macos-gui-screenshots/window-id.js" capture-root))
                                    (emacs-pid))))))
    (and ids (car (last ids)))))

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
  ;; Capture the Emacs window by its window number, never a screen region:
  ;; a region grabs whatever is on top, and once that was someone's terminal.
  (unless capture-window-id
    (error "No Emacs window number; refusing a region capture"))
  (let* ((region capture-window-id)
         (file (expand-file-name (concat name ".png") capture-dir))
         (_ (capture-step (format "screencapture %s window %s" name region)))
         (status (call-process "screencapture" nil nil nil "-x" "-o" "-l" region file)))
    (push (format "%s region=%s status=%s size=%s" name region status
                  (file-attribute-size (file-attributes file)))
          capture-log)))

(defun capture-open (title-fragment)
  "Open the row in *Wave* whose text contains TITLE-FRAGMENT.
The classic list opens waves in the window below, so go back to the
list's own window first."
  (select-window (or (get-buffer-window "*Wave*") (selected-window)))
  (switch-to-buffer "*Wave*")
  (wave-ui-refresh)
  (goto-char (point-min))
  (search-forward title-fragment)
  (hl-line-highlight)                   ; no command ran, so move the highlight by hand
  (wave-ui-open)
  (goto-char (point-min))
  (capture-step (format "opened %s; windows %S" title-fragment
                        (mapcar (lambda (w) (buffer-name (window-buffer w))) (window-list)))))

(defun capture-run ()
  (make-directory capture-dir t)
  (tool-bar-mode -1)
  (set-frame-font "Menlo 14" nil t)
  (load-theme 'modus-operandi t)
  (set-frame-size nil 118 34)
  (set-frame-position nil 80 60)
  (raise-frame)
  (select-frame-set-input-focus (selected-frame))
  (setq capture-window-id (capture-find-window-id))
  (capture-step (format "frame ready, window %s" capture-window-id))
  (setq auth-sources nil)
  (delete-other-windows)
  (wave)
  (goto-char (point-min))
  (capture-step (format "inbox rendered: %d rows" (length wave-ui-rows)))
  (when (equal (getenv "WAVE_SHOT_SCENE") "inbox")
    (capture-frame "inbox")
    (capture-finish))
  (when (equal (getenv "WAVE_SHOT_SCENE") "bus")
    (capture-bus)
    (capture-finish))
  (capture-frame "wave-inbox")
  (let ((wave-ui-list-style 'rich))
    (wave-ui-refresh)
    (capture-frame "wave-inbox-rich"))
  (wave-ui-refresh)
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
  (capture-finish))

(defun capture-finish ()
  (with-temp-file (expand-file-name "capture.log" capture-dir)
    (insert (mapconcat #'identity (nreverse capture-log) "\n") "\n"))
  (kill-emacs 0))

(defun capture-bus ()
  "Inbox of WAVE_SHOT_USER, then the Agent bus thread below it."
  (capture-frame "bus-inbox")
  (capture-open "Agent bus")
  (capture-frame "bus-thread"))

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
