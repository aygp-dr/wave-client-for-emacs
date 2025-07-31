(defun wave-generate-test-id ()
  "Generate a test wave ID."
  (format "localhost!w+test%s" (format-time-string "%Y%m%d%H%M%S")))

(defun wave-test-request (endpoint &optional method data)
  "Make a test request to wave server."
  (let ((url (format "http://localhost:9898%s" endpoint))
        (url-request-method (or method "GET"))
        (url-request-extra-headers '(("Content-Type" . "application/json")))
        (url-request-data (when data (json-encode data))))
    (with-current-buffer (url-retrieve-synchronously url)
      (goto-char (point-min))
      (re-search-forward "^$")
      (json-read))))
