;;; wave-ui-acceptance.el --- Every UI feature, rendered by M-x wave -*- lexical-binding: t -*-

;; Each UI feature from wave_client_server.synthetic.UI_FEATURES has a
;; witness (user, folder, wave) found by scripts/gen-synthetic-waves.py
;; --witnesses.  For each, log in as that user, open that folder, find that
;; wave's row, check the row, open the wave and check the conversation.
;;
;; Run with: gmake elisp-ui-acceptance  (starts its own server on a synthetic DB)
;; Env: WAVE_WITNESSES (JSON path), WAVE_UI_SERVER (http://localhost:PORT)

;;; Code:

(require 'ert)
(require 'json)
(require 'cl-lib)
(setq auth-sources nil)
(require 'wave-ui)

(defvar wave-acceptance-server (or (getenv "WAVE_UI_SERVER") "http://localhost:9897"))
(defvar wave-acceptance-witnesses
  (let ((path (getenv "WAVE_WITNESSES")))
    (and path (with-temp-buffer
                (insert-file-contents path)
                (json-parse-buffer :object-type 'alist :array-type 'list)))))

(defun wave-acceptance--witness (feature)
  (or (alist-get (intern feature) wave-acceptance-witnesses)
      (ert-fail (format "no witness for %s" feature))))

(defun wave-acceptance--login (user)
  (setq wave-ui-server wave-acceptance-server
        wave-ui-user user
        wave-client-user user
        wave-client-domain "localhost"
        wave-client-ws-url (replace-regexp-in-string "^http" "ws" (concat wave-acceptance-server "/socket"))))

(defun wave-acceptance--row (feature)
  "Open the witness folder for FEATURE; return (WITNESS . ROW-TEXT)."
  (let ((witness (wave-acceptance--witness feature)))
    (wave-acceptance--login (alist-get 'user witness))
    (wave)
    (wave-ui-goto-folder (alist-get 'folder witness))
    (goto-char (point-min))
    (while (and (not (eobp))
                (not (equal (plist-get (get-text-property (point) 'wave-ui-row) :id)
                            (alist-get 'wave witness))))
      (forward-line 1))
    (should-not (eobp))
    (cons witness (buffer-substring-no-properties (line-beginning-position) (line-end-position)))))

(defun wave-acceptance--open (feature)
  "Render FEATURE's witness wave; return the display buffer text.
Uses `wave-display' rather than `wave-ui-open', which marks the wave read
and would change what later tests see."
  (let* ((row (progn (wave-acceptance--row feature) (get-text-property (point) 'wave-ui-row)))
         (buffer (wave-display (plist-get row :title) (plist-get row :id))))
    (with-current-buffer buffer
      (setq wave-ui-wave-id (plist-get row :id))
      (wave-display-refresh)
      (buffer-substring-no-properties (point-min) (point-max)))))

(defmacro wave-acceptance-deftest (name feature &rest body)
  (declare (indent 2))
  `(ert-deftest ,name ()
     ,(format "UI feature: %s" feature)
     (skip-unless wave-acceptance-witnesses)
     ,@body))

(wave-acceptance-deftest wave-ui-shows-unread-badge "unread wave"
  (let ((row (cdr (wave-acceptance--row "unread wave"))))
    (should (string-match-p "\\` *[1-9][0-9]* " row))
    ;; Opening marks it read: the badge goes on the next refresh.  Restore
    ;; afterwards so the witness stays unread for other runs.
    (wave-ui-open)
    (switch-to-buffer "*Wave*")
    (wave-ui-refresh)
    (let ((after (cdr (wave-acceptance--row "unread wave"))))
      (wave-ui-mark-unread)
      (should (string-prefix-p "    " after)))))

(wave-acceptance-deftest wave-ui-fully-read-has-no-badge "fully read wave"
  (should (string-prefix-p "    " (cdr (wave-acceptance--row "fully read wave")))))

(wave-acceptance-deftest wave-ui-marks-muted "muted wave"
  (should (string-match-p "\\[muted\\]" (cdr (wave-acceptance--row "muted wave")))))

(wave-acceptance-deftest wave-ui-archived-leaves-inbox "archived wave"
  (let ((witness (car (wave-acceptance--row "archived wave"))))
    (wave-ui-goto-folder "inbox")
    (should-not (cl-some (lambda (row) (equal (plist-get row :id) (alist-get 'wave witness))) wave-ui-rows))))

(wave-acceptance-deftest wave-ui-lists-custom-folder "custom folder"
  (let ((witness (car (wave-acceptance--row "custom folder"))))
    (should (string-match-p (regexp-quote (capitalize (alist-get 'folder witness)))
                            (format "%s" header-line-format)))))

(wave-acceptance-deftest wave-ui-shows-tags "tagged wave"
  (should (string-match-p "#[a-z]+" (cdr (wave-acceptance--row "tagged wave")))))

(wave-acceptance-deftest wave-ui-lists-spam "spam"
  (should (car (wave-acceptance--row "spam"))))

(wave-acceptance-deftest wave-ui-lists-trash "trash"
  (should (car (wave-acceptance--row "trash"))))

(wave-acceptance-deftest wave-ui-public-row-and-banner "public wave"
  (should (string-match-p "\\[public\\]" (cdr (wave-acceptance--row "public wave"))))
  (should (string-match-p "Everyone has access to this wave" (wave-acceptance--open "public wave"))))

(wave-acceptance-deftest wave-ui-renders-gadget "gadget, all columns voted"
  (let ((text (wave-acceptance--open "gadget, all columns voted")))
    (should (string-match-p "Yes ([1-9]" text))
    (should (string-match-p "No ([1-9]" text))
    (should (string-match-p "Maybe ([1-9]" text))))

(wave-acceptance-deftest wave-ui-indents-deep-threads "reply nested 2 deep"
  ;; replies to the root sit at level 0 beside it; two nested levels = 4 spaces
  (should (string-match-p "^    [^ \n]" (wave-acceptance--open "reply nested 2 deep"))))

(wave-acceptance-deftest wave-ui-single-blip "single-blip wave"
  (let ((wave-ui-list-style 'rich))
    (should (string-match-p "  1 msg " (cdr (wave-acceptance--row "single-blip wave"))))))

(wave-acceptance-deftest wave-ui-collapses-many-participants ">= 6 participants"
  (let ((wave-ui-list-style 'rich))
    (should (string-match-p "+[0-9]+" (cdr (wave-acceptance--row ">= 6 participants"))))))

;; The classic row is the 2010 *Wave List* (reference screenshot): count,
;; title bold while unread, creator's name in the right-hand column.
(wave-acceptance-deftest wave-ui-classic-row-shape "unread wave"
  (let ((wave-ui-list-style 'classic))
    (pcase-let* ((`(,witness . ,text) (wave-acceptance--row "unread wave"))
                 (row (get-text-property (point) 'wave-ui-row))
                 (creator (replace-regexp-in-string "@.*" "" (plist-get row :creator))))
      (ignore witness)
      (should (string-match-p (concat "\\`[1-9][0-9]* +.* " (regexp-quote creator) " *\\'") text))
      (should (eq (get-text-property (+ (line-beginning-position) 6) 'face) 'wave-ui-unread))
      (should (eq (get-text-property (- (line-end-position) 15) 'face) 'wave-ui-author)))))

(wave-acceptance-deftest wave-ui-classic-read-row-is-plain "fully read wave"
  (let ((wave-ui-list-style 'classic))
    (let ((text (cdr (wave-acceptance--row "fully read wave"))))
      (should (string-prefix-p "      " text))
      (should-not (eq (get-text-property (+ (line-beginning-position) 6) 'face) 'wave-ui-unread)))))

(wave-acceptance-deftest wave-ui-classic-opens-below-list "single-blip wave"
  (let ((wave-ui-list-style 'classic))
    (delete-other-windows)
    (wave-acceptance--row "single-blip wave")
    (let ((list-window (selected-window))
          (was-unread (> (plist-get (get-text-property (point) 'wave-ui-row) :unread_count) 0)))
      (wave-ui-open)
      (should (eq (window-in-direction 'above) list-window))
      (should (equal (buffer-name (window-buffer list-window)) "*Wave*"))
      ;; opening marked it read; restore its state for other tests
      (select-window list-window)
      (when was-unread (wave-ui-mark-unread))
      (delete-other-windows))))

(wave-acceptance-deftest wave-ui-truncates-long-title "title >= 60 chars"
  (should (string-match-p "…" (cdr (wave-acceptance--row "title >= 60 chars")))))

(wave-acceptance-deftest wave-ui-multi-line-blip "multi-line blip"
  (let ((text (wave-acceptance--open "multi-line blip")))
    (should (> (length (split-string text "\n" t)) 6))))

(ert-deftest wave-ui-acceptance-covers-every-feature ()
  "The witnesses file names every feature the generator promises."
  (skip-unless wave-acceptance-witnesses)
  (dolist (feature '("unread wave" "fully read wave" "muted wave" "archived wave" "custom folder"
                     "tagged wave" "spam" "trash" "public wave" "gadget, all columns voted"
                     "reply nested 2 deep" "single-blip wave" ">= 6 participants"
                     "title >= 60 chars" "multi-line blip"))
    (should (alist-get (intern feature) wave-acceptance-witnesses))))

(provide 'wave-ui-acceptance)
;;; wave-ui-acceptance.el ends here
