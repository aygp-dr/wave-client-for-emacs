# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| < 0.2   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in Wave Client for Emacs, please report it responsibly:

1. **Do NOT open a public issue** for security vulnerabilities
2. Email the maintainers directly at: security@defrecord.com
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Any suggested fixes (optional)

## Response Timeline

- **Initial Response**: Within 48 hours
- **Assessment**: Within 7 days
- **Fix Timeline**: Varies by severity
  - Critical: 24-48 hours
  - High: 7 days
  - Medium: 30 days
  - Low: Next release

## Security Considerations

### Current Status

This project is currently in **development/research phase** and should NOT be used in production without additional security hardening.

### Known Limitations

1. **Authentication**: JWT authentication is available via experiments but not integrated into production server
2. **CORS**: Configured via `ALLOWED_ORIGINS` environment variable - ensure proper configuration in production
3. **Rate Limiting**: Not yet implemented in production (see experiments/006-security-hardening)
4. **WebSocket Security**: Origin validation available but not enforced by default

### Production Deployment Checklist

Before deploying to production:

- [ ] Set `ALLOWED_ORIGINS` environment variable to specific domains
- [ ] Enable HTTPS/TLS termination
- [ ] Implement authentication middleware
- [ ] Enable rate limiting
- [ ] Review and restrict CORS headers
- [ ] Configure security headers (CSP, X-Frame-Options, etc.)
- [ ] Audit all dependencies for vulnerabilities
- [ ] Enable comprehensive logging and monitoring

### Security Headers

The following security headers are recommended for production:

```
Content-Security-Policy: default-src 'self'
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### Dependency Security

Run security audits regularly:

```bash
# Python dependencies
pip-audit

# Check for known vulnerabilities
uv pip install safety && safety check
```

## Security Experiments

Security-related proof-of-concept code is available in:

- `experiments/005-jwt-authentication/` - JWT token generation and validation
- `experiments/006-security-hardening/` - CORS, rate limiting, input validation

These experiments demonstrate security patterns that should be integrated before production use.
