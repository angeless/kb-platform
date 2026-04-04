"""S3/MinIO storage client for file uploads."""

import io
import logging

import boto3
from botocore.exceptions import ClientError

from shared_config.settings import Settings

logger = logging.getLogger(__name__)

# Asset types that have a registered parser in ingestion-worker
PARSEABLE_ASSET_TYPES: set[str] = {"text", "pdf", "doc", "document", "image", "audio"}

# Allowed file extensions for upload
ALLOWED_EXTENSIONS: set[str] = {
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg",  # image
    ".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac",           # audio
    ".mp4", ".mov", ".avi", ".mkv", ".webm",                   # video
    ".pdf",                                                      # pdf
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",         # doc
    ".zip", ".tar", ".gz", ".7z", ".rar",                      # zip
    ".txt", ".md", ".csv", ".json", ".xml", ".html", ".htm",   # text
}


def _get_extension(filename: str) -> str:
    """Extract lowercase file extension including the dot."""
    dot_pos = filename.rfind(".")
    if dot_pos == -1:
        return ""
    return filename[dot_pos:].lower()


def is_allowed_file(filename: str) -> bool:
    """Check if file extension is in the whitelist."""
    ext = _get_extension(filename)
    return ext in ALLOWED_EXTENSIONS


def guess_asset_type(filename: str) -> str:
    """Guess asset_type from file extension."""
    ext = _get_extension(filename)
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
    audio_exts = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    zip_exts = {".zip", ".tar", ".gz", ".7z", ".rar"}
    doc_exts = {".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx"}

    if ext in image_exts:
        return "image"
    if ext in audio_exts:
        return "audio"
    if ext in video_exts:
        return "video"
    if ext == ".pdf":
        return "pdf"
    if ext in doc_exts:
        return "doc"
    if ext in zip_exts:
        return "zip"
    return "text"


def create_storage_client(settings: "Settings") -> "StorageClient":
    """Factory: creates StorageClient configured for minio or s3 backend.

    Both backends use the same boto3 client — the difference is only
    in the endpoint_url (MinIO uses explicit endpoint, S3 uses default AWS).
    """
    if settings.storage_backend == "s3" and not settings.s3_endpoint:
        # Pure AWS S3 — use default endpoint (no endpoint_url)
        return StorageClient(settings, use_default_endpoint=True)
    return StorageClient(settings)


class StorageClient:
    """Wrapper around boto3 S3 client for MinIO/S3 operations."""

    def __init__(self, settings: Settings, use_default_endpoint: bool = False) -> None:
        self.bucket = settings.s3_bucket
        kwargs: dict = {
            "aws_access_key_id": settings.s3_access_key,
            "aws_secret_access_key": settings.s3_secret_key,
            "region_name": settings.s3_region,
        }
        if not use_default_endpoint and settings.s3_endpoint:
            kwargs["endpoint_url"] = settings.s3_endpoint
        self.client = boto3.client("s3", **kwargs)

    def ensure_bucket(self) -> None:
        """Create bucket if it does not exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)
            logger.info("Created bucket: %s", self.bucket)

    def upload_file(self, object_key: str, file_content: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload file bytes to S3/MinIO. Returns the object key."""
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=io.BytesIO(file_content),
            ContentLength=len(file_content),
            ContentType=content_type,
        )
        logger.info("Uploaded %s to bucket %s", object_key, self.bucket)
        return object_key

    def download_file(self, object_key: str) -> bytes:
        """Download file bytes from S3/MinIO."""
        try:
            resp = self.client.get_object(Bucket=self.bucket, Key=object_key)
            return resp["Body"].read()
        except ClientError as e:
            logger.error("Failed to download %s from bucket %s: %s", object_key, self.bucket, e)
            raise

    def presign_url(self, object_key: str, expires_in: int = 3600) -> str:
        """Generate a pre-signed URL for downloading a file."""
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error("Failed to generate presign URL for %s: %s", object_key, e)
            raise

    def delete_file(self, object_key: str) -> None:
        """Delete a file from S3/MinIO. Best-effort: logs warning on failure."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info("Deleted %s from bucket %s", object_key, self.bucket)
        except Exception as e:
            logger.warning("Failed to delete %s from bucket %s: %s", object_key, self.bucket, e)
