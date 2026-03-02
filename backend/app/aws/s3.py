"""
S3 client for file storage.
"""
from typing import Any, Optional
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)


class S3Client:
    """Client for S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        self._client = None

    @property
    def client(self):
        """Get or create S3 client."""
        if self._client is None:
            kwargs = {
                "region_name": settings.AWS_REGION,
            }
            if settings.AWS_ACCESS_KEY_ID:
                kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
                kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY

            self._client = boto3.client("s3", **kwargs)
        return self._client

    async def upload_file(
        self,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        metadata: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Upload a file to S3.
        
        Args:
            key: The S3 key for the file.
            data: The file data.
            content_type: The MIME type of the file.
            metadata: Optional metadata to attach.
            
        Returns:
            The S3 URI of the uploaded file.
        """
        try:
            extra_args: dict[str, Any] = {"ContentType": content_type}
            if metadata:
                extra_args["Metadata"] = metadata

            self.client.upload_fileobj(
                BytesIO(data),
                settings.S3_BUCKET_NAME,
                key,
                ExtraArgs=extra_args,
            )
            uri = f"s3://{settings.S3_BUCKET_NAME}/{key}"
            logger.info("File uploaded to S3", key=key, uri=uri)
            return uri
        except ClientError as e:
            logger.error("Failed to upload file to S3", error=str(e))
            raise

    async def download_file(self, key: str) -> bytes:
        """
        Download a file from S3.
        
        Args:
            key: The S3 key of the file.
            
        Returns:
            The file data.
        """
        try:
            buffer = BytesIO()
            self.client.download_fileobj(settings.S3_BUCKET_NAME, key, buffer)
            buffer.seek(0)
            logger.info("File downloaded from S3", key=key)
            return buffer.read()
        except ClientError as e:
            logger.error("Failed to download file from S3", error=str(e))
            raise

    async def get_presigned_url(
        self,
        key: str,
        expires_in: int = 3600,
        operation: str = "get_object",
    ) -> str:
        """
        Generate a presigned URL for S3 access.
        
        Args:
            key: The S3 key.
            expires_in: URL expiration time in seconds.
            operation: The S3 operation (get_object or put_object).
            
        Returns:
            The presigned URL.
        """
        try:
            url = self.client.generate_presigned_url(
                operation,
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": key},
                ExpiresIn=expires_in,
            )
            logger.info("Presigned URL generated", key=key, operation=operation)
            return url
        except ClientError as e:
            logger.error("Failed to generate presigned URL", error=str(e))
            raise

    async def delete_file(self, key: str) -> None:
        """
        Delete a file from S3.
        
        Args:
            key: The S3 key of the file to delete.
        """
        try:
            self.client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
            logger.info("File deleted from S3", key=key)
        except ClientError as e:
            logger.error("Failed to delete file from S3", error=str(e))
            raise


# Singleton instance
s3_client = S3Client()
