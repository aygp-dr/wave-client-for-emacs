;;; websocket-test.el --- ERT tests for the RFC 6455 shim -*- lexical-binding: t -*-
;; Run: emacs -Q --batch -L lisp -l experiments/009-rfc6455-websocket-shim/websocket-test.el -f ert-run-tests-batch-and-exit

(require 'ert)
(require 'websocket)

(defun websocket-test--server-frame (opcode payload &optional fin)
  "Build an unmasked server frame, as a server would send it."
  (let ((len (length payload)))
    (concat (unibyte-string (logior (if (eq fin 'no) 0 #x80) opcode))
            (cond ((< len 126) (unibyte-string len))
                  ((< len 65536) (unibyte-string 126 (ash len -8) (logand len 255)))
                  (t (apply #'unibyte-string 127
                            (cl-loop for shift from 56 downto 0 by 8
                                     collect (logand (ash len (- shift)) 255)))))
            payload)))

(ert-deftest websocket-test-parse-each-length-branch ()
  (dolist (len '(0 1 125 126 127 65535 65536))
    (let* ((payload (make-string len ?x))
           (parsed (websocket--parse-frame
                    (concat (websocket-test--server-frame 1 payload) "tail"))))
      (should (equal (nth 2 parsed) (encode-coding-string payload 'binary)))
      (should (equal (nth 3 parsed) "tail")))))

(ert-deftest websocket-test-client-frame-is-masked-and-decodes ()
  (dolist (len '(0 125 126 65536))
    (let* ((payload (encode-coding-string (make-string len ?y) 'binary))
           (frame (websocket--frame 1 payload))
           (parsed (websocket--parse-frame frame)))
      (should (/= 0 (logand (aref frame 1) #x80)))
      (should (equal (nth 2 parsed) payload)))))

(ert-deftest websocket-test-incomplete-frame-returns-nil ()
  (let ((frame (websocket-test--server-frame 1 (make-string 300 ?z))))
    (dotimes (cut (length frame))
      (should-not (websocket--parse-frame (substring frame 0 cut))))))

(ert-deftest websocket-test-accept-value-matches-rfc-example ()
  ;; RFC 6455 section 1.3
  (should (equal (websocket--accept-value "dGhlIHNhbXBsZSBub25jZQ==")
                 "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=")))

(ert-deftest websocket-test-fragments-and-utf8-reassemble ()
  (let* ((received nil)
         (text "héllo wörld ☃")
         (bytes (encode-coding-string text 'utf-8))
         (websocket (make-websocket :filter (lambda (message) (push message received))
                                    :url "ws://test/" :state 'open)))
    (setf (websocket-inflight-packet websocket)
          (concat (websocket-test--server-frame 1 (substring bytes 0 4) 'no)
                  (websocket-test--server-frame 0 (substring bytes 4 9) 'no)
                  (websocket-test--server-frame 0 (substring bytes 9))))
    (websocket--read-frames websocket)
    (should (equal received (list text)))))
