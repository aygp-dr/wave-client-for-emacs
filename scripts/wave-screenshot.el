;;; wave-screenshot.el --- Screenshot helper for Wave client demo -*- lexical-binding: t -*-

;;; Commentary:
;; This script loads the Wave client and displays the inbox for screenshots.

;;; Code:

(require 'url)
(require 'json)

;; Configuration
(defvar wave-server-url "http://localhost:9898")

(defun wave-fetch-inbox ()
  "Fetch inbox from Wave server and return as list."
  (with-current-buffer
      (url-retrieve-synchronously (concat wave-server-url "/api/inbox") t)
    (goto-char (point-min))
    (re-search-forward "^$" nil t)
    (let ((json-object-type 'plist)
          (json-array-type 'list))
      (json-read))))

(defun wave-demo-buffer ()
  "Create a demo buffer showing Wave inbox."
  (interactive)
  (let ((buf (get-buffer-create "*Wave Inbox*"))
        (inbox (wave-fetch-inbox)))
    (with-current-buffer buf
      (erase-buffer)
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
      (insert "                         📧 Wave Inbox                                         \n")
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
      (dolist (wave inbox)
        (let ((id (plist-get wave :id))
              (digest (plist-get wave :digest))
              (creator (plist-get wave :creator))
              (unread (plist-get wave :unread)))
          (insert (format "  %s %s\n"
                          (if (> unread 0) "●" "○")
                          digest))
          (insert (format "    └─ %s (%s)\n\n" creator id))))
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
      (insert (format "  Total: %d waves | Server: %s\n" (length inbox) wave-server-url))
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
      (goto-char (point-min)))
    (switch-to-buffer buf)
    buf))

(defun wave-demo-wave-detail ()
  "Create a demo buffer showing a single wave detail."
  (interactive)
  (let ((buf (get-buffer-create "*Wave Detail*")))
    (with-current-buffer buf
      (erase-buffer)
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
      (insert "  📝 Wave: Discussion: Wave protocol features                                  \n")
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n")
      (insert "  Participants: alice@localhost, bob@localhost, charlie@localhost\n")
      (insert "  Created: 2026-01-08 17:42:58\n")
      (insert "  Version: 7\n\n")
      (insert "  ┌────────────────────────────────────────────────────────────────────────────┐\n")
      (insert "  │ alice@localhost (Jan 8, 17:42):                                           │\n")
      (insert "  │   Let's discuss the Wave protocol implementation. Key areas:              │\n")
      (insert "  │   - WebSocket connection handling                                         │\n")
      (insert "  │   - Delta operations                                                      │\n")
      (insert "  │   - Operational transformation                                            │\n")
      (insert "  └────────────────────────────────────────────────────────────────────────────┘\n\n")
      (insert "  ┌────────────────────────────────────────────────────────────────────────────┐\n")
      (insert "  │ bob@localhost (Jan 8, 17:45):                                             │\n")
      (insert "  │   I've been looking at the original elisp source. The websocket module    │\n")
      (insert "  │   needs updating for Emacs 30 compatibility.                              │\n")
      (insert "  └────────────────────────────────────────────────────────────────────────────┘\n\n")
      (insert "  ┌────────────────────────────────────────────────────────────────────────────┐\n")
      (insert "  │ charlie@localhost (Jan 8, 17:48):                                         │\n")
      (insert "  │   Don't forget about the conflict resolution algorithms! The OT system   │\n")
      (insert "  │   is critical for real-time collaboration.                                │\n")
      (insert "  └────────────────────────────────────────────────────────────────────────────┘\n\n")
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
      (insert "  [r]eply  [e]dit  [a]dd participant  [q]uit\n")
      (insert "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
      (goto-char (point-min)))
    (switch-to-buffer buf)
    buf))

;; Run demo when loaded
(when noninteractive
  (message "Wave Screenshot Demo loaded"))

(provide 'wave-screenshot)
;;; wave-screenshot.el ends here
