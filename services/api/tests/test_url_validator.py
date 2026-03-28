"""Tests for URL validator SSRF protection."""

import pytest
from app.utils.url_validator import validate_import_url
from shared_errors import AppException


@pytest.mark.asyncio
async def test_valid_public_url():
    """Public HTTPS URLs should pass validation."""
    await validate_import_url("https://example.com/file.pdf")


@pytest.mark.asyncio
async def test_block_private_ip_10():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://10.0.0.1/secret")


@pytest.mark.asyncio
async def test_block_private_ip_172():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://172.16.0.1/secret")


@pytest.mark.asyncio
async def test_block_private_ip_192():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://192.168.1.1/secret")


@pytest.mark.asyncio
async def test_block_localhost():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://127.0.0.1/secret")


@pytest.mark.asyncio
async def test_block_link_local():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://169.254.169.254/latest/meta-data/")


@pytest.mark.asyncio
async def test_block_ipv6_loopback():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://[::1]/secret")


@pytest.mark.asyncio
async def test_block_ftp_protocol():
    with pytest.raises(AppException, match="不允许的协议"):
        await validate_import_url("ftp://evil.com/file")


@pytest.mark.asyncio
async def test_block_file_protocol():
    with pytest.raises(AppException, match="不允许的协议"):
        await validate_import_url("file:///etc/passwd")


@pytest.mark.asyncio
async def test_block_empty_hostname():
    with pytest.raises(AppException, match="缺少主机名"):
        await validate_import_url("http:///path")


@pytest.mark.asyncio
async def test_block_zero_ip():
    with pytest.raises(AppException, match="内网"):
        await validate_import_url("http://0.0.0.0/")
