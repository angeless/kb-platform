"""URL fetcher with SSRF protection.

Per design doc section 5.5:
- Only http/https protocols allowed
- Private IP ranges blocked (10.x, 172.16-31.x, 192.168.x, 127.x, ::1)
- Max 3 redirects
- 30 second timeout
"""

import ipaddress
import logging
from urllib.parse import urlparse

import httpx

from shared_errors import AppException, ErrorCode

logger = logging.getLogger(__name__)

_BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

FETCH_TIMEOUT = 30
MAX_REDIRECTS = 3


def validate_url(url: str) -> None:
    """Validate URL protocol and check for SSRF risks.

    Raises AppException if the URL is not safe to fetch.
    """
    parsed = urlparse(url)

    # Protocol check
    if parsed.scheme not in ("http", "https"):
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message=f"不允许的协议: {parsed.scheme}，仅支持 http/https",
        )

    # Hostname check
    hostname = parsed.hostname
    if not hostname:
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message="URL 缺少主机名",
        )

    # Try to parse as IP address and check against blocked ranges
    try:
        ip = ipaddress.ip_address(hostname)
        for network in _BLOCKED_NETWORKS:
            if ip in network:
                raise AppException(
                    error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
                    message="不允许访问内网地址",
                )
    except ValueError:
        # Not an IP literal — it's a domain name, which is fine
        pass


async def fetch_url(url: str) -> tuple[bytes, str]:
    """Fetch URL content with SSRF protection.

    Returns (content_bytes, content_type).
    Raises AppException on validation failure or fetch error.
    """
    validate_url(url)

    try:
        async with httpx.AsyncClient(
            timeout=FETCH_TIMEOUT,
            max_redirects=MAX_REDIRECTS,
            follow_redirects=True,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.TooManyRedirects:
        raise AppException(
            error_code=ErrorCode.SYSTEM_SSRF_BLOCKED,
            message="URL 重定向次数超过限制",
        )
    except httpx.HTTPStatusError as e:
        raise AppException(
            error_code=ErrorCode.ASSET_NOT_FOUND,
            message=f"URL 请求失败: HTTP {e.response.status_code}",
        )
    except httpx.RequestError as e:
        raise AppException(
            error_code=ErrorCode.ASSET_NOT_FOUND,
            message=f"URL 请求失败: {e!s}",
        )

    content_type = response.headers.get("content-type", "text/html")
    return response.content, content_type
