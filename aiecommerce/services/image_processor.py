"""A service for processing images."""

import logging

import boto3
from django.conf import settings

from .image_processing.analyzer import BackgroundAnalyzer
from .image_processing.deduplicator import ImageDeduplicator
from .image_processing.downloader import ImageDownloader
from .image_processing.storage import StorageGateway
from .image_processing.transformer import ImageTransformer

logger = logging.getLogger(__name__)


class ImageProcessorService:
    """A service for processing images, orchestrating specialized components."""

    def __init__(
        self,
        downloader: ImageDownloader | None = None,
        deduplicator: ImageDeduplicator | None = None,
        analyzer: BackgroundAnalyzer | None = None,
        transformer: ImageTransformer | None = None,
        storage: StorageGateway | None = None,
    ) -> None:
        self.downloader = downloader or ImageDownloader()
        self.deduplicator = deduplicator or ImageDeduplicator()
        self.analyzer = analyzer or BackgroundAnalyzer()
        self.transformer = transformer or ImageTransformer()

        if storage:
            self.storage = storage
        else:
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            self.storage = StorageGateway(
                s3_client=s3_client,
                bucket_name=settings.AWS_STORAGE_BUCKET_NAME,
                region_name=settings.AWS_S3_REGION_NAME,
            )

    def clear_session_hashes(self) -> None:
        """Clears the set of seen image hashes."""
        self.deduplicator.clear()

    def is_duplicate(self, image_bytes: bytes) -> bool:
        """Checks if an image is a visual duplicate."""
        return self.deduplicator.is_duplicate(image_bytes)

    def download_image(self, url: str) -> bytes | None:
        """Downloads an image from a URL."""
        return self.downloader.download(url)

    def process_image(self, image_bytes: bytes, with_background_removal: bool = False) -> bytes | None:
        """Processes an image using the transformer and analyzer."""
        return self.transformer.transform(image_bytes, with_background_removal=with_background_removal, background_analyzer=self.analyzer)

    def upload_to_s3(self, image_bytes: bytes, product_id: int, image_name: str) -> str | None:
        """Uploads an image to storage and returns the public URL."""
        return self.storage.upload(image_bytes, product_id, image_name)
