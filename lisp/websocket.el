;;; websocket.el --- RFC 6455 websocket behind the 2010 Wave client API -*- lexical-binding: t -*-

;; Licensed under the Apache License, Version 2.0.

;;; Commentary:
;; The original Wave client shipped a websocket.el implementing the
;; hixie-75/76 drafts (preserved in lisp/legacy/websocket-hixie76.el).
;; No current server speaks those drafts; uvicorn answers the hixie
;; handshake with 400.  This file is the intermediate layer: it keeps
;; the four entry points the client calls --
;;
;;   (websocket-open URL FILTER &optional CLOSE-CALLBACK)
;;   (websocket-send WEBSOCKET TEXT)
;;   (websocket-openp WEBSOCKET)
;;   (websocket-close WEBSOCKET)
;;
;; -- and implements them with RFC 6455 framing.  FILTER receives each
;; complete text message as a decoded string, as before.
;;
;; Two behavioural changes, both deliberate:
;; - CLOSE-CALLBACK fires only for a connection that completed its
;;   handshake and was not closed with `websocket-close'.  The client's
;;   callback reconnects synchronously, so firing it on a failed
;;   handshake recursed until `max-lisp-eval-depth'.
;; - Messages sent before the handshake completes are queued, not lost.
;;
;; Not implemented: wss://, extensions, subprotocols.

;;; Code:

