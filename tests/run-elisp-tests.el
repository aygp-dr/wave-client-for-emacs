;;; run-elisp-tests.el --- Test runner for Wave Elisp code -*- lexical-binding: t -*-

;; This test runner executes the existing Elisp tests without modifying
;; the 15-year-old code we're trying to preserve.

;;; Code:

(require 'ert)

;; Add lisp directory to load path
(add-to-list 'load-path (expand-file-name "../lisp" (file-name-directory load-file-name)))

;; Load the existing test file
(load (expand-file-name "wave-tests.el" (file-name-directory load-file-name)))

;; Define test groups if not already defined
(unless (fboundp 'ert-deftest)
  (error "ERT (Emacs Lisp Regression Testing) is required"))

;; Wrapper to run all tests and exit with appropriate code
(defun wave-run-all-tests ()
  "Run all Wave Elisp tests and exit with appropriate code."
  (let ((stats (ert-run-tests-batch-and-exit)))
    ;; ert-run-tests-batch-and-exit handles the exit
    ))

;; Helper functions for test output
(defun wave-test-summary ()
  "Print a summary of available tests."
  (let ((test-count 0))
    (mapatoms (lambda (sym)
                (when (ert-test-boundp sym)
                  (setq test-count (1+ test-count))
                  (message "  - %s" sym))))
    (message "Total tests found: %d" test-count)))

;; Print test information
(message "Wave Elisp Test Runner")
(message "======================")
(message "Available tests:")
(wave-test-summary)
(message "")
(message "Running tests...")

;; Run the tests
(wave-run-all-tests)

;;; run-elisp-tests.el ends here