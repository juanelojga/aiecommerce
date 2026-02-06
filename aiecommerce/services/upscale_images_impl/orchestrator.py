import logging
import time
from typing import Dict

from aiecommerce.services.upscale_images_impl.selector import UpscaleHighResSelector
from aiecommerce.tasks.upscale_images import process_highres_image_task

logger = logging.getLogger(__name__)


class UpscaleHighResOrchestrator:
    """Orchestrates the high-resolution image upscaling process."""

    def __init__(self, selector: UpscaleHighResSelector):
        """Initialize with a selector for candidate products.

        Args:
            selector: The selector to find products needing upscaling.
        """
        self.selector = selector

    def run(
        self,
        product_code: str | None = None,
        dry_run: bool = False,
        delay: float = 0.5,
    ) -> Dict[str, int]:
        """Run the upscaling orchestration process.

        Args:
            product_code: Optional specific product code to process.
            dry_run: If True, simulate without triggering tasks.
            delay: Seconds to wait between processing each product.

        Returns:
            Dictionary with total and processed product counts.
        """
        candidates = self.selector.get_candidates(product_code=product_code)
        total_products = len(candidates)
        processed_products = 0

        for product in candidates:
            logger.info(f"Processing product: {product.code}")
            if not dry_run:
                if product.code:
                    process_highres_image_task.delay(product.code)
                time.sleep(delay)
            processed_products += 1

        logger.info(f"Finished processing {processed_products} of {total_products} products.")
        return {"total": total_products, "processed": processed_products}
