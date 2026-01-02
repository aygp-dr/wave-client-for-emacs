;;; connection-test.el --- Test Wave client connection -*- lexical-binding: t -*-

;;; Commentary:
;; Quick test to verify the Emacs Wave client can connect to the local server.
;; Usage: emacs -Q -batch -l lisp/wave-util.el -l lisp/wave-data.el \
;;               -l lisp/websocket.el -l lisp/wave-client-websocket.el \
;;               -l tests/http/connection-test.el

;;; Code:

(require 'url)
(require 'json)

(defvar wave-test-server-url "http://localhost:9898"
  "The HTTP URL for the Wave server.")

(defvar wave-test-ws-url "ws://localhost:9898/ws"
  "The WebSocket URL for the Wave server.")

(defun wave-test-http-get (endpoint)
  "Fetch ENDPOINT from the Wave server and return parsed JSON."
  (let* ((url (concat wave-test-server-url endpoint))
         (url-request-method "GET")
         (buffer (url-retrieve-synchronously url t t 5)))
    (when buffer
      (with-current-buffer buffer
        (goto-char (point-min))
        (re-search-forward "\n\n" nil t)
        (condition-case nil
            (json-read)
          (error nil))))))

(defun wave-test-check-server ()
  "Check if the Wave server is running."
  (message "Testing Wave Server connection...")
  (message "  Server URL: %s" wave-test-server-url)
  (condition-case err
      (let ((result (wave-test-http-get "/")))
        (if result
            (progn
              (message "  ✓ Server is responding")
              t)
          (message "  ✗ Server returned empty response")
          nil))
    (error
     (message "  ✗ Failed to connect: %s" (error-message-string err))
     nil)))

(defun wave-test-check-inbox ()
  "Check if we can fetch the inbox."
  (message "Testing inbox endpoint...")
  (condition-case err
      (let ((result (wave-test-http-get "/api/inbox")))
        (if result
            (progn
              (message "  ✓ Inbox returned %d items" (length result))
              t)
          (message "  ✗ Inbox returned empty response")
          nil))
    (error
     (message "  ✗ Failed to fetch inbox: %s" (error-message-string err))
     nil)))

(defun wave-test-run-all ()
  "Run all connection tests."
  (message "\n=== Wave Client Connection Tests ===\n")
  (let ((results (list
                  (cons "Server" (wave-test-check-server))
                  (cons "Inbox" (wave-test-check-inbox)))))
    (message "\n=== Results ===")
    (dolist (r results)
      (message "  %s: %s" (car r) (if (cdr r) "PASS" "FAIL")))
    (message "")
    ;; Return exit code
    (if (cl-every #'cdr results) 0 1)))

;; Run tests when loaded in batch mode
(when noninteractive
  (kill-emacs (wave-test-run-all)))

(provide 'connection-test)
;;; connection-test.el ends here
