"""Unit tests for URL fetcher SSRF protection (T-37-06)."""

import pytest

from shared_errors import AppException

from app.utils.url_fetcher import validate_url


class TestValidateUrlSsrf:
    """Tests for SSRF IP blocking in validate_url."""

    def test_blocks_zero_address(self):
        """0.0.0.0 should be blocked (T-37-06)."""
        with pytest.raises(AppException) as exc:
            validate_url("http://0.0.0.0:8080/file.txt")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_ipv6_zero_address(self):
        """:: (IPv6 unspecified) should be blocked (T-37-06)."""
        with pytest.raises(AppException) as exc:
            validate_url("http://[::]:8080/file.txt")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_loopback(self):
        """127.0.0.1 should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("http://127.0.0.1/file")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_private_10(self):
        """10.x.x.x should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("http://10.0.0.1/file")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_private_172(self):
        """172.16.x.x should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("http://172.16.0.1/file")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_private_192(self):
        """192.168.x.x should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("http://192.168.1.1/file")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_ipv6_loopback(self):
        """::1 should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("http://[::1]/file")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_allows_public_url(self):
        """Public URLs should pass validation."""
        validate_url("https://example.com/file.txt")

    def test_allows_public_ip(self):
        """Public IP addresses should pass validation."""
        validate_url("http://8.8.8.8/file.txt")

    def test_blocks_ftp_protocol(self):
        """Non-http/https protocols should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("ftp://evil.com/file")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"

    def test_blocks_missing_hostname(self):
        """URLs without hostname should be blocked."""
        with pytest.raises(AppException) as exc:
            validate_url("http:///path")
        assert exc.value.error_code.value == "SYSTEM_SSRF_BLOCKED"
