;;; wave-ws-inbox.el --- Fetch inbox and one wave through the real client -*- lexical-binding: nil -*-
;; Uses the return values of wave-ws-get-inbox / wave-ws-get-wave: the client
;; registers callbacks only after a 1s wait, so early updates never reach them.
(require 'cl)
(require 'wave-client)
(require 'wave-client-websocket)
(setq wave-client-connection-method 'websocket
      wave-client-ws-url "ws://localhost:9898/ws"
      wave-client-user "batch@localhost"
      wave-client-domain "localhost")
(wave-client-ws-connect wave-client-ws-url)
(let ((inbox (wave-ws-get-inbox #'ignore)))
  (message "=== INBOX (%d waves) ===" (length inbox))
  (dolist (wave inbox)
    (message "  %-22s %-15s %s" (plist-get wave :id) (plist-get wave :creator) (plist-get wave :digest))))
(let ((wavelets (wave-ws-get-wave "localhost!w+abc123" #'ignore)))
  (dolist (wavelet wavelets)
    (message "wavelet %S participants %S" (wave-wavelet-wavelet-name wavelet) (wave-wavelet-participants wavelet))
    (maphash (lambda (doc-id doc) (message "  %s by %S: %S" doc-id (wave-doc-contributors doc) (wave-doc-content doc)))
             (wave-wavelet-docs wavelet))))
