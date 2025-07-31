;;; init-dev.el --- Development setup for Wave Client -*- lexical-binding: t -*-

;;; Commentary:
;; Development configuration for Wave Client
;; Includes REST client, literate programming support, and testing tools
;; Usage: emacs -nw -Q -l init-dev.el

;;; Code:

;; Initialize package system
(require 'package)
(add-to-list 'package-archives '("melpa" . "https://melpa.org/packages/") t)
(package-initialize)

;; Development packages
(defvar wave-dev-packages
  '(restclient           ; REST client for HTTP testing
    ob-http              ; Org Babel HTTP support
    ob-restclient        ; Org Babel restclient support
    company              ; Completion framework
    which-key            ; Display available keybindings
    )
  "Packages useful for Wave client development.")

;; Install packages if needed
(dolist (pkg wave-dev-packages)
  (unless (package-installed-p pkg)
    (message "Installing %s..." pkg)
    (package-refresh-contents)
    (package-install pkg)))

;; Load the base init
(load (expand-file-name "init.el" default-directory))

;; Configure Org Babel for literate programming
(require 'org)
(require 'ob-http nil t)
(require 'ob-restclient nil t)

(org-babel-do-load-languages
 'org-babel-load-languages
 '((emacs-lisp . t)
   (shell . t)
   (python . t)
   (http . t)
   (restclient . t)))

;; Don't ask for confirmation when evaluating code blocks
(setq org-confirm-babel-evaluate nil)

;; REST client configuration
(require 'restclient)

;; Which-key for discovering keybindings
(when (require 'which-key nil t)
  (which-key-mode 1))

;; Company mode for completion
(when (require 'company nil t)
  (global-company-mode 1))

;; Development keybindings
(global-set-key (kbd "C-c d r") 'restclient-mode)
(global-set-key (kbd "C-c d t") 
                (lambda () 
                  (interactive)
                  (find-file "examples/README.org")))
(global-set-key (kbd "C-c d h")
                (lambda ()
                  (interactive)
                  (find-file "tests/http/")))

;; Helper functions for development
(defun wave-dev-run-server ()
  "Run the Wave server in a compile buffer."
  (interactive)
  (compile "make server"))

(defun wave-dev-run-tests ()
  "Run all tests."
  (interactive)
  (compile "make test"))

(defun wave-dev-tangle-examples ()
  "Tangle examples from org files."
  (interactive)
  (compile "make -C examples tangle"))

;; Development menu
(defvar wave-dev-menu-map
  (let ((map (make-sparse-keymap "Wave Dev")))
    (define-key map [run-tests] '("Run Tests" . wave-dev-run-tests))
    (define-key map [run-server] '("Run Server" . wave-dev-run-server))
    (define-key map [tangle] '("Tangle Examples" . wave-dev-tangle-examples))
    (define-key map [separator] '("--"))
    (define-key map [examples] '("Open Examples" . (lambda () (interactive) (find-file "examples/README.org"))))
    (define-key map [http-tests] '("HTTP Tests" . (lambda () (interactive) (find-file "tests/http/"))))
    map))

(define-key global-map [menu-bar wave-dev] (cons "Wave-Dev" wave-dev-menu-map))

;; Add to the startup buffer
(with-current-buffer "*Wave Client*"
  (goto-char (point-max))
  (insert "\n\nDevelopment Mode Active\n")
  (insert "======================\n")
  (insert "Additional commands:\n")
  (insert "  C-c d r  - Open REST client mode\n")
  (insert "  C-c d t  - Open test examples (README.org)\n")
  (insert "  C-c d h  - Browse HTTP test files\n")
  (insert "\nDevelopment functions:\n")
  (insert "  M-x wave-dev-run-server    - Start Wave server\n")
  (insert "  M-x wave-dev-run-tests     - Run all tests\n")
  (insert "  M-x wave-dev-tangle-examples - Generate HTTP test files\n"))

(message "Wave Client development mode initialized")

(provide 'init-dev)
;;; init-dev.el ends here