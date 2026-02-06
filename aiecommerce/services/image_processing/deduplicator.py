import logging
from io import BytesIO
from typing import Set

import imagehash
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)


class ImageDeduplicator:
    """Handles visual duplicate detection using perceptual hashing."""

    def __init__(self, threshold: int = 2):
        """Initialize the deduplicator with a similarity threshold.

        Args:
            threshold: Maximum hash difference to consider images as duplicates.
        """
        self.threshold = threshold
        self.seen_hashes: Set[imagehash.ImageHash] = set()

    def clear(self) -> None:
        """Clears the set of seen image hashes."""
        self.seen_hashes.clear()
        logger.info("Cleared seen image hashes.")

    def is_duplicate(self, image_bytes: bytes) -> bool:
        """
        Checks if an image is a visual duplicate of one already seen.

        Args:
            image_bytes: The image content in bytes.

        Returns:
            True if the image is a duplicate, False otherwise.
        """
        try:
            with Image.open(BytesIO(image_bytes)) as img:
                new_hash = imagehash.phash(img)

            for seen_hash in self.seen_hashes:
                distance = new_hash - seen_hash
                if distance <= self.threshold:
                    logger.info(f"Visual duplicate detected with distance {distance}. Skipping.")
                    return True

            self.seen_hashes.add(new_hash)
            return False
        except UnidentifiedImageError:
            logger.error("Failed to decode image for hashing: invalid or corrupt image data.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during image hashing: {e}")
            return False
