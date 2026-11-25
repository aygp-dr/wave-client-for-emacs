;;; wave-ui.el --- Folders, search and actions for the Wave client -*- lexical-binding: t -*-

;; Licensed under the Apache License, Version 2.0.

;;; Commentary:
;; The 2009 Wave UI as an Emacs buffer (experiments/014):
;;
;;   M-x wave       folder list, unread badges, participants, title — snippet,
;;                  time and message counts; header line with folder tabs.
;;
;; List keys:  RET open   f folder   1-7 Inbox..Trash   s search   S save search
;;             r read  u unread  a archive  m mute  ! spam  D trash  U restore
;;             F move to folder   t tag  T untag   c new wave   C contacts
;;             g refresh   n/p move   q quit
;;
;; In an open wave (wave-display, rendered over the FedOne websocket):
;;             i reply to blip at point   r reply to wave   + add participant
;;             V vote on gadget   v playback   t tag   a archive   m mute
;;             u mark unread
;;
;; Conversations still come over the FedOne websocket (009/010); per-user
;; state comes from the server's REST API (user_api.py) with HTTP Basic auth.
;; Live updates arrive over the websocket, so replies from others re-render
;; the open wave.

;;; Code:

(require 'cl-lib)
(require 'subr-x)
(require 'url)
(require 'url-http)
(require 'json)
(require 'auth-source)
(require 'wave-client)
(require 'wave-client-websocket)
(require 'wave-display)
(require 'ewoc)

(defvar url-http-response-status)
(defvar url-http-end-of-headers)

(defgroup wave-ui nil "Folders, search and actions for Wave." :group 'applications)

(defcustom wave-ui-server "http://localhost:9898"
  "Base URL of the Wave server's REST API."
  :type 'string)

(defcustom wave-ui-user nil
  "User address or local part; nil means `wave-client-user'."
  :type '(choice (const nil) string))

(defcustom wave-ui-password nil
  "Password; nil means the local part of the user name (the mock
server's convention), or auth-source when `wave-ui-use-auth-source'."
  :type '(choice (const nil) string))

(defcustom wave-ui-use-auth-source nil
  "Look the password up in auth-source.  Off by default: the mock server
needs no secret, and a lookup can decrypt (and prompt for) a gpg store."
  :type 'boolean)

(defcustom wave-ui-saved-searches '(("Help" . "tag:help") ("Unread" . "is:unread"))
  "Saved searches offered by `wave-ui-folder' as (NAME . QUERY)."
  :type '(alist :key-type string :value-type string))

(defconst wave-ui-folders '("inbox" "active" "all" "by-me" "history" "spam" "trash"))

(defface wave-ui-unread '((t :inherit bold)) "Unread row title.")
(defface wave-ui-badge '((t :inherit success :weight bold)) "Unread count.")
(defface wave-ui-snippet '((t :inherit shadow)) "Snippet after the title.")
(defface wave-ui-meta '((t :inherit shadow)) "Time and message count.")
(defface wave-ui-tab '((t :inherit header-line)) "Folder tab.")
(defface wave-ui-tab-current '((t :inherit (bold header-line) :underline t)) "Current folder tab.")
(defface wave-ui-banner '((t :inherit warning)) "Access banner in an open wave.")
(defface wave-ui-yes '((t :inherit success :weight bold)) "Gadget Yes column.")
(defface wave-ui-no '((t :inherit error :weight bold)) "Gadget No column.")
(defface wave-ui-maybe '((t :inherit warning :weight bold)) "Gadget Maybe column.")

(defvar-local wave-ui-folder "inbox")
(defvar-local wave-ui-query "")
(defvar-local wave-ui-rows nil)
(defvar-local wave-ui-folder-counts nil)
(defvar-local wave-ui-wave-id nil "Wave id of an open wave buffer.")

;;;; REST

(defun wave-ui--user ()
  (let ((user (or wave-ui-user wave-client-user)))
    (if (string-match-p "@" user) user (concat user "@" (wave-client-domain)))))

(defun wave-ui--password ()
  (or wave-ui-password
      (when wave-ui-use-auth-source
        (let* ((host (url-host (url-generic-parse-url wave-ui-server)))
             (found (car (auth-source-search :host host :user (wave-ui--user) :max 1)))
             (secret (plist-get found :secret)))
          (if (functionp secret) (funcall secret) secret)))
      (car (split-string (wave-ui--user) "@"))))

(defun wave-ui--encode-path (wave-id &rest more)
  (mapconcat #'identity (cons (url-hexify-string wave-id) more) "/"))

(defun wave-ui-request (method path &optional params body)
  "Send METHOD to PATH with query PARAMS and JSON BODY; return parsed JSON."
  (let* ((url-request-method method)
         (url-show-status nil)
         (credentials (base64-encode-string (concat (wave-ui--user) ":" (wave-ui--password)) t))
         (url-request-extra-headers
          `(("Authorization" . ,(concat "Basic " credentials))
            ,@(when body '(("Content-Type" . "application/json")))))
         (url-request-data (when body (encode-coding-string (json-encode body) 'utf-8)))
         (url (concat wave-ui-server path
                      (when params (concat "?" (url-build-query-string params)))))
         (buffer (url-retrieve-synchronously url t t 15)))
    (unless buffer (error "Wave server did not answer: %s" url))
    (with-current-buffer buffer
      (unwind-protect
          (let ((status url-http-response-status))
            (goto-char url-http-end-of-headers)
            (if (and status (< status 300))
                (json-parse-buffer :object-type 'plist :array-type 'list
                                   :null-object nil :false-object nil)
              (error "Wave server: %s %s -> %s %s" method path status
                     (string-trim (buffer-substring (point) (point-max))))))
        (kill-buffer buffer)))))

(defun wave-ui--wave-action (wave-id action &optional body)
  (wave-ui-request "POST" (concat "/api/waves/" (wave-ui--encode-path wave-id action)) nil body))

;;;; Avatars

(defvar wave-ui--avatar-cache (make-hash-table :test 'equal))

(defun wave-ui--avatar (path)
  "Image for avatar PATH (/avatars/...), cached; nil without image support."
  (when (and (display-images-p) (image-type-available-p 'svg))
    (or (gethash path wave-ui--avatar-cache)
        (puthash path
                 (condition-case nil
                     (let ((buffer (url-retrieve-synchronously (concat wave-ui-server path) t t 5)))
                       (with-current-buffer buffer
                         (prog1 (progn (goto-char url-http-end-of-headers)
                                       (create-image (buffer-substring-no-properties (point) (point-max))
                                                     'svg t :height (frame-char-height) :ascent 'center))
                           (kill-buffer buffer))))
                   (error nil))
                 wave-ui--avatar-cache))))

(defun wave-ui--participants (participants width)
  "Avatars (or names) for PARTICIPANTS, padded to WIDTH columns.
The +N overflow count is always kept; names are truncated instead."
  (let* ((shown (seq-take participants 3))
         (extra (- (length participants) (length shown)))
         (suffix (if (> extra 0) (format " +%d" extra) ""))
         (images (and (display-images-p) (mapcar (lambda (p) (wave-ui--avatar (plist-get p :avatar))) shown))))
    (if (and images (cl-every #'identity images))
        (concat (mapconcat (lambda (image) (propertize "  " 'display image)) images " ")
                suffix
                (make-string (max 0 (- width (* 3 (length shown)) (length suffix))) ?\s))
      (concat (truncate-string-to-width (mapconcat (lambda (p) (plist-get p :name)) shown ",")
                                        (- width (length suffix)) nil nil "…")
              suffix
              (make-string (max 0 (- width (string-width (truncate-string-to-width
                                                          (mapconcat (lambda (p) (plist-get p :name)) shown ",")
                                                          (- width (length suffix)) nil nil "…"))
                                     (length suffix)))
                           ?\s)))))

;;;; Time

(defun wave-ui--time (iso)
  "Short time for ISO (naive UTC from the server): HH:MM today, else Mon DD."
  (if (not iso) ""
    (let* ((time (date-to-time (concat (substring iso 0 (min 19 (length iso))) "Z")))
           (today (format-time-string "%F")))
      (if (equal (format-time-string "%F" time) today)
          (format-time-string "%H:%M" time)
        (format-time-string "%b %d" time)))))

;;;; List buffer

(defvar wave-ui-list-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map (kbd "RET") #'wave-ui-open)
    (define-key map "n" #'next-line)
    (define-key map "p" #'previous-line)
    (define-key map "g" #'wave-ui-refresh)
    (define-key map "f" #'wave-ui-folder)
    (cl-loop for folder in wave-ui-folders
             for key from 1
             do (define-key map (number-to-string key)
                            (let ((name folder)) (lambda () (interactive) (wave-ui-goto-folder name)))))
    (define-key map "s" #'wave-ui-search)
    (define-key map "S" #'wave-ui-save-search)
    (define-key map "r" #'wave-ui-mark-read)
    (define-key map "u" #'wave-ui-mark-unread)
    (define-key map "a" #'wave-ui-archive)
    (define-key map "m" #'wave-ui-mute)
    (define-key map "!" #'wave-ui-spam)
    (define-key map "D" #'wave-ui-trash)
    (define-key map "U" #'wave-ui-restore)
    (define-key map "F" #'wave-ui-move-to-folder)
    (define-key map "t" #'wave-ui-tag)
    (define-key map "T" #'wave-ui-untag)
    (define-key map "c" #'wave-ui-compose)
    (define-key map "C" #'wave-ui-contacts)
    (define-key map "q" #'quit-window)
    map))

(define-derived-mode wave-ui-list-mode special-mode "Wave"
  "Wave folders and search.  \\{wave-ui-list-mode-map}"
  (setq truncate-lines t)
  (setq-local revert-buffer-function (lambda (&rest _) (wave-ui-refresh)))
  (hl-line-mode 1))

;;;###autoload
(defun wave ()
  "Open the Wave inbox."
  (interactive)
  ;; The 2010 default is the browser-channel backend, which logs in to
  ;; google.com; this UI only works over the FedOne websocket.
  (setq wave-client-connection-method 'websocket)
  (unless (and wave-client-ws-websocket (websocket-openp wave-client-ws-websocket))
    (wave-client-ws-connect wave-client-ws-url))
  (pop-to-buffer-same-window (get-buffer-create "*Wave*"))
  (unless (derived-mode-p 'wave-ui-list-mode) (wave-ui-list-mode))
  (wave-ui-refresh))

(defun wave-ui--folder-label (name)
  (pcase name ("by-me" "By me") (_ (capitalize name))))

(defun wave-ui--header-line ()
  (concat
   " "
   (mapconcat
    (lambda (counts)
      (let* ((name (plist-get counts :name))
             (unread (plist-get counts :unread))
             (label (concat (wave-ui--folder-label name) (if (> unread 0) (format " (%d)" unread) ""))))
        (propertize label 'face (if (equal name wave-ui-folder) 'wave-ui-tab-current 'wave-ui-tab))))
    wave-ui-folder-counts "  ")
   (if (string-empty-p wave-ui-query) "" (format "   search: %s" wave-ui-query))
   (format "   [%s]" (wave-ui--user))))

(defun wave-ui-refresh ()
  "Reload folder counts and the current folder or search."
  (interactive)
  (setq wave-ui-folder-counts (wave-ui-request "GET" "/api/folders")
        wave-ui-rows (wave-ui-request "GET" "/api/waves"
                                      `(("folder" ,wave-ui-folder)
                                        ,@(unless (string-empty-p wave-ui-query) `(("q" ,wave-ui-query))))))
  (setq header-line-format (wave-ui--header-line))
  (let ((inhibit-read-only t)
        (line (line-number-at-pos)))
    (erase-buffer)
    (if (null wave-ui-rows)
        (insert (propertize (format "\n  No waves in %s%s.\n" (wave-ui--folder-label wave-ui-folder)
                                    (if (string-empty-p wave-ui-query) "" (format " matching %S" wave-ui-query)))
                            'face 'wave-ui-snippet))
      (dolist (row wave-ui-rows) (wave-ui--insert-row row)))
    (goto-char (point-min))
    (forward-line (1- (min line (max 1 (length wave-ui-rows)))))))

(defun wave-ui--insert-row (row)
  (let* ((unread (plist-get row :unread_count))
         (width (max 60 (1- (window-width))))
         (badge (if (> unread 0) (propertize (format "%3d " unread) 'face 'wave-ui-badge) "    "))
         (who (wave-ui--participants (plist-get row :participants) 14))
         (meta (format " %6s %3d msg%s" (wave-ui--time (plist-get row :last_modified))
                       (plist-get row :blip_count) (if (= 1 (plist-get row :blip_count)) " " "s")))
         ;; Flags go before the title so a long title cannot truncate them away.
         (flags (concat (if (plist-get row :muted) "[muted] " "")
                        (if (plist-get row :public) "[public] " "")
                        (mapconcat (lambda (tag) (concat "#" tag " ")) (plist-get row :tags) "")))
         (title-width (- width 4 14 1 (string-width meta)))
         (title (propertize (plist-get row :title) 'face (if (> unread 0) 'wave-ui-unread 'default)))
         (text (truncate-string-to-width
                (concat (propertize flags 'face 'wave-ui-meta) title
                        (propertize (concat " — " (plist-get row :snippet)) 'face 'wave-ui-snippet))
                title-width nil ?\s "…"))
         (start (point)))
    (insert badge who " " text (propertize meta 'face 'wave-ui-meta) "\n")
    (put-text-property start (point) 'wave-ui-row row)))

(defun wave-ui--row-at-point ()
  (or (get-text-property (point) 'wave-ui-row)
      (user-error "No wave on this line")))

(defun wave-ui-goto-folder (name)
  (setq wave-ui-folder name wave-ui-query "")
  (wave-ui-refresh))

(defun wave-ui-folder ()
  "Choose a folder or saved search."
  (interactive)
  (let* ((choices (append (mapcar (lambda (c)
                                    (cons (format "%-10s %d" (wave-ui--folder-label (plist-get c :name))
                                                  (plist-get c :total))
                                          (cons 'folder (plist-get c :name))))
                                  wave-ui-folder-counts)
                          (mapcar (lambda (s) (cons (format "Search: %s" (car s)) (cons 'search (cdr s))))
                                  wave-ui-saved-searches)))
         (choice (cdr (assoc (completing-read "Folder: " choices nil t) choices))))
    (if (eq (car choice) 'folder)
        (wave-ui-goto-folder (cdr choice))
      (setq wave-ui-folder "all" wave-ui-query (cdr choice))
      (wave-ui-refresh))))

(defun wave-ui-search (query)
  "Search all waves.  Operators: is:unread is:read is:muted is:public
with:NAME by:NAME tag:TAG; other words match title and text."
  (interactive (list (read-string "Search waves: " wave-ui-query)))
  (setq wave-ui-folder "all" wave-ui-query query)
  (wave-ui-refresh))

(defun wave-ui-save-search (name)
  "Save the current search as NAME for this session (customize to keep)."
  (interactive (list (read-string (format "Save search %S as: " wave-ui-query))))
  (when (string-empty-p wave-ui-query) (user-error "No search to save"))
  (add-to-list 'wave-ui-saved-searches (cons name wave-ui-query) t)
  (message "Saved; M-x customize-variable wave-ui-saved-searches to keep it"))

(defmacro wave-ui--define-action (name action doc)
  `(defun ,name ()
     ,doc
     (interactive)
     (wave-ui--wave-action (plist-get (wave-ui--row-at-point) :id) ,action)
     (wave-ui-refresh)))

(wave-ui--define-action wave-ui-mark-read "read" "Mark the wave read.")
(wave-ui--define-action wave-ui-mark-unread "unread" "Mark the wave unread.")
(wave-ui--define-action wave-ui-archive "archive" "Archive the wave (out of the inbox).")
(wave-ui--define-action wave-ui-mute "mute" "Mute and archive the wave.")
(wave-ui--define-action wave-ui-spam "spam" "Report the wave as spam.")
(wave-ui--define-action wave-ui-trash "trash" "Move the wave to the trash.")
(wave-ui--define-action wave-ui-restore "restore" "Back to the inbox: un-trash, un-spam, un-archive.")

(defun wave-ui-move-to-folder (name)
  "Move the wave to folder NAME (empty returns it to the inbox)."
  (interactive (list (completing-read "Folder (empty = inbox): "
                                      (cl-remove-if (lambda (f) (member f wave-ui-folders))
                                                    (mapcar (lambda (c) (plist-get c :name)) wave-ui-folder-counts)))))
  (wave-ui--wave-action (plist-get (wave-ui--row-at-point) :id) "folder"
                        `(:name ,(if (string-empty-p name) nil name)))
  (wave-ui-refresh))

(defun wave-ui--tags (wave-id add remove)
  (wave-ui--wave-action wave-id "tags" `(:add ,(vconcat add) :remove ,(vconcat remove))))

(defun wave-ui-tag (tag)
  "Add TAG to the wave at point."
  (interactive (list (read-string "Tag: ")))
  (wave-ui--tags (plist-get (wave-ui--row-at-point) :id) (list tag) nil)
  (wave-ui-refresh))

(defun wave-ui-untag (tag)
  "Remove TAG from the wave at point."
  (interactive (list (completing-read "Remove tag: " (plist-get (wave-ui--row-at-point) :tags) nil t)))
  (wave-ui--tags (plist-get (wave-ui--row-at-point) :id) nil (list tag))
  (wave-ui-refresh))

(defun wave-ui-open ()
  "Open the wave at point and mark it read."
  (interactive)
  (let* ((row (wave-ui--row-at-point))
         (wave-id (plist-get row :id)))
    (wave-ui--wave-action wave-id "read")
    (let ((buffer (wave-display (plist-get row :title) wave-id)))
      ;; wave-display already rendered (and decorated, via the hook).
      (with-current-buffer buffer (setq wave-ui-wave-id wave-id))
      (switch-to-buffer buffer))))

;;;; Compose and contacts

(defun wave-ui--contacts () (wave-ui-request "GET" "/api/contacts"))

(defun wave-ui-compose (title participants text)
  "Start a wave called TITLE with PARTICIPANTS and first blip TEXT."
  (interactive
   (list (read-string "Title: ")
         (completing-read-multiple "Participants (comma separated): "
                                   (mapcar (lambda (c) (plist-get c :name)) (wave-ui--contacts)))
         (read-string "Text: ")))
  (let ((created (wave-ui-request "POST" "/api/waves" nil
                                  `(:title ,title :text ,text :participants ,(vconcat participants)))))
    (when (derived-mode-p 'wave-ui-list-mode) (wave-ui-refresh))
    (message "Created %s" (plist-get created :id))
    created))

(defvar wave-ui-contacts-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map (kbd "RET") #'wave-ui-contacts-compose)
    (define-key map "g" #'wave-ui-contacts)
    (define-key map "q" #'quit-window)
    map))

(define-derived-mode wave-ui-contacts-mode special-mode "Wave Contacts"
  "Contacts; RET starts a wave with the contact at point.")

(defun wave-ui-contacts ()
  "Show contacts with online state."
  (interactive)
  (let ((contacts (wave-ui--contacts)))
    (pop-to-buffer (get-buffer-create "*Wave Contacts*"))
    (wave-ui-contacts-mode)
    (let ((inhibit-read-only t))
      (erase-buffer)
      (insert (propertize (format " Contacts of %s\n\n" (wave-ui--user)) 'face 'bold))
      (dolist (contact contacts)
        (let ((start (point))
              (image (wave-ui--avatar (plist-get contact :avatar))))
          (insert (if (plist-get contact :online) (propertize " ● " 'face 'success) " ○ ")
                  (if image (propertize "  " 'display image) "")
                  " " (plist-get contact :name) "\n")
          (put-text-property start (point) 'wave-ui-contact contact)))
      (goto-char (point-min))
      (forward-line 2))))

(defun wave-ui-contacts-compose ()
  (interactive)
  (let ((contact (or (get-text-property (point) 'wave-ui-contact) (user-error "No contact here"))))
    (wave-ui-compose (read-string "Title: ") (list (plist-get contact :name)) (read-string "Text: "))))

;;;; Open wave: decorations, replies, votes, playback

(defvar wave-ui-display-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map "i" #'wave-ui-reply-to-blip)
    (define-key map "r" #'wave-ui-reply-to-wave)
    (define-key map "+" #'wave-ui-add-participant)
    (define-key map "V" #'wave-ui-vote)
    (define-key map "v" #'wave-ui-playback)
    (define-key map "t" #'wave-ui-display-tag)
    (define-key map "a" #'wave-ui-display-archive)
    (define-key map "m" #'wave-ui-display-mute)
    (define-key map "u" #'wave-ui-display-unread)
    map))

(define-minor-mode wave-ui-display-mode
  "Wave UI keys in an open wave."
  :lighter " WaveUI" :keymap wave-ui-display-mode-map)

(defun wave-ui--display-wave-id ()
  (or wave-ui-wave-id (bound-and-true-p wave-display-wave-id) (user-error "Not in a wave")))

(defun wave-ui--decorate ()
  "Banner, tags and key help above the conversation (after each render)."
  (when (and (derived-mode-p 'wave-display-mode) (wave-ui--display-wave-id))
    (wave-ui-display-mode 1)
    (let* ((view (ignore-errors (wave-ui-request "GET" (concat "/api/waves/" (wave-ui--encode-path (wave-ui--display-wave-id) "view")))))
           (inhibit-read-only t))
      (when view
        (save-excursion
          (goto-char (point-min))
          (insert (propertize (plist-get view :title) 'face '(bold :height 1.2)) "\n")
          (when (plist-get view :public)
            (insert (propertize "Everyone has access to this wave" 'face 'wave-ui-banner) "\n"))
          (let ((images (delq nil (mapcar (lambda (p) (wave-ui--avatar (plist-get p :avatar)))
                                          (plist-get view :participants)))))
            (when images
              (insert (mapconcat (lambda (image) (propertize "  " 'display image)) images " ") "\n")))
          (when (plist-get view :tags)
            (insert "Tags: " (mapconcat #'identity (plist-get view :tags) ", ") "\n"))
          (insert (propertize "i reply here  r reply to wave  + participant  V vote  v playback  t tag  a archive  m mute  q back"
                              'face 'wave-ui-snippet)
                  "\n\n"))))))

(add-hook 'wave-display-after-render-hook #'wave-ui--decorate)

(defun wave-ui--blip-id-at-point ()
  (let* ((node (and (bound-and-true-p wave-display-ewoc) (ewoc-locate wave-display-ewoc)))
         (data (and node (ewoc-data node))))
    (if (and data (wave-display-blip-p data))
        (format "%s" (wave-display-blip-blip-id data))
      "b+root")))

(defun wave-ui--reply (parent text)
  (wave-ui--wave-action (wave-ui--display-wave-id) "blips" `(:text ,text :parent ,parent))
  ;; The server pushes the new conversation over the websocket; give it a moment.
  (accept-process-output nil 0.5)
  (wave-display-refresh))

(defun wave-ui-reply-to-blip (text)
  "Reply to the blip at point with TEXT."
  (interactive (list (read-string (format "Reply to %s: " (wave-ui--blip-id-at-point)))))
  (wave-ui--reply (wave-ui--blip-id-at-point) text))

(defun wave-ui-reply-to-wave (text)
  "Reply to the wave (a new top-level blip) with TEXT."
  (interactive (list (read-string "Reply to wave: ")))
  (wave-ui--reply "b+root" text))

(defun wave-ui-add-participant (address)
  "Add ADDRESS to the open wave."
  (interactive (list (completing-read "Add participant: " (mapcar (lambda (c) (plist-get c :name)) (wave-ui--contacts)))))
  (wave-ui--wave-action (wave-ui--display-wave-id) "participants" `(:address ,address))
  (accept-process-output nil 0.5)
  (wave-display-refresh))

(defun wave-ui--display-action (action)
  (wave-ui--wave-action (wave-ui--display-wave-id) action)
  (message "Wave %s" (pcase action ("archive" "archived") ("mute" "muted") ("unread" "marked unread") (_ action))))

(defun wave-ui-display-archive () (interactive) (wave-ui--display-action "archive"))
(defun wave-ui-display-mute () (interactive) (wave-ui--display-action "mute"))
(defun wave-ui-display-unread () (interactive) (wave-ui--display-action "unread"))

(defun wave-ui-display-tag (tag)
  (interactive (list (read-string "Tag: ")))
  (wave-ui--tags (wave-ui--display-wave-id) (list tag) nil)
  (wave-display-refresh))

(defun wave-ui-vote (choice)
  "Vote CHOICE (yes, no or maybe) on the wave's gadget."
  (interactive
   (list (pcase (read-char-choice "Vote [y]es [n]o [m]aybe: " '(?y ?n ?m))
           (?y "yes") (?n "no") (?m "maybe"))))
  (let* ((view (wave-ui-request "GET" (concat "/api/waves/" (wave-ui--encode-path (wave-ui--display-wave-id) "view"))))
         (gadgets (let (found)
                    (cl-labels ((walk (blips) (dolist (b blips)
                                                (setq found (append found (plist-get b :gadgets)))
                                                (walk (plist-get b :children)))))
                      (walk (plist-get view :blips)))
                    found))
         (gadget (cond ((null gadgets) (user-error "No gadget in this wave"))
                       ((null (cdr gadgets)) (car gadgets))
                       (t (let ((ids (mapcar (lambda (g) (plist-get g :id)) gadgets)))
                            (seq-find (lambda (g) (equal (plist-get g :id)
                                                         (completing-read "Gadget: " ids nil t)))
                                      gadgets))))))
    (wave-ui--wave-action (wave-ui--display-wave-id)
                          (concat "gadgets/" (url-hexify-string (plist-get gadget :id)) "/vote")
                          `(:choice ,choice))
    (accept-process-output nil 0.5)
    (wave-display-refresh)))

(defun wave-ui-render-gadget (attributes level)
  "Render a Yes/No/Maybe gadget from its element ATTRIBUTES at indent LEVEL."
  (let* ((indent (make-string (* 2 (1+ level)) ?\s))
         (columns (mapcar (lambda (choice)
                            (let ((value (plist-get attributes choice)))
                              (if (or (null value) (string-empty-p value)) nil
                                (mapcar (lambda (a) (car (split-string a "@"))) (split-string value ",")))))
                          '(yes no maybe)))
         (title (plist-get attributes 'title))
         (rows (apply #'max 1 (mapcar #'length columns)))
         (cell (lambda (text face) (propertize (truncate-string-to-width (or text "") 14 nil ?\s "…") 'face face))))
    (concat
     "\n"
     (if (and title (not (string-empty-p title))) (concat indent (propertize title 'face 'bold) "\n") "")
     indent
     (funcall cell (format "Yes (%d)" (length (nth 0 columns))) 'wave-ui-yes) " "
     (funcall cell (format "No (%d)" (length (nth 1 columns))) 'wave-ui-no) " "
     (funcall cell (format "Maybe (%d)" (length (nth 2 columns))) 'wave-ui-maybe) "\n"
     (mapconcat (lambda (row)
                  (concat indent
                          (mapconcat (lambda (column) (funcall cell (nth row column) 'default)) columns " ")))
                (number-sequence 0 (1- rows)) "\n")
     "\n")))

(setf (alist-get 'gadget wave-display-element-renderers) #'wave-ui-render-gadget)

(defvar-local wave-ui-playback-steps nil)
(defvar-local wave-ui-playback-index 0)

(defvar wave-ui-playback-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map "." #'wave-ui-playback-next)
    (define-key map "," #'wave-ui-playback-previous)
    (define-key map "q" #'quit-window)
    map))

(define-derived-mode wave-ui-playback-mode special-mode "Wave Playback"
  "Step through a wave's history: . forward, , back.")

(defun wave-ui-playback ()
  "Play back the open wave one blip at a time."
  (interactive)
  (let ((steps (wave-ui-request "GET" (concat "/api/waves/" (wave-ui--encode-path (wave-ui--display-wave-id) "history"))))
        (title (buffer-name)))
    (pop-to-buffer (get-buffer-create (format "*Playback %s*" title)))
    (wave-ui-playback-mode)
    (setq wave-ui-playback-steps steps wave-ui-playback-index 1)
    (wave-ui--playback-render)))

(defun wave-ui--playback-render ()
  (let ((inhibit-read-only t))
    (erase-buffer)
    (insert (propertize (format "Step %d of %d   (. next  , previous  q quit)\n\n"
                                wave-ui-playback-index (length wave-ui-playback-steps))
                        'face 'wave-ui-snippet))
    (cl-loop for step in wave-ui-playback-steps
             for number from 1 to wave-ui-playback-index
             do (insert (propertize (format "%s  %s\n" (car (split-string (plist-get step :author) "@"))
                                            (wave-ui--time (plist-get step :time)))
                                    'face (if (= number wave-ui-playback-index) 'wave-ui-unread 'wave-ui-meta))
                        "  " (plist-get step :text) "\n\n"))))

(defun wave-ui-playback-next ()
  (interactive)
  (setq wave-ui-playback-index (min (length wave-ui-playback-steps) (1+ wave-ui-playback-index)))
  (wave-ui--playback-render))

(defun wave-ui-playback-previous ()
  (interactive)
  (setq wave-ui-playback-index (max 1 (1- wave-ui-playback-index)))
  (wave-ui--playback-render))

(provide 'wave-ui)
;;; wave-ui.el ends here
