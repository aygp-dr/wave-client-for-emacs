#!/usr/bin/env python3
"""
Experiment 006: Security Hardening for Wave Server

This experiment explores security hardening measures for the Wave server,
following OWASP recommendations and security best practices.

Topics covered:
1. CORS configuration
2. Rate limiting
3. Input validation
4. Security headers
5. WebSocket security
"""

import time
import hashlib
import hmac
import secrets
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from functools import wraps


@dataclass
class CORSConfig:
    """CORS configuration following OWASP recommendations."""
    allowed_origins: List[str] = field(default_factory=lambda: ["http://localhost:9898"])
    allowed_methods: List[str] = field(default_factory=lambda: ["GET", "POST", "OPTIONS"])
    allowed_headers: List[str] = field(default_factory=lambda: ["Authorization", "Content-Type"])
    expose_headers: List[str] = field(default_factory=list)
    allow_credentials: bool = False  # Be careful with this + wildcards
    max_age: int = 3600

    def validate_origin(self, origin: str) -> bool:
        """Check if origin is allowed."""
        if "*" in self.allowed_origins:
            return True
        return origin in self.allowed_origins

    def to_headers(self, origin: str) -> Dict[str, str]:
        """Generate CORS headers for response."""
        if not self.validate_origin(origin):
            return {}

        headers = {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": ", ".join(self.allowed_methods),
            "Access-Control-Allow-Headers": ", ".join(self.allowed_headers),
            "Access-Control-Max-Age": str(self.max_age),
        }
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        return headers


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_size: int = 10  # Allow burst of requests
    block_duration: int = 300  # Block for 5 minutes after limit exceeded


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self.buckets: Dict[str, Dict] = defaultdict(lambda: {
            "tokens": self.config.burst_size,
            "last_update": time.time(),
        })
        self.blocked_until: Dict[str, float] = {}

    def _refill_bucket(self, client_id: str):
        """Refill tokens based on time elapsed."""
        bucket = self.buckets[client_id]
        now = time.time()
        elapsed = now - bucket["last_update"]

        # Refill rate: requests_per_minute / 60 = tokens per second
        refill_rate = self.config.requests_per_minute / 60
        new_tokens = elapsed * refill_rate

        bucket["tokens"] = min(
            self.config.burst_size,
            bucket["tokens"] + new_tokens
        )
        bucket["last_update"] = now

    def is_allowed(self, client_id: str) -> tuple:
        """Check if request is allowed. Returns (allowed, retry_after)."""
        now = time.time()

        # Check if blocked
        if client_id in self.blocked_until:
            if now < self.blocked_until[client_id]:
                retry_after = int(self.blocked_until[client_id] - now)
                return (False, retry_after)
            del self.blocked_until[client_id]

        # Refill and check tokens
        self._refill_bucket(client_id)
        bucket = self.buckets[client_id]

        if bucket["tokens"] >= 1:
            bucket["tokens"] -= 1
            return (True, 0)
        else:
            # Block the client
            self.blocked_until[client_id] = now + self.config.block_duration
            return (False, self.config.block_duration)