(require 'cl-lib)
(require 'url-parse)

(cl-defstruct websocket
  conn filter close-callback url
  (inflight-packet "")              ; unparsed bytes from the server
  (fragments nil)                   ; payloads of a fragmented message
  (handshake-key nil)
  (state 'connecting)               ; connecting | open | closing | closed
  (outbox nil)                      ; texts queued until the handshake
  (v75 nil))                        ; ignored; kept for the old API

(defvar websocket-use-v75 nil
  "Ignored.  Kept because callers let-bind it around `websocket-open'.")

(defvar websocket-debug nil
  "Non-nil to log traffic to a per-connection buffer.")

(defconst websocket--guid "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
  "Magic string from RFC 6455 section 1.3.")

(defun websocket-debug (websocket msg &rest args)
  "Log MSG formatted with ARGS for WEBSOCKET when `websocket-debug'."
  (when websocket-debug
    (with-current-buffer (get-buffer-create
                          (format " *websocket %s debug*" (websocket-url websocket)))
      (goto-char (point-max))
      (insert (apply #'format msg args) "\n"))))

(defun websocket--random-bytes (count)
  "Return a unibyte string of COUNT random bytes."
  (apply #'unibyte-string (cl-loop repeat count collect (random 256))))

(defun websocket--bytes (string)
  "Return STRING as a unibyte string of raw bytes."
  (if (multibyte-string-p string) (encode-coding-string string 'binary) string))

(defun websocket--accept-value (key)
  "Sec-WebSocket-Accept the server must return for KEY."
  (base64-encode-string
   (secure-hash 'sha1 (concat key websocket--guid) nil nil t)))

;;;; Framing

(defun websocket--encode-length (len)
  "Return the 7-bit length byte (masked) plus extended length bytes for LEN."
  (cond ((< len 126) (unibyte-string (logior #x80 len)))
        ((< len 65536) (unibyte-string (logior #x80 126) (ash len -8) (logand len 255)))
        (t (apply #'unibyte-string (logior #x80 127)
                  (cl-loop for shift from 56 downto 0 by 8
                           collect (logand (ash len (- shift)) 255))))))

(defun websocket--frame (opcode payload)
  "Build a masked, final client frame with OPCODE carrying unibyte PAYLOAD."
  (let* ((mask (websocket--random-bytes 4))
         (masked (apply #'unibyte-string
                        (cl-loop for byte across payload
                                 for index from 0
                                 collect (logxor byte (aref mask (% index 4)))))))
    (concat (unibyte-string (logior #x80 opcode))
            (websocket--encode-length (length payload))
            mask masked)))

(defun websocket--parse-frame (data)
  "Parse one server frame from the start of unibyte DATA.
Return (FIN OPCODE PAYLOAD REST), or nil if DATA is incomplete."
  (let* ((size (length data))
         (len7 (and (>= size 2) (logand (aref data 1) #x7f)))
         (offset (pcase len7
                   ('nil nil)
                   (126 4)
                   (127 10)
                   (_ 2))))
    (when (and offset (>= size offset))
      (let* ((byte0 (aref data 0))
             (masked (/= 0 (logand (aref data 1) #x80)))
             (len (if (= offset 2)
                      len7
                    (cl-loop for index from 2 below offset
                             for value = (aref data index)
                             then (logior (ash value 8) (aref data index))
                             finally return value)))
             (start (+ offset (if masked 4 0)))
             (end (+ start len)))
        (when (>= size end)
          (let ((payload (substring data start end)))
            (when masked
              (let ((mask (substring data offset (+ offset 4))))
                (setq payload (apply #'unibyte-string
                                     (cl-loop for byte across payload
                                              for index from 0
                                              collect (logxor byte (aref mask (% index 4))))))))
            (list (/= 0 (logand byte0 #x80))
                  (logand byte0 #x0f)
                  payload
                  (substring data end))))))))

;;;; Connection

(defun websocket--send-frame (websocket opcode payload)
  "Send PAYLOAD with OPCODE on WEBSOCKET's process."
  (process-send-string (websocket-conn websocket) (websocket--frame opcode payload)))

(defun websocket--handle-message (websocket opcode payload)
  "Dispatch a complete message PAYLOAD with OPCODE for WEBSOCKET."
  (pcase opcode
    (1 (funcall (websocket-filter websocket) (decode-coding-string payload 'utf-8)))
    (2 (funcall (websocket-filter websocket) payload))
    (8 (unless (eq (websocket-state websocket) 'closing)
         (ignore-errors (websocket--send-frame websocket 8 payload)))
       (setf (websocket-state websocket) 'closing)
       (delete-process (websocket-conn websocket)))
    (9 (websocket--send-frame websocket 10 payload))
    (10 nil)))

(defun websocket--read-frames (websocket)
  "Consume every complete frame buffered in WEBSOCKET."
  (let (frame)
    (while (and (memq (websocket-state websocket) '(open closing))
                (setq frame (websocket--parse-frame (websocket-inflight-packet websocket))))
      (cl-destructuring-bind (fin opcode payload rest) frame
        (setf (websocket-inflight-packet websocket) rest)
        (cond ((>= opcode 8) (websocket--handle-message websocket opcode payload))
              ((not fin)
               (when (/= opcode 0) (setf (websocket-fragments websocket) (list opcode)))
               (push payload (websocket-fragments websocket)))
              ((= opcode 0)
               (let ((parts (reverse (cons payload (websocket-fragments websocket)))))
                 (setf (websocket-fragments websocket) nil)
                 (websocket--handle-message websocket (car parts)
                                            (apply #'concat (cdr parts)))))
              (t (websocket--handle-message websocket opcode payload)))))))

(defun websocket--read-handshake (websocket)
  "Complete WEBSOCKET's handshake if the full HTTP response has arrived."
  (let* ((data (websocket-inflight-packet websocket))
         (end (string-search "\r\n\r\n" data)))
    (when end
      (let ((headers (substring data 0 end))
            (expected (websocket--accept-value (websocket-handshake-key websocket))))
        (setf (websocket-inflight-packet websocket) (substring data (+ end 4)))
        (if (and (string-match-p "\\`HTTP/1\\.1 101" headers)
                 (string-match-p (concat "^[Ss]ec-[Ww]eb[Ss]ocket-[Aa]ccept: *"
                                         (regexp-quote expected))
                                 headers))
            (progn
              (setf (websocket-state websocket) 'open)
              (websocket-debug websocket "Handshake complete")
              (dolist (text (nreverse (websocket-outbox websocket)))
                (websocket-send websocket text))
              (setf (websocket-outbox websocket) nil))
          (websocket-debug websocket "Handshake rejected: %s" headers)
          (setf (websocket-state websocket) 'closed)
          (delete-process (websocket-conn websocket))
          (message "websocket: handshake rejected by %s: %s"
                   (websocket-url websocket)
                   (car (split-string headers "\r\n"))))))))

(defun websocket--process-filter (websocket output)
  "Accumulate OUTPUT for WEBSOCKET and process what is complete."
  (websocket-debug websocket "Received %d bytes" (length output))
  (setf (websocket-inflight-packet websocket)
        (concat (websocket-inflight-packet websocket) (websocket--bytes output)))
  (when (eq (websocket-state websocket) 'connecting)
    (websocket--read-handshake websocket))
  (websocket--read-frames websocket))

(defun websocket--sentinel (websocket change)
  "Handle process status CHANGE for WEBSOCKET."
  (websocket-debug websocket "State change to %s" (string-trim change))
  (unless (process-live-p (websocket-conn websocket))
    (let ((was (websocket-state websocket)))
      (setf (websocket-state websocket) 'closed)
      (when (and (eq was 'open) (websocket-close-callback websocket))
        (funcall (websocket-close-callback websocket))))))

(defun websocket-open (url filter &optional close-callback)
  "Open a websocket to URL.
Each text message is passed to FILTER as a string.  CLOSE-CALLBACK is
called with no arguments if an established connection drops."
  (let* ((url-struct (url-generic-parse-url url))
         (host (url-host url-struct))
         (port (url-port url-struct))
         (path (let ((filename (url-filename url-struct)))
                 (if (string-empty-p filename) "/" filename)))
         (key (base64-encode-string (websocket--random-bytes 16)))
         (conn (pcase (url-type url-struct)
                 ("ws" (make-network-process
                        :name (format "websocket to %s" url)
                        :buffer nil :host host :service port
                        :coding 'binary :nowait nil))
                 ("wss" (error "websocket: wss:// is not implemented"))
                 (type (error "websocket: unknown scheme %s" type))))
         (websocket (make-websocket :conn conn :url url :filter filter
                                    :close-callback close-callback
                                    :handshake-key key)))
    (set-process-filter conn (lambda (_process output)
                               (websocket--process-filter websocket output)))
    (set-process-sentinel conn (lambda (_process change)
                                 (websocket--sentinel websocket change)))
    (process-send-string
     conn
     (concat (format "GET %s HTTP/1.1\r\n" path)
             (format "Host: %s:%d\r\n" host port)
             "Upgrade: websocket\r\n"
             "Connection: Upgrade\r\n"
             (format "Sec-WebSocket-Key: %s\r\n" key)
             "Sec-WebSocket-Version: 13\r\n\r\n"))
    (websocket-debug websocket "Handshake sent")
    websocket))

(defun websocket-openp (websocket)
  "Return non-nil if WEBSOCKET is connecting or open."
  (and websocket
       (memq (websocket-state websocket) '(connecting open))
       (process-live-p (websocket-conn websocket))))

(defun websocket-send (websocket text)
  "Send TEXT as a text message on WEBSOCKET.
Before the handshake completes, TEXT is queued."
  (unless (websocket-openp websocket)
    (error "websocket: no open connection to %s" (and websocket (websocket-url websocket))))
  (if (eq (websocket-state websocket) 'connecting)
      (push text (websocket-outbox websocket))
    (websocket-debug websocket "Sending: %s" text)
    (websocket--send-frame websocket 1 (encode-coding-string text 'utf-8))))

(defun websocket-close (websocket)
  "Close WEBSOCKET without running its close callback."
  (when (websocket-openp websocket)
    (when (eq (websocket-state websocket) 'open)
      (ignore-errors (websocket--send-frame websocket 8 (unibyte-string 3 232))))
    (setf (websocket-state websocket) 'closing)
    (delete-process (websocket-conn websocket))))

(provide 'websocket)
;;; websocket.el ends here
