"""URL validation with DNS resolution SSRF protection.

Extends the IP-literal checks in url_fetcher.py with DNS resolution
to prevent DNS rebinding attacks (e.g., evil.com resolving to 169.254.169.254).
"""

import ipaddress
import socket
from urllib.parse import urlparse

from shared_errors import AppException, ErrorCode

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("0.0.0.0/32"),
    ipaddress.ip_network("::/128"),
]


def _is_private_ip(ip_str: str) -> bool:
    """Check if an IP address falls within blocked private/internal ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in _BLOCKED_NETWORKS)
    except ValueError:
        return False


def validate_import_url(url: str) -> None:
    """Validate a URL for safe external fetching, including DNS resolution check.

    Raises AppException if the URL points to internal/private infrastructure.
    """
    parsed = urlparse(url)

    # Protocol check
    if parsed.scheme not in ("http", "https"):
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message=f"不允许的协议: {parsed.scheme}，仅支持 http/https",
        )

    hostname = parsed.hostname
    if not hostname:
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message="URL 缺少主机名",
        )

    # Check IP literal
    if _is_private_ip(hostname):
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message="不允许访问内网地址",
        )

    # DNS resolution check — resolve hostname and verify all IPs are public
    try:
        addrinfo = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _type, _proto, _canonname, sockaddr in addrinfo:
            resolved_ip = sockaddr[0]
            if _is_private_ip(resolved_ip):
                raise AppException(
                    error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
                    message="不允许访问内网地址",
                )
    except socket.gaierror:
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message="无法解析域名",
        )
