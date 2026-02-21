"""
Security configuration and utilities for ISO 27001, NIST SP 800-53, and OWASP ASVS compliance.

This module implements security controls aligned with:
- ISO 27001:2013 Information Security Management
- NIST SP 800-53 Rev 5 Security and Privacy Controls
- OWASP Application Security Verification Standard (ASVS) 4.0
"""

import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time


# Security Configuration
# ISO 27001 A.9.4.2, NIST SP 800-53 AC-12, OWASP ASVS 3.3.1
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))
ABSOLUTE_SESSION_TIMEOUT_HOURS = int(os.getenv("ABSOLUTE_SESSION_TIMEOUT_HOURS", "8"))

# Password Policy
# ISO 27001 A.9.4.3, NIST SP 800-53 IA-5, OWASP ASVS 2.1.1-9
PASSWORD_MIN_LENGTH = int(os.getenv("PASSWORD_MIN_LENGTH", "12"))
PASSWORD_REQUIRE_UPPERCASE = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_LOWERCASE = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
PASSWORD_REQUIRE_DIGITS = os.getenv("PASSWORD_REQUIRE_DIGITS", "true").lower() == "true"
PASSWORD_REQUIRE_SPECIAL = os.getenv("PASSWORD_REQUIRE_SPECIAL", "true").lower() == "true"
PASSWORD_MAX_AGE_DAYS = int(os.getenv("PASSWORD_MAX_AGE_DAYS", "90"))

# Rate Limiting
# NIST SP 800-53 SC-5, OWASP ASVS 2.2.1
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
LOGIN_RATE_LIMIT = int(os.getenv("LOGIN_RATE_LIMIT", "5"))
LOGIN_RATE_WINDOW = int(os.getenv("LOGIN_RATE_WINDOW", "300"))  # 5 minutes

# File Upload Security
# OWASP ASVS 12.1.1-3, NIST SP 800-53 SI-10
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(5 * 1024 * 1024)))  # 5MB default
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/gif', 'image/webp'
}

# Security Headers
# OWASP ASVS 14.4.1-7, NIST SP 800-53 SC-8
SECURITY_HEADERS_ENABLED = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() == "true"

# Content Security Policy
# OWASP ASVS 14.4.7
CSP_POLICY = os.getenv("CSP_POLICY",
    "default-src 'self'; "
    "script-src 'self' https://cdn.jsdelivr.net https://d3js.org https://cdnjs.cloudflare.com 'unsafe-inline'; "
    "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "connect-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
    "frame-ancestors 'none';"
)


class PasswordValidator:
    """
    Password validation implementing NIST SP 800-63B and OWASP ASVS 2.1 requirements.
    """

    @staticmethod
    def validate_password(password: str) -> tuple[bool, list[str]]:
        """
        Validate password against security policy.

        Returns:
            tuple: (is_valid, list_of_errors)
        """
        errors = []

        # Check minimum length (OWASP ASVS 2.1.1)
        if len(password) < PASSWORD_MIN_LENGTH:
            errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")

        # Check maximum length to prevent DoS (OWASP ASVS 2.1.1)
        if len(password) > 128:
            errors.append("Password must not exceed 128 characters")

        # Check for uppercase letters (NIST SP 800-63B)
        if PASSWORD_REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        # Check for lowercase letters
        if PASSWORD_REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")

        # Check for digits
        if PASSWORD_REQUIRE_DIGITS and not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")

        # Check for special characters
        if PASSWORD_REQUIRE_SPECIAL and not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
            errors.append("Password must contain at least one special character")

        # Check for common patterns (OWASP ASVS 2.1.7)
        common_patterns = ['password', '123456', 'qwerty', 'abc123', 'admin']
        if any(pattern in password.lower() for pattern in common_patterns):
            errors.append("Password contains common patterns and is too weak")

        return (len(errors) == 0, errors)

    @staticmethod
    def check_password_history(user_id: int, password_hash: str) -> bool:
        """
        Check if password was used in history (OWASP ASVS 2.1.9).
        Implementation would check against password history table.
        """
        # TODO: Implement password history check in database
        return True


