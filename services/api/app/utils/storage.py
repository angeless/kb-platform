"""S3/MinIO storage client for file uploads."""

import io
import logging

import boto3
from botocore.exceptions import ClientError

from shared_config.settings import Settings

logger = logging.getLogger(__name__)

# Asset types that have a registered parser in ingestion-worker
PARSEABLE_ASSET_TYPES: set[str] = {"text", "pdf", "doc", "document"}

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


class StorageClient:
    """Wrapper around boto3 S3 client for MinIO/S3 operations."""

    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            region_name=settings.s3_region,
        )

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

    def delete_file(self, object_key: str) -> None:
        """Delete a file from S3/MinIO. Best-effort: logs warning on failure."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info("Deleted %s from bucket %s", object_key, self.bucket)
        except Exception as e:
            logger.warning("Failed to delete %s from bucket %s: %s", object_key, self.bucket, e)
