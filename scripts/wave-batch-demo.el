;;; wave-batch-demo.el --- Batch mode demo of Wave client -*- lexical-binding: t -*-

;;; Commentary:
;; Run with: emacs -Q --batch -l scripts/wave-batch-demo.el
;; Requires Wave server running on localhost:9898

;;; Code:

(require 'url)
(require 'json)

(defvar wave-server-url "http://localhost:9898"
  "Wave server URL.")

(defun wave-http-get (endpoint)
  "Fetch ENDPOINT from Wave server and return parsed JSON."
  (let ((url (concat wave-server-url endpoint)))
    (with-current-buffer (url-retrieve-synchronously url t)
      (goto-char (point-min))
      (re-search-forward "^$" nil t)
      (let ((json-object-type 'plist)
            (json-array-type 'list))
        (json-read)))))

(defun wave-print-header (title)
  "Print a formatted header with TITLE."
  (princ "\n")
  (princ "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
  (princ (format "  %s\n" title))
  (princ "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"))

(defun wave-print-separator ()
  "Print a separator line."
  (princ "──────────────────────────────────────────────────────────────────────────────\n"))

(defun wave-demo-health ()
  "Check server health."
  (wave-print-header "🏥 Health Check")
  (let ((health (wave-http-get "/health")))
    (princ (format "  Status: %s\n" (plist-get health :status)))
    (princ (format "  Timestamp: %s\n" (plist-get health :timestamp)))))

(defun wave-demo-inbox ()
  "Display inbox contents."
  (wave-print-header "📧 Wave Inbox")
  (let ((inbox (wave-http-get "/api/inbox")))
    (princ (format "  Found %d waves:\n\n" (length inbox)))
    (dolist (wave inbox)
      (let ((id (plist-get wave :id))
            (digest (plist-get wave :digest))
            (creator (plist-get wave :creator))
            (unread (plist-get wave :unread)))
        (princ (format "  %s %s\n" (if (> unread 0) "●" "○") digest))
        (princ (format "    └─ from: %s\n" creator))
        (princ (format "       id: %s\n\n" id))))))

(defun wave-demo-wave (wave-id)
  "Display details of WAVE-ID."
  (wave-print-header (format "📝 Wave: %s" wave-id))
  (condition-case err
      (let ((wavelets (wave-http-get (format "/api/waves/%s" wave-id))))
        (dolist (wavelet wavelets)
          (let* ((name (plist-get wavelet :wavelet_name))
                 (participants (plist-get wavelet :participants))
                 (version (plist-get wavelet :version))
                 (docs (plist-get wavelet :docs)))
            (princ (format "  Wavelet: %s\n" (plist-get name :wavelet_id)))
            (princ (format "  Creator: %s\n" (plist-get wavelet :creator)))
            (princ (format "  Version: %s\n" (plist-get version :version)))
            (princ (format "  Participants: %s\n" (mapconcat #'identity participants ", ")))
            (princ "\n")
            (when docs
              (princ "  Documents:\n")
              (maphash (lambda (doc-id doc)
                         (princ (format "    • %s\n" doc-id))
                         (let ((content (plist-get doc :content)))
                           (when content
                             (dolist (item content)
                               (princ (format "      %s\n" item))))))
                       docs)))))
    (error (princ (format "  Error: %s\n" (error-message-string err))))))

(defun wave-demo-api-info ()
  "Display API information."
  (wave-print-header "🔌 API Information")
  (let ((info (wave-http-get "/")))
    (princ (format "  Server: %s\n" (plist-get info :message)))
    (princ (format "  Status: %s\n" (plist-get info :status)))
    (princ (format "  Version: %s\n" (plist-get info :version)))))

(defun wave-demo-run ()
  "Run the complete Wave demo."
  (princ "\n")
  (princ "╔══════════════════════════════════════════════════════════════════════════════╗\n")
  (princ "║                     Wave Client for Emacs - Batch Demo                       ║\n")
  (princ "║                                                                              ║\n")
  (princ "║  Connecting to server at localhost:9898                                      ║\n")
  (princ "╚══════════════════════════════════════════════════════════════════════════════╝\n")

  (wave-demo-api-info)
  (wave-demo-health)
  (wave-demo-inbox)
  (wave-demo-wave "indexwave!indexwave")

  (wave-print-separator)
  (princ "  Demo complete.\n")
  (princ "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
  (princ "\n"))

;; Run if in batch mode
(when noninteractive
  (condition-case err
      (wave-demo-run)
    (error
     (princ (format "ERROR: %s\n" (error-message-string err)))
     (princ "Make sure the Wave server is running: gmake server\n"))))

(provide 'wave-batch-demo)
;;; wave-batch-demo.el ends here
