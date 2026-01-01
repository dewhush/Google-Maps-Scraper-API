"""
LeadMaps Security Module
========================
Centralized security utilities for input validation, output encoding,
path traversal prevention, and IDOR protection.

Threat Model Coverage:
- SQL Injection: Input sanitization before DB operations
- XSS (Stored): HTML entity encoding for user content
- RCE: Pattern blocking and safe execution practices
- Path Traversal: Path normalization and validation
- IDOR: Ownership verification helpers
"""

import os
import re
import html
import secrets
from typing import Optional
import json
from datetime import datetime


# ==============================================================================
# INPUT VALIDATION & SANITIZATION
# ==============================================================================

def sanitize_string(value: str, max_length: int = 1000, allow_newlines: bool = False) -> str:
    """
    Sanitize a string by removing dangerous characters and limiting length.
    
    Args:
        value: The input string to sanitize
        max_length: Maximum allowed length (default 1000)
        allow_newlines: Whether to preserve newlines (default False)
    
    Returns:
        Sanitized string safe for storage and display
    """
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    
    # Truncate to max length
    value = value[:max_length]
    
    # Remove null bytes (common injection vector)
    value = value.replace("\x00", "")
    
    # Normalize whitespace
    if not allow_newlines:
        value = " ".join(value.split())
    else:
        # Still normalize spaces but preserve newlines
        lines = value.split("\n")
        value = "\n".join(" ".join(line.split()) for line in lines)
    
    return value.strip()