class RateLimiter:
    """
    Rate limiting implementation for brute force protection.
    NIST SP 800-53 SC-5, OWASP ASVS 2.2.1
    """

    def __init__(self):
        self.requests: Dict[str, list[float]] = defaultdict(list)
        self.login_attempts: Dict[str, list[float]] = defaultdict(list)

    def check_rate_limit(self, identifier: str, limit: int = RATE_LIMIT_REQUESTS,
                        window: int = RATE_LIMIT_WINDOW_SECONDS) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (IP address or user ID)
            limit: Maximum number of requests
            window: Time window in seconds

        Returns:
            bool: True if within limit, False if exceeded
        """
        if not RATE_LIMIT_ENABLED:
            return True

        current_time = time.time()
        cutoff_time = current_time - window

        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if req_time > cutoff_time
        ]

        # Check limit
        if len(self.requests[identifier]) >= limit:
            return False

        # Add current request
        self.requests[identifier].append(current_time)
        return True

    def check_login_rate_limit(self, identifier: str) -> bool:
        """
        Stricter rate limit for login attempts (OWASP ASVS 2.2.1).
        """
        return self.check_rate_limit(
            f"login_{identifier}",
            limit=LOGIN_RATE_LIMIT,
            window=LOGIN_RATE_WINDOW
        )

    def reset_login_attempts(self, identifier: str):
        """Reset login attempts after successful authentication."""
        key = f"login_{identifier}"
        if key in self.requests:
            self.requests[key] = []


# Global rate limiter instance
rate_limiter = RateLimiter()


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses.
    Implements OWASP ASVS 14.4.1-7, NIST SP 800-53 SC-8
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if not SECURITY_HEADERS_ENABLED:
            return response

        # Strict-Transport-Security (HSTS) - OWASP ASVS 9.1.3
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # X-Frame-Options - OWASP ASVS 14.4.2
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options - OWASP ASVS 14.4.3
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-XSS-Protection - OWASP ASVS 14.4.1
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content-Security-Policy - OWASP ASVS 14.4.7
        response.headers["Content-Security-Policy"] = CSP_POLICY

        # Referrer-Policy - OWASP ASVS 14.4.6
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy - OWASP ASVS 14.4.5
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )

        # Remove server header to prevent information disclosure
        response.headers["Server"] = "Secure"

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.
    Implements NIST SP 800-53 SC-5, OWASP ASVS 2.2.1
    """

    async def dispatch(self, request: Request, call_next):
        if not RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not rate_limiter.check_rate_limit(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later."
            )

        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMIT_REQUESTS)
        response.headers["X-RateLimit-Window"] = str(RATE_LIMIT_WINDOW_SECONDS)

        return response


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    Implements OWASP ASVS 5.1.1-5, NIST SP 800-53 SI-10

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        str: Sanitized text
    """
    if not text:
        return text

    # Truncate to maximum length
    text = text[:max_length]

    # Remove null bytes
    text = text.replace('\x00', '')

    # Replace dangerous HTML characters
    html_escape_table = {
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#x27;",
        ">": "&gt;",
        "<": "&lt;",
    }

    return "".join(html_escape_table.get(c, c) for c in text)


def validate_file_upload(filename: str, content_type: str, file_size: int) -> tuple[bool, str]:
    """
    Validate file upload for security.
    Implements OWASP ASVS 12.1.1-3, NIST SP 800-53 SI-10

    Args:
        filename: Original filename
        content_type: MIME type
        file_size: File size in bytes

    Returns:
        tuple: (is_valid, error_message)
    """
    # Check file size (OWASP ASVS 12.1.1)
    if file_size > MAX_FILE_SIZE:
        return False, f"File size exceeds maximum allowed size of {MAX_FILE_SIZE / (1024*1024):.1f}MB"

    # Check file extension (OWASP ASVS 12.1.2)
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, f"File type not allowed. Allowed types: {', '.join(ALLOWED_IMAGE_EXTENSIONS)}"

    # Check MIME type (OWASP ASVS 12.1.2)
    if content_type not in ALLOWED_MIME_TYPES:
        return False, f"Invalid file type. Expected image file."

    # Check for path traversal (OWASP ASVS 12.3.1)
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Invalid filename. Path traversal detected."

    return True, ""


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token.
    Implements NIST SP 800-63B, OWASP ASVS 2.6.3

    Args:
        length: Token length in bytes

    Returns:
        str: Hex-encoded secure random token
    """
    return secrets.token_hex(length)


def generate_secure_filename(original_filename: str) -> str:
    """
    Generate secure filename to prevent directory traversal and injection.
    Implements OWASP ASVS 12.3.1

    Args:
        original_filename: Original uploaded filename

    Returns:
        str: Secure filename
    """
    # Get extension
    ext = os.path.splitext(original_filename.lower())[1]

    # Generate secure random name
    secure_name = generate_secure_token(16)

    return f"{secure_name}{ext}"


def hash_password_for_breach_check(password: str) -> str:
    """
    Hash password for checking against breach databases (k-anonymity model).
    Implements OWASP ASVS 2.1.7

    Args:
        password: Password to hash

    Returns:
        str: SHA-1 hash (first 5 characters for API lookup)
    """
    sha1_hash = hashlib.sha1(password.encode('utf-8')).hexdigest().upper()
    return sha1_hash[:5]


def get_client_ip(request: Request) -> str:
    """
    Extract client IP address from request, handling proxies.
    Implements ISO 27001 A.12.4.1, NIST SP 800-53 AU-2

    Args:
        request: FastAPI request object

    Returns:
        str: Client IP address
    """
    # Check for X-Forwarded-For header (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP in chain (original client)
        return forwarded_for.split(",")[0].strip()

    # Check for X-Real-IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"


# Audit Log Levels aligned with ISO 27001 A.12.4.1
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"
LOG_LEVEL_CRITICAL = "CRITICAL"

# Security Event Categories
SECURITY_EVENT_AUTH = "authentication"
SECURITY_EVENT_AUTHZ = "authorization"
SECURITY_EVENT_DATA_ACCESS = "data_access"
SECURITY_EVENT_DATA_CHANGE = "data_change"
SECURITY_EVENT_CONFIG_CHANGE = "config_change"
SECURITY_EVENT_ADMIN = "admin_action"