class InputValidator:
    """Input validation for Wave protocol messages."""

    # Maximum sizes for various inputs
    MAX_WAVE_ID_LENGTH = 128
    MAX_WAVELET_ID_LENGTH = 128
    MAX_BLIP_LENGTH = 100000  # 100KB
    MAX_PARTICIPANT_EMAIL_LENGTH = 254
    MAX_PARTICIPANTS = 100

    # Allowed characters in IDs
    SAFE_ID_CHARS = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!+-_@.")

    @classmethod
    def validate_wave_id(cls, wave_id: str) -> tuple:
        """Validate wave ID format. Returns (valid, error_message)."""
        if not wave_id:
            return (False, "Wave ID is required")
        if len(wave_id) > cls.MAX_WAVE_ID_LENGTH:
            return (False, f"Wave ID exceeds {cls.MAX_WAVE_ID_LENGTH} characters")
        if not all(c in cls.SAFE_ID_CHARS for c in wave_id):
            return (False, "Wave ID contains invalid characters")
        if "!" not in wave_id:
            return (False, "Wave ID must contain domain separator '!'")
        return (True, None)

    @classmethod
    def validate_email(cls, email: str) -> tuple:
        """Validate participant email format."""
        if not email:
            return (False, "Email is required")
        if len(email) > cls.MAX_PARTICIPANT_EMAIL_LENGTH:
            return (False, f"Email exceeds {cls.MAX_PARTICIPANT_EMAIL_LENGTH} characters")
        if "@" not in email:
            return (False, "Invalid email format")
        # Basic email pattern (not RFC 5322 compliant, but good enough)
        local, _, domain = email.partition("@")
        if not local or not domain or "." not in domain:
            return (False, "Invalid email format")
        return (True, None)

    @classmethod
    def sanitize_content(cls, content: str) -> str:
        """Sanitize content for XSS prevention."""
        # Replace dangerous characters
        replacements = {
            "<": "&lt;",
            ">": "&gt;",
            "&": "&amp;",
            '"': "&quot;",
            "'": "&#x27;",
        }
        for char, replacement in replacements.items():
            content = content.replace(char, replacement)
        return content


@dataclass
class SecurityHeaders:
    """Security headers for HTTP responses."""

    # Content Security Policy
    csp: str = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'"

    # Other security headers
    headers: Dict[str, str] = field(default_factory=lambda: {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    })

    def to_headers(self) -> Dict[str, str]:
        """Return all security headers."""
        return {
            "Content-Security-Policy": self.csp,
            **self.headers
        }


