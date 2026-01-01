"""
Security Unit Tests
===================
Test suite for LeadMaps security module functions.

Run with: python -m pytest test_security.py -v
"""

import pytest
import os
import tempfile


class TestInputSanitization:
    """Tests for input validation and sanitization functions"""
    
    def test_sanitize_string_basic(self):
        from security import sanitize_string
        
        # Basic string passes through
        assert sanitize_string("Hello World") == "Hello World"
        
        # Whitespace is normalized
        assert sanitize_string("  Hello   World  ") == "Hello World"
        
        # Null bytes are removed
        assert sanitize_string("Hello\x00World") == "HelloWorld"
        
        # Length is limited
        assert len(sanitize_string("A" * 2000, max_length=100)) == 100
    
    def test_sanitize_html_xss_prevention(self):
        from security import sanitize_html
        
        # Script tags are encoded
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result
        
        # Event handlers: quotes are escaped (prevents attribute injection)
        result = sanitize_html('<img onerror="alert(1)">')
        assert '"' not in result  # Quotes are escaped
        assert '&quot;' in result or '&#x27;' in result
        
        # Normal text with special chars is properly escaped
        assert sanitize_html("John's Cafe & Bar") == "John&#x27;s Cafe &amp; Bar"
    
    def test_validate_email_format(self):
        from security import validate_email_format
        
        # Valid emails
        assert validate_email_format("user@example.com") is True
        assert validate_email_format("user.name@subdomain.example.co.id") is True
        
        # Invalid emails
        assert validate_email_format("") is False
        assert validate_email_format("notanemail") is False
        assert validate_email_format("@nodomain.com") is False
        assert validate_email_format("user@") is False
    
    def test_validate_uuid(self):
        from security import validate_uuid
        
        # Valid UUID v4
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        
        # Valid numeric ID (Supabase bigint)
        assert validate_uuid("12345") is True
        
        # Invalid formats
        assert validate_uuid("") is False
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("../etc/passwd") is False
        assert validate_uuid("1; DROP TABLE users;--") is False
    
    def test_validate_query_string(self):
        from security import validate_query_string
        
        # Normal queries pass
        result = validate_query_string("coffee shop jakarta")
        assert result == "coffee shop jakarta"
        
        # SQL injection patterns removed (word boundaries)
        result = validate_query_string("coffee' OR 1=1--")
        assert "'" not in result  # Single quotes removed
        assert "--" not in result  # SQL comments removed
        assert " OR " not in result  # OR keyword removed (word boundary)
        
        # XSS patterns removed
        result = validate_query_string("<script>alert(1)</script>")
        assert "<script" not in result


class TestPathTraversalPrevention:
    """Tests for path traversal prevention functions"""
    
    def test_safe_path_join_basic(self):
        from security import safe_path_join
        
        base = tempfile.gettempdir()
        
        # Normal path works
        result = safe_path_join(base, "file.txt")
        assert result.startswith(base)
        assert result.endswith("file.txt")
    
    def test_safe_path_join_blocks_traversal(self):
        from security import safe_path_join
        
        base = tempfile.gettempdir()
        
        # Path traversal raises ValueError
        with pytest.raises(ValueError, match="Path traversal"):
            safe_path_join(base, "..", "..", "etc", "passwd")
        
        with pytest.raises(ValueError, match="Path traversal"):
            safe_path_join(base, "subdir", "../../../etc/passwd")
    
    def test_validate_path_within_directory(self):
        from security import validate_path_within_directory
        
        base = tempfile.gettempdir()
        
        # Valid path within directory
        valid_path = os.path.join(base, "subdir", "file.txt")
        assert validate_path_within_directory(valid_path, base) is True
        
        # Path outside directory
        assert validate_path_within_directory("/etc/passwd", base) is False
    
    def test_validate_filename(self):
        from security import validate_filename
        
        # Valid filenames
        assert validate_filename("document.pdf") is True
        assert validate_filename("my-file_v2.txt") is True
        
        # Invalid: contains path separator
        assert validate_filename("../file.txt") is False
        assert validate_filename("folder/file.txt") is False
        
        # Invalid: hidden or special
        assert validate_filename(".") is False
        assert validate_filename("..") is False
        assert validate_filename(".hidden") is False


class TestBlockedPatterns:
    """Tests for malicious pattern detection"""
    
    def test_is_blocked_path(self):
        from security import is_blocked_path
        
        # Blocked paths
        assert is_blocked_path("/admin/.env") is True
        assert is_blocked_path("/wp-admin/login.php") is True
        assert is_blocked_path("/config.php") is True
        assert is_blocked_path("/.git/config") is True
        
        # Allowed paths
        assert is_blocked_path("/api/contacts") is False
        assert is_blocked_path("/auth/login") is False
    
    def test_is_blocked_user_agent(self):
        from security import is_blocked_user_agent
        
        # Blocked scanners
        assert is_blocked_user_agent("sqlmap/1.0") is True
        assert is_blocked_user_agent("Nikto/2.1.5") is True
        
        # Allowed browsers
        assert is_blocked_user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)") is False
        assert is_blocked_user_agent("") is False


class TestPasswordValidation:
    """Tests for password strength validation"""
    
    def test_validate_password_strength(self):
        from security import validate_password_strength
        
        # Valid passwords
        is_valid, msg = validate_password_strength("Password123")
        assert is_valid is True
        
        # Too short
        is_valid, msg = validate_password_strength("Pass1")
        assert is_valid is False
        assert "8 characters" in msg
        
        # Missing uppercase
        is_valid, msg = validate_password_strength("password123")
        assert is_valid is False
        assert "uppercase" in msg
        
        # Missing lowercase
        is_valid, msg = validate_password_strength("PASSWORD123")
        assert is_valid is False
        assert "lowercase" in msg
        
        # Missing number
        is_valid, msg = validate_password_strength("PasswordABC")
        assert is_valid is False
        assert "number" in msg


class TestSecurityLogging:
    """Tests for security event logging"""
    
    def test_log_security_event(self):
        from security import log_security_event, SECURITY_LOG_FILE
        import json
        
        # Log an event
        log_security_event("TEST_EVENT", "Test detail", "127.0.0.1", "user123")
        
        # Verify it was written
        assert os.path.exists(SECURITY_LOG_FILE)
        
        with open(SECURITY_LOG_FILE, "r") as f:
            lines = f.readlines()
            last_event = json.loads(lines[-1])
            assert last_event["event_type"] == "TEST_EVENT"
            assert last_event["ip"] == "127.0.0.1"


class TestAttackPatterns:
    """
    Tests for common attack patterns.
    Validates that attacks fail safely with appropriate responses.
    """
    
    def test_sql_injection_payloads(self):
        """Test that SQL injection payloads are sanitized"""
        from security import validate_query_string, sanitize_html
        
        payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users;--",
            "1 UNION SELECT * FROM users",
            "admin'--",
            "1; DELETE FROM contacts WHERE 1=1",
            "' OR 1=1 --",
            "1' AND '1'='1",
        ]
        
        for payload in payloads:
            result = validate_query_string(payload)
            # Should not contain SQL keywords or dangerous chars
            assert "'" not in result, f"Single quote in: {result}"
            assert "--" not in result, f"SQL comment in: {result}"
            assert ";" not in result, f"Semicolon in: {result}"
    
    def test_xss_payloads(self):
        """Test that XSS payloads are safely encoded"""
        from security import sanitize_html
        
        payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<body onload=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "'\"><script>alert('XSS')</script>",
            "<iframe src='javascript:alert(1)'>",
        ]
        
        for payload in payloads:
            result = sanitize_html(payload)
            # Should not contain unescaped HTML
            assert "<script>" not in result
            assert "<iframe" not in result
            assert "<svg" not in result
            # Dangerous chars should be escaped
            assert "<" not in result or "&lt;" in result
    
    def test_path_traversal_payloads(self):
        """Test that path traversal attempts are blocked"""
        from security import safe_path_join, validate_filename
        import tempfile
        
        base = tempfile.gettempdir()
        
        payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2fetc/passwd",
            "..%252f..%252f..%252fetc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\SAM",
        ]
        
        for payload in payloads:
            # safe_path_join should raise ValueError
            try:
                result = safe_path_join(base, payload)
                # If it didn't raise, verify it's still within base
                assert result.startswith(base)
            except ValueError:
                pass  # Expected for traversal attempts
        
        # Filenames with path components should be invalid
        assert validate_filename("../file.txt") is False
        assert validate_filename("..\\file.txt") is False
        assert validate_filename("/etc/passwd") is False
    
    def test_rce_patterns_blocked(self):
        """Test that RCE patterns are blocked in paths"""
        from security import is_blocked_path
        
        payloads = [
            "/__import__('os').system('id')",
            "/exec(input())",
            "/pickle.loads(data)",
            "/subprocess.run(['id'])",
            "/os.system('rm -rf /')",
            "/eval(user_input)",
        ]
        
        for payload in payloads:
            assert is_blocked_path(payload) is True, f"Should block: {payload}"
    
    def test_idor_uuid_validation(self):
        """Test that IDOR attempts via malformed IDs are rejected"""
        from security import validate_uuid
        
        # Valid IDs
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert validate_uuid("12345") is True
        
        # Invalid/malicious IDs
        invalid_ids = [
            "../../../etc/passwd",
            "1 OR 1=1",
            "<script>alert(1)</script>",
            "12345; DROP TABLE users;--",
            "-1",
            "0x1",
            "null",
            "undefined",
            "",
            "../../1234",
        ]
        
        for invalid_id in invalid_ids:
            assert validate_uuid(invalid_id) is False, f"Should reject: {invalid_id}"


class TestFileUploadSecurity:
    """Tests for file upload validation"""
    
    def test_validate_file_upload(self):
        from security import validate_file_upload
        
        # Valid upload
        is_valid, msg = validate_file_upload("photo.jpg", 1024 * 1024, "image")
        assert is_valid is True
        
        # Invalid extension
        is_valid, msg = validate_file_upload("script.php", 1024, "image")
        assert is_valid is False
        assert "not allowed" in msg
        
        # File too large
        is_valid, msg = validate_file_upload("photo.jpg", 100 * 1024 * 1024, "image")
        assert is_valid is False
        assert "too large" in msg
    
    def test_generate_safe_filename(self):
        from security import generate_safe_filename
        
        # Generates safe random name
        result = generate_safe_filename("malicious<script>.jpg")
        assert "<script>" not in result
        assert result.endswith(".jpg")
        assert len(result) > 20  # Random component
        
        # Invalid extension gets .bin
        result = generate_safe_filename("file")
        assert result.endswith(".bin")


class TestJSONValidation:
    """Tests for JSON body validation"""
    
    def test_validate_json_body(self):
        from security import validate_json_body
        
        # Valid body
        is_valid, msg = validate_json_body(
            {"email": "test@test.com", "password": "secret"},
            ["email", "password"]
        )
        assert is_valid is True
        
        # Missing field
        is_valid, msg = validate_json_body(
            {"email": "test@test.com"},
            ["email", "password"]
        )
        assert is_valid is False
        assert "Missing" in msg
        
        # Field too long
        is_valid, msg = validate_json_body(
            {"data": "A" * 20000},
            [],
            max_field_length=10000
        )
        assert is_valid is False
        assert "exceeds" in msg
