#!/usr/bin/env python3
"""
Experiment 005: JWT Authentication for Wave Protocol

This experiment explores JWT-based authentication for the Wave server,
following OAuth2 standards (RFC 6749) and JWT best practices (RFC 7519).

Topics covered:
1. Token generation with proper claims (iss, sub, aud, exp, iat, jti)
2. Token refresh flow with refresh tokens
3. Token revocation via blacklist
4. Multiple auth method support (.netrc, .authinfo, env vars)
"""

import os
import time
import secrets
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# Attempt to import JWT library
try:
    import jwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False
    print("Note: PyJWT not installed. Run: pip install PyJWT")


@dataclass
class TokenConfig:
    """JWT token configuration following OAuth2 standards."""
    issuer: str = "wave-server"
    audience: str = "wave-client"
    access_token_lifetime: int = 3600  # 1 hour
    refresh_token_lifetime: int = 86400 * 7  # 7 days
    algorithm: str = "HS256"
    secret_key: str = field(default_factory=lambda: os.getenv("JWT_SECRET", secrets.token_urlsafe(32)))


@dataclass
class TokenPair:
    """OAuth2-compliant token response."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600


class JWTAuthenticator:
    """JWT authentication handler for Wave protocol."""

    def __init__(self, config: Optional[TokenConfig] = None):
        self.config = config or TokenConfig()
        self.revoked_tokens: set = set()  # In production, use Redis or DB

    def generate_token_pair(self, user_id: str, extra_claims: Optional[Dict] = None) -> TokenPair:
        """Generate access and refresh token pair."""
        if not HAS_JWT:
            raise RuntimeError("PyJWT required for token generation")

        now = datetime.utcnow()
        jti = secrets.token_urlsafe(16)  # Unique token ID

        # Access token claims
        access_claims = {
            "iss": self.config.issuer,
            "sub": user_id,
            "aud": self.config.audience,
            "exp": now + timedelta(seconds=self.config.access_token_lifetime),
            "iat": now,
            "jti": jti,
            "type": "access",
        }
        if extra_claims:
            access_claims.update(extra_claims)

        access_token = jwt.encode(
            access_claims,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )

        # Refresh token with longer lifetime
        refresh_claims = {
            "iss": self.config.issuer,
            "sub": user_id,
            "exp": now + timedelta(seconds=self.config.refresh_token_lifetime),
            "iat": now,
            "jti": secrets.token_urlsafe(16),
            "type": "refresh",
            "parent_jti": jti,  # Link to access token
        }

        refresh_token = jwt.encode(
            refresh_claims,
            self.config.secret_key,
            algorithm=self.config.algorithm
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_lifetime
        )

    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict]:
        """Verify and decode a JWT token."""
        if not HAS_JWT:
            raise RuntimeError("PyJWT required for token verification")

        try:
            claims = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                audience=self.config.audience if token_type == "access" else None,
                issuer=self.config.issuer
            )

            # Check token type
            if claims.get("type") != token_type:
                return None

            # Check if revoked
            if claims.get("jti") in self.revoked_tokens:
                return None

            return claims

        except jwt.ExpiredSignatureError:
            print("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Invalid token: {e}")
            return None

    def refresh_access_token(self, refresh_token: str) -> Optional[TokenPair]:
        """Generate new token pair from refresh token."""
        claims = self.verify_token(refresh_token, token_type="refresh")
        if not claims:
            return None

        # Revoke old refresh token (rotation)
        self.revoked_tokens.add(claims["jti"])

        # Generate new pair
        return self.generate_token_pair(claims["sub"])

    def revoke_token(self, token: str):
        """Revoke a token by adding its jti to blacklist."""
        if not HAS_JWT:
            return

        try:
            # Decode without verification to get jti
            claims = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
                options={"verify_exp": False}
            )
            self.revoked_tokens.add(claims.get("jti"))
        except jwt.InvalidTokenError:
            pass


class AuthMethodResolver:
    """Resolve authentication credentials from multiple sources."""

    # Priority order for credential sources
    SOURCES = ["environment", "netrc", "authinfo"]

    @staticmethod
    def from_environment() -> Optional[tuple]:
        """Get credentials from environment variables."""
        user = os.getenv("WAVE_CLIENT_USER")
        password = os.getenv("WAVE_CLIENT_PASSWORD")
        if user and password:
            return (user, password)
        return None

    @staticmethod
    def from_netrc(host: str = "localhost") -> Optional[tuple]:
        """Get credentials from .netrc file (like curl/wget)."""
        import netrc
        try:
            netrc_path = os.path.expanduser("~/.netrc")
            if os.path.exists(netrc_path):
                nrc = netrc.netrc(netrc_path)
                auth = nrc.authenticators(host)
                if auth:
                    return (auth[0], auth[2])  # (login, password)
        except Exception as e:
            print(f"Error reading .netrc: {e}")
        return None

    @staticmethod
    def from_authinfo(host: str = "localhost", port: int = 9898) -> Optional[tuple]:
        """Get credentials from .authinfo file (like Emacs/Gnus)."""
        # Format: machine HOST port PORT login USER password PASS
        authinfo_paths = [
            os.path.expanduser("~/.authinfo"),
            os.path.expanduser("~/.authinfo.gpg"),
        ]

        for path in authinfo_paths:
            if os.path.exists(path) and not path.endswith(".gpg"):
                try:
                    with open(path) as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 8:
                                d = dict(zip(parts[::2], parts[1::2]))
                                if d.get("machine") == host:
                                    if port and d.get("port") and int(d["port"]) != port:
                                        continue
                                    return (d.get("login"), d.get("password"))
                except Exception as e:
                    print(f"Error reading {path}: {e}")
        return None

    @classmethod
    def resolve(cls, host: str = "localhost", port: int = 9898) -> Optional[tuple]:
        """Try all sources in priority order."""
        # Try environment first
        creds = cls.from_environment()
        if creds:
            print("Using credentials from environment")
            return creds

        # Try .netrc
        creds = cls.from_netrc(host)
        if creds:
            print("Using credentials from .netrc")
            return creds

        # Try .authinfo
        creds = cls.from_authinfo(host, port)
        if creds:
            print("Using credentials from .authinfo")
            return creds

        print("No credentials found")
        return None


def demo_jwt_flow():
    """Demonstrate JWT authentication flow."""
    print("=" * 60)
    print("JWT Authentication Experiment")
    print("=" * 60)

    if not HAS_JWT:
        print("\nSkipping JWT demo - PyJWT not installed")
        print("Install with: pip install PyJWT")
        return

    auth = JWTAuthenticator()

    # 1. Login - generate tokens
    print("\n1. User Login")
    print("-" * 40)
    tokens = auth.generate_token_pair("alice@localhost")
    print(f"Access Token: {tokens.access_token[:50]}...")
    print(f"Refresh Token: {tokens.refresh_token[:50]}...")
    print(f"Token Type: {tokens.token_type}")
    print(f"Expires In: {tokens.expires_in}s")

    # 2. Verify access token
    print("\n2. Verify Access Token")
    print("-" * 40)
    claims = auth.verify_token(tokens.access_token)
    if claims:
        print(f"Subject: {claims['sub']}")
        print(f"Issuer: {claims['iss']}")
        print(f"Token ID: {claims['jti']}")

    # 3. Refresh tokens
    print("\n3. Refresh Token Flow")
    print("-" * 40)
    new_tokens = auth.refresh_access_token(tokens.refresh_token)
    if new_tokens:
        print(f"New Access Token: {new_tokens.access_token[:50]}...")
        print("Old refresh token revoked")

    # 4. Verify old token is revoked
    print("\n4. Token Revocation Check")
    print("-" * 40)
    if auth.verify_token(tokens.refresh_token, "refresh"):
        print("Old refresh token still valid (unexpected)")
    else:
        print("Old refresh token revoked (expected)")


def demo_auth_resolution():
    """Demonstrate credential resolution from multiple sources."""
    print("\n" + "=" * 60)
    print("Credential Resolution Experiment")
    print("=" * 60)

    print("\n.netrc format (like curl/wget):")
    print('  machine localhost login alice@localhost password secret')

    print("\n.authinfo format (like Emacs/Gnus):")
    print('  machine localhost port 9898 login alice@localhost password secret')

    print("\nEnvironment variables:")
    print("  WAVE_CLIENT_USER=alice@localhost")
    print("  WAVE_CLIENT_PASSWORD=secret")

    print("\nAttempting credential resolution...")
    creds = AuthMethodResolver.resolve()
    if creds:
        print(f"Resolved: user={creds[0]}, password={'*' * len(creds[1])}")


if __name__ == "__main__":
    demo_jwt_flow()
    demo_auth_resolution()

    print("\n" + "=" * 60)
    print("Experiment Complete")
    print("=" * 60)
    print("\nSee also:")
    print("  - RFC 7519 (JWT)")
    print("  - RFC 6749 (OAuth 2.0)")
    print("  - specs/wave-api.openapi.yaml (API contract)")