class WebSocketSecurityValidator:
    """Security validation for WebSocket connections."""

    def __init__(self, allowed_origins: List[str] = None):
        self.allowed_origins = allowed_origins or ["http://localhost:9898"]

    def validate_origin(self, origin: str) -> bool:
        """Validate WebSocket connection origin."""
        return origin in self.allowed_origins

    def validate_protocol_message(self, message: dict) -> tuple:
        """Validate incoming WebSocket message structure."""
        required_fields = ["version", "sequenceNumber", "messageType", "messageJson"]

        for field in required_fields:
            if field not in message:
                return (False, f"Missing required field: {field}")

        if message["version"] not in [0, 1]:
            return (False, "Unsupported protocol version")

        valid_types = ["ProtocolOpenRequest", "ProtocolSubmitRequest", "ProtocolWaveletUpdate"]
        if message["messageType"] not in valid_types:
            return (False, f"Invalid message type: {message['messageType']}")

        return (True, None)

    @staticmethod
    def generate_ws_ticket(user_id: str, secret_key: str, expires_in: int = 300) -> str:
        """Generate a time-limited WebSocket connection ticket."""
        expires = int(time.time()) + expires_in
        data = f"{user_id}:{expires}"
        signature = hmac.new(
            secret_key.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{data}:{signature}"

    @staticmethod
    def verify_ws_ticket(ticket: str, secret_key: str) -> Optional[str]:
        """Verify WebSocket ticket. Returns user_id if valid."""
        try:
            parts = ticket.rsplit(":", 1)
            if len(parts) != 2:
                return None
            data, signature = parts

            # Verify signature
            expected = hmac.new(
                secret_key.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected):
                return None

            # Check expiration
            user_id, expires_str = data.rsplit(":", 1)
            if int(time.time()) > int(expires_str):
                return None

            return user_id
        except Exception:
            return None


def demo_cors():
    """Demonstrate CORS configuration."""
    print("=" * 60)
    print("CORS Configuration Demo")
    print("=" * 60)

    config = CORSConfig(
        allowed_origins=["http://localhost:9898", "http://localhost:3000"],
        allow_credentials=False,
    )

    print("\nAllowed origins:", config.allowed_origins)
    print("\nValidating origins:")
    for origin in ["http://localhost:9898", "http://evil.com", "http://localhost:3000"]:
        valid = config.validate_origin(origin)
        print(f"  {origin}: {'allowed' if valid else 'BLOCKED'}")

    print("\nGenerated headers for allowed origin:")
    headers = config.to_headers("http://localhost:9898")
    for k, v in headers.items():
        print(f"  {k}: {v}")


def demo_rate_limiting():
    """Demonstrate rate limiting."""
    print("\n" + "=" * 60)
    print("Rate Limiting Demo")
    print("=" * 60)

    config = RateLimitConfig(requests_per_minute=5, burst_size=3)
    limiter = RateLimiter(config)

    client = "192.168.1.100"
    print(f"\nConfig: {config.requests_per_minute} req/min, burst size {config.burst_size}")
    print(f"Client: {client}")
    print("\nMaking requests:")

    for i in range(8):
        allowed, retry_after = limiter.is_allowed(client)
        if allowed:
            print(f"  Request {i+1}: ALLOWED")
        else:
            print(f"  Request {i+1}: BLOCKED (retry after {retry_after}s)")


def demo_input_validation():
    """Demonstrate input validation."""
    print("\n" + "=" * 60)
    print("Input Validation Demo")
    print("=" * 60)

    print("\nWave ID validation:")
    test_ids = [
        "localhost!w+abc123",
        "invalid_no_bang",
        "a" * 200,  # Too long
        "localhost!w+<script>alert(1)</script>",
    ]
    for wave_id in test_ids:
        valid, error = InputValidator.validate_wave_id(wave_id)
        status = "valid" if valid else f"INVALID: {error}"
        print(f"  {wave_id[:40]:40} -> {status}")

    print("\nEmail validation:")
    test_emails = [
        "alice@localhost",
        "bob@example.com",
        "invalid",
        "@nodomain.com",
    ]
    for email in test_emails:
        valid, error = InputValidator.validate_email(email)
        status = "valid" if valid else f"INVALID: {error}"
        print(f"  {email:30} -> {status}")

    print("\nContent sanitization:")
    malicious = '<script>alert("xss")</script>'
    safe = InputValidator.sanitize_content(malicious)
    print(f"  Input:  {malicious}")
    print(f"  Output: {safe}")


def demo_security_headers():
    """Demonstrate security headers."""
    print("\n" + "=" * 60)
    print("Security Headers Demo")
    print("=" * 60)

    headers = SecurityHeaders()
    print("\nRecommended security headers:")
    for k, v in headers.to_headers().items():
        print(f"  {k}:")
        print(f"    {v}")


def demo_websocket_security():
    """Demonstrate WebSocket security."""
    print("\n" + "=" * 60)
    print("WebSocket Security Demo")
    print("=" * 60)

    ws_sec = WebSocketSecurityValidator()
    secret = secrets.token_urlsafe(32)

    print("\nOrigin validation:")
    for origin in ["http://localhost:9898", "http://evil.com"]:
        valid = ws_sec.validate_origin(origin)
        print(f"  {origin}: {'allowed' if valid else 'BLOCKED'}")

    print("\nWebSocket ticket generation:")
    ticket = ws_sec.generate_ws_ticket("alice@localhost", secret, expires_in=60)
    print(f"  Ticket: {ticket[:50]}...")

    user = ws_sec.verify_ws_ticket(ticket, secret)
    print(f"  Verified user: {user}")

    # Tampered ticket
    bad_ticket = ticket[:-1] + "X"
    user = ws_sec.verify_ws_ticket(bad_ticket, secret)
    print(f"  Tampered ticket verification: {user}")


if __name__ == "__main__":
    demo_cors()
    demo_rate_limiting()
    demo_input_validation()
    demo_security_headers()
    demo_websocket_security()

    print("\n" + "=" * 60)
    print("Security Hardening Experiment Complete")
    print("=" * 60)
    print("\nRecommendations:")
    print("  1. Enable CORS with explicit allowed origins (not *)")
    print("  2. Implement rate limiting per client IP")
    print("  3. Validate and sanitize all inputs")
    print("  4. Set security headers on all responses")
    print("  5. Use time-limited tickets for WebSocket auth")
    print("\nSee also:")
    print("  - OWASP Top 10")
    print("  - OWASP API Security Top 10")
    print("  - RFC 6454 (Origin)")