def sanitize_html(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input by encoding HTML entities to prevent XSS.
    
    This converts:
    - < to &lt;
    - > to &gt;
    - & to &amp;
    - " to &quot;
    - ' to &#x27;
    
    Args:
        value: The input string containing potential HTML
        max_length: Maximum allowed length
    
    Returns:
        HTML-encoded string safe for storage and rendering
    """
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    
    # First sanitize the string
    value = sanitize_string(value, max_length)
    
    # Encode HTML entities
    value = html.escape(value, quote=True)
    
    return value


def validate_email_format(email: str) -> bool:
    """
    Validate email format using a strict regex pattern.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid format, False otherwise
    """
    if not email or not isinstance(email, str):
        return False
    
    # RFC 5322 compliant email regex (simplified)
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) and len(email) <= 254


def validate_uuid(value: str) -> bool:
    """
    Validate that a string is a valid UUID format.
    
    Supports both UUID v4 and Supabase's bigint IDs.
    
    Args:
        value: String to validate
    
    Returns:
        True if valid UUID or numeric ID, False otherwise
    """
    if not value or not isinstance(value, str):
        return False
    
    # UUID v4 pattern
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    if re.match(uuid_pattern, value.lower()):
        return True
    
    # Numeric ID (Supabase bigint)
    if value.isdigit() and len(value) <= 20:
        return True
    
    return False


def validate_query_string(query: str, max_length: int = 200) -> str:
    """
    Validate and sanitize a search query string.
    
    Args:
        query: The search query to validate
        max_length: Maximum allowed length
    
    Returns:
        Sanitized query string
    """
    if not query or not isinstance(query, str):
        return ""
    
    sanitized = query[:max_length]
    
    # Remove SQL-like patterns (character-based)
    char_patterns = [
        r"--",           # SQL comment
        r";",            # SQL statement terminator
        r"'",            # Single quote
        r"\"",           # Double quote
        r"\\",           # Backslash
        r"\x00",         # Null byte
    ]
    
    for pattern in char_patterns:
        sanitized = re.sub(pattern, "", sanitized)
    
    # Remove SQL keywords (word boundary matching)
    sql_keywords = [
        r"\bUNION\b",
        r"\bSELECT\b",
        r"\bINSERT\b",
        r"\bUPDATE\b",
        r"\bDELETE\b",
        r"\bDROP\b",
        r"\bEXEC\b",
        r"\bOR\b",
        r"\bAND\b",
    ]
    
    for keyword in sql_keywords:
        sanitized = re.sub(keyword, "", sanitized, flags=re.IGNORECASE)
    
    # Remove XSS patterns
    xss_patterns = [
        r"<script",
        r"javascript:",
    ]
    
    for pattern in xss_patterns:
        sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)
    
    return sanitize_string(sanitized)


# ==============================================================================
# PATH TRAVERSAL PREVENTION
# ==============================================================================

def safe_path_join(base_dir: str, *paths: str) -> str:
    """
    Safely join paths, preventing directory traversal attacks.
    
    Args:
        base_dir: The base directory (must be absolute)
        *paths: Path components to join
    
    Returns:
        Absolute path that is guaranteed to be within base_dir
    
    Raises:
        ValueError: If resulting path escapes base_dir
    """
    # Normalize the base directory
    base_dir = os.path.abspath(base_dir)
    
    # Join and normalize the full path
    joined = os.path.join(base_dir, *paths)
    full_path = os.path.abspath(joined)
    
    # Verify the result is within the base directory
    if not full_path.startswith(base_dir):
        raise ValueError(f"Path traversal attempt detected: {paths}")
    
    return full_path


def validate_path_within_directory(path: str, allowed_dir: str) -> bool:
    """
    Validate that a path is within an allowed directory.
    
    Args:
        path: Path to validate
        allowed_dir: Directory that path must be within
    
    Returns:
        True if path is safely within allowed_dir, False otherwise
    """
    try:
        # Normalize both paths
        path = os.path.abspath(path)
        allowed_dir = os.path.abspath(allowed_dir)
        
        # Check if path starts with allowed_dir
        return path.startswith(allowed_dir + os.sep) or path == allowed_dir
    except Exception:
        return False


def validate_filename(filename: str) -> bool:
    """
    Validate that a filename is safe (no path components).
    
    Args:
        filename: Filename to validate
    
    Returns:
        True if filename is safe, False otherwise
    """
    if not filename or not isinstance(filename, str):
        return False
    
    # Check for path separators
    if "/" in filename or "\\" in filename:
        return False
    
    # Check for parent directory reference
    if filename in (".", "..") or filename.startswith("."):
        return False
    
    # Check for null bytes
    if "\x00" in filename:
        return False
    
    # Validate characters (alphanumeric, dash, underscore, dot)
    if not re.match(r'^[\w\-. ]+$', filename):
        return False
    
    return len(filename) <= 255


# ==============================================================================
# OUTPUT ENCODING
# ==============================================================================

def encode_for_json(value: str) -> str:
    """
    Encode a string for safe inclusion in JSON responses.
    
    Handles special characters that could cause issues in JSON or XSS.
    
    Args:
        value: String to encode
    
    Returns:
        JSON-safe encoded string
    """
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    
    # HTML encode to prevent XSS when rendered
    return html.escape(value, quote=True)


# ==============================================================================
# IDOR PREVENTION
# ==============================================================================

class SecurityError(Exception):
    """Custom exception for security-related errors."""
    pass


def generate_error_id() -> str:
    """
    Generate a unique error ID for tracking without exposing internals.
    
    Returns:
        16-character hex string
    """
    return secrets.token_hex(8)


# ==============================================================================
# IP AUTO-BAN SYSTEM
# ==============================================================================

class IPBanTracker:
    """
    Automatic IP banning for malicious crawlers and attack attempts.
    
    Tracks violations per IP and bans after threshold is exceeded.
    Bans expire after configurable duration.
    """
    
    def __init__(
        self, 
        violation_threshold: int = 5,
        ban_duration_seconds: int = 3600,  # 1 hour default
        violation_window_seconds: int = 300  # 5 minute window
    ):
        self.threshold = violation_threshold
        self.ban_duration = ban_duration_seconds
        self.violation_window = violation_window_seconds
        
        # {ip: [timestamp, timestamp, ...]}
        self.violations: dict[str, list[float]] = {}
        # {ip: ban_expiry_timestamp}
        self.banned_ips: dict[str, float] = {}

        # Load persisted bans
        self._load_bans()

    def _load_bans(self):
        """Load banned IPs from disk."""
        try:
            if os.path.exists("banned_ips.json"):
                with open("banned_ips.json", "r") as f:
                    self.banned_ips = json.load(f)
        except Exception as e:
            print(f"Error loading bans: {e}")

    def _save_bans(self):
        """Save banned IPs to disk."""
        try:
            with open("banned_ips.json", "w") as f:
                json.dump(self.banned_ips, f)
        except Exception as e:
            print(f"Error saving bans: {e}")
    
    def is_banned(self, ip: str) -> bool:
        """Check if an IP is currently banned."""
        if ip not in self.banned_ips:
            return False
        
        expiry = self.banned_ips[ip]
        now = datetime.now().timestamp()
        
        if now >= expiry:
            # Ban expired, remove it
            del self.banned_ips[ip]
            self._save_bans()
            if ip in self.violations:
                del self.violations[ip]
            return False
        
        return True
    
    def get_ban_remaining(self, ip: str) -> int:
        """Get remaining ban time in seconds."""
        if ip not in self.banned_ips:
            return 0
        
        now = datetime.now().timestamp()
        remaining = self.banned_ips[ip] - now
        return max(0, int(remaining))
    
    def record_violation(self, ip: str, reason: str = "") -> bool:
        """
        Record a security violation for an IP.
        
        Args:
            ip: Client IP address
            reason: Violation reason for logging
        
        Returns:
            True if IP is now banned, False otherwise
        """
        now = datetime.now().timestamp()
        
        # Initialize if new IP
        if ip not in self.violations:
            self.violations[ip] = []
        
        # Add this violation
        self.violations[ip].append(now)
        
        # Clean old violations outside window
        self.violations[ip] = [
            t for t in self.violations[ip]
            if now - t < self.violation_window
        ]
        
        # Check if threshold exceeded
        if len(self.violations[ip]) >= self.threshold:
            self._ban_ip(ip, reason)
            return True
        
        return False
    
    def _ban_ip(self, ip: str, reason: str = "") -> None:
        """Add IP to ban list."""
        now = datetime.now().timestamp()
        self.banned_ips[ip] = now + self.ban_duration
        
        # Log the ban
        log_security_event(
            "IP_BANNED",
            f"Auto-banned for {self.ban_duration}s: {reason}",
            ip
        )
        print(f"🚫 [AUTO-BAN] IP {ip} banned for {self.ban_duration}s: {reason}")
        self._save_bans()
    
    def unban_ip(self, ip: str) -> bool:
        """Manually unban an IP."""
        if ip in self.banned_ips:
            del self.banned_ips[ip]
            self._save_bans()
            if ip in self.violations:
                del self.violations[ip]
            return True
        return False
    
    def get_banned_ips(self) -> list[dict]:
        """Get list of currently banned IPs with expiry times."""
        now = datetime.now().timestamp()
        result = []
        
        for ip, expiry in list(self.banned_ips.items()):
            if now < expiry:
                result.append({
                    "ip": ip,
                    "expires_in": int(expiry - now),
                    "expires_at": datetime.fromtimestamp(expiry).isoformat()
                })
            else:
                # Clean expired
                del self.banned_ips[ip]
                self._save_bans() # Clean up file too
        
        return result
    
    def get_violation_count(self, ip: str) -> int:
        """Get current violation count for an IP."""
        if ip not in self.violations:
            return 0
        
        now = datetime.now().timestamp()
        recent = [t for t in self.violations[ip] if now - t < self.violation_window]
        return len(recent)


# Global IP ban tracker instance
# Bans IMMEDIATELY on first violation, for 1 hour
ip_ban_tracker = IPBanTracker(
    violation_threshold=1,      # Ban on FIRST violation
    ban_duration_seconds=3600,  # 1 hour ban
    violation_window_seconds=300
)


# ==============================================================================
# SECURITY LOGGING
# ==============================================================================

SECURITY_LOG_FILE = "security_events.json"

def log_security_event(
    event_type: str, 
    detail: str, 
    ip: str = "Unknown",
    user_id: Optional[str] = None
) -> None:
    """
    Log a security event to a JSON file for auditing.
    
    Event types:
    - DOS_ATTEMPT: Large payload blocked
    - BOT_SCAN: Malicious path access attempt
    - IDOR_ATTEMPT: Unauthorized resource access
    - PATH_TRAVERSAL: Path manipulation attempt
    - INJECTION_ATTEMPT: SQL/XSS injection detected
    - AUTH_FAILURE: Authentication failure
    - RATE_LIMIT: Rate limit exceeded
    - UNHANDLED_ERROR: Application error occurred
    
    Args:
        event_type: Category of security event
        detail: Descriptive detail of the event
        ip: Client IP address
        user_id: Optional authenticated user ID
    """
    import json
    
    try:
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "detail": detail[:500],  # Limit detail length
            "ip": ip[:45],           # Max IPv6 length
            "user_id": str(user_id)[:50] if user_id else None
        }
        
        with open(SECURITY_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
            
    except Exception as e:
        # Fail silently but print for debugging
        print(f"[SECURITY] Failed to log event: {e}")


# ==============================================================================
# REQUEST VALIDATION PATTERNS
# ==============================================================================

# Patterns to block in paths and queries (expanded from secure_middleware)
BLOCKED_PATH_PATTERNS = [
    # Web vulnerabilities
    ".php", ".env", ".git", ".gitignore", ".htaccess", ".htpasswd",
    "xmlrpc", "wp-admin", "wp-content", "wp-includes", "wp-login",
    # Debug/config exposure
    "xdebug", "config", "backup", ".bak", ".old", ".orig",
    # Database exposure  
    "mysql", "phpmyadmin", "adminer", ".sql", ".db", ".sqlite",
    # Shell/execution
    "shell", "eval", ".cgi", ".sh", ".bash", ".zsh",
    # Archive/binary
    "node_modules", ".zip", ".rar", ".tar", ".gz", ".exe", ".dll",
    # Windows/scripts
    "autodiscover", "powershell", "aspx", "jsp", "jspx",
    # Python-specific RCE patterns
    "__import__", "subprocess", "os.system", "exec(",
    "pickle", "marshal", "code.interact", "pty.spawn",
    # Directory enumeration
    "/..", "..\\", "%2e%2e", "%252e",
]

# Suspicious User-Agent patterns
BLOCKED_USER_AGENTS = [
    "sqlmap", "nikto", "nmap", "masscan", "zgrab",
    "gobuster", "dirbuster", "wfuzz", "ffuf",
    "nuclei", "httpx", "curl/", "python-requests",
]


def is_blocked_path(path: str, query: str = "") -> bool:
    """
    Check if a request path/query contains blocked patterns.
    
    Args:
        path: Request URL path
        query: Request query string
    
    Returns:
        True if blocked pattern found, False otherwise
    """
    combined = (path + query).lower()
    return any(pattern in combined for pattern in BLOCKED_PATH_PATTERNS)


def is_blocked_user_agent(user_agent: str) -> bool:
    """
    Check if User-Agent matches known scanner/bot patterns.
    
    Args:
        user_agent: Request User-Agent header
    
    Returns:
        True if suspicious User-Agent, False otherwise
    """
    if not user_agent:
        return False
    
    ua_lower = user_agent.lower()
    return any(pattern in ua_lower for pattern in BLOCKED_USER_AGENTS)


# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password meets minimum security requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one digit
    
    Args:
        password: Password to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password) > 128:
        return False, "Password too long (max 128 characters)"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, ""


# ==============================================================================
# FILE UPLOAD VALIDATION
# ==============================================================================

# Allowed file extensions for uploads (if needed in future)
ALLOWED_EXTENSIONS = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp"],
    "document": [".pdf", ".doc", ".docx", ".txt", ".csv"],
    "data": [".json", ".xml", ".csv"],
}

# Maximum file sizes in bytes
MAX_FILE_SIZES = {
    "image": 5 * 1024 * 1024,      # 5MB
    "document": 10 * 1024 * 1024,  # 10MB
    "data": 50 * 1024 * 1024,      # 50MB
}


def validate_file_upload(
    filename: str,
    file_size: int,
    file_type: str = "image"
) -> tuple[bool, str]:
    """
    Validate a file upload for security.
    
    Args:
        filename: Original filename
        file_size: Size in bytes
        file_type: Type category ("image", "document", "data")
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not filename:
        return False, "Filename is required"
    
    # Validate filename safety
    if not validate_filename(filename):
        return False, "Invalid filename"
    
    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(file_type, [])
    if ext not in allowed:
        return False, f"File type {ext} not allowed"
    
    # Check size
    max_size = MAX_FILE_SIZES.get(file_type, 5 * 1024 * 1024)
    if file_size > max_size:
        return False, f"File too large (max {max_size // (1024*1024)}MB)"
    
    return True, ""


def generate_safe_filename(original_filename: str) -> str:
    """
    Generate a safe filename for storage.
    
    Preserves the original extension but replaces the name with
    a cryptographically random string.
    
    Args:
        original_filename: The original uploaded filename
    
    Returns:
        Safe filename with random prefix and original extension
    """
    ext = os.path.splitext(original_filename)[1].lower()
    # Validate extension is safe
    if not ext or len(ext) > 10 or not re.match(r'^\.[a-z0-9]+$', ext):
        ext = ".bin"
    
    random_name = secrets.token_hex(16)
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{timestamp}_{random_name}{ext}"


# ==============================================================================
# JSON BODY VALIDATION
# ==============================================================================

def validate_json_body(
    body: dict,
    required_fields: list[str],
    max_field_length: int = 10000
) -> tuple[bool, str]:
    """
    Validate a JSON request body structure.
    
    Args:
        body: Parsed JSON body
        required_fields: List of required field names
        max_field_length: Maximum string field length
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(body, dict):
        return False, "Request body must be a JSON object"
    
    # Check required fields
    for field in required_fields:
        if field not in body:
            return False, f"Missing required field: {field}"
    
    # Check field lengths for string values
    for key, value in body.items():
        if isinstance(value, str) and len(value) > max_field_length:
            return False, f"Field '{key}' exceeds maximum length"
    
    return True, ""


# ==============================================================================
# RATE LIMITING HELPERS
# ==============================================================================

class RateLimitTracker:
    """
    Simple in-memory rate limit tracker.
    
    For production, use Redis-backed rate limiting.
    """
    
    def __init__(self, limit: int = 100, window_seconds: int = 60):
        self.limit = limit
        self.window = window_seconds
        self.requests: dict[str, list[float]] = {}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed under rate limit."""
        now = datetime.now().timestamp()
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old entries
        self.requests[key] = [
            t for t in self.requests[key] 
            if now - t < self.window
        ]
        
        if len(self.requests[key]) >= self.limit:
            return False
        
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests in current window."""
        now = datetime.now().timestamp()
        
        if key not in self.requests:
            return self.limit
        
        recent = [t for t in self.requests[key] if now - t < self.window]
        return max(0, self.limit - len(recent))


# ==============================================================================
# SECURITY RESPONSE HELPERS  
# ==============================================================================

def get_safe_error_response(status_code: int) -> dict:
    """
    Get a safe, generic error response that doesn't leak information.
    
    Args:
        status_code: HTTP status code
    
    Returns:
        Safe error response dict
    """
    messages = {
        400: "Invalid request",
        401: "Authentication required",
        403: "Access denied",
        404: "Resource not found",
        405: "Method not allowed",
        422: "Validation error",
        429: "Too many requests",
        500: "Internal server error",
    }
    
    return {
        "detail": messages.get(status_code, "An error occurred"),
        "error_id": generate_error_id()
    }

