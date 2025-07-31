;;; init.el --- Wave Client Emacs Configuration -*- lexical-binding: t -*-

;;; Commentary:
;; Minimal configuration for running Wave Client in Emacs
;; This file is loaded with: emacs -nw -Q -l init.el

;;; Code:

;; Add lisp directory to load path
(add-to-list 'load-path (expand-file-name "lisp" default-directory))

;; Load Wave client
(require 'wave-list)

;; Configure Wave client from environment variables
(let ((user (getenv "WAVE_CLIENT_USER"))
      (domain (getenv "WAVE_CLIENT_DOMAIN"))
      (ws-url (getenv "WAVE_WS_URL"))
      (debug (getenv "WAVE_DEBUG")))
  
  ;; Set user
  (when user
    (setq wave-client-user user))
  
  ;; Set domain (empty string means localhost)
  (when domain
    (setq wave-client-domain (if (string-empty-p domain) nil domain)))
  
  ;; Set WebSocket URL
  (when ws-url
    (setq wave-client-ws-url ws-url))
  
  ;; Enable debug if requested
  (when (and debug (member debug '("true" "1" "yes")))
    (setq wave-debug t)))

;; Use WebSocket connection method
(setq wave-client-connection-method 'websocket)

;; Display configuration
(message "Wave Client Configuration:")
(message "  User: %s" wave-client-user)
(message "  Domain: %s" (or wave-client-domain "localhost"))
(message "  WebSocket URL: %s" wave-client-ws-url)
(message "  Debug: %s" (if wave-debug "enabled" "disabled"))

;; Key bindings
(global-set-key (kbd "C-c w l") 'wave-list-mode)
(global-set-key (kbd "C-c w q") 'kill-emacs)

;; Start with instructions
(switch-to-buffer "*Wave Client*")
(insert "Wave Client for Emacs\n")
(insert "====================\n\n")
(insert "Configuration loaded from environment:\n")
(insert (format "  User: %s\n" wave-client-user))
(insert (format "  Domain: %s\n" (or wave-client-domain "localhost")))
(insert (format "  WebSocket: %s\n\n" wave-client-ws-url))
(insert "Commands:\n")
(insert "  C-c w l  - Open Wave list\n")
(insert "  C-c w q  - Quit Emacs\n\n")
(insert "Press C-c w l to start...")

(provide 'init)
;;; init.el ends here