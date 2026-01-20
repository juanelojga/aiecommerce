import logging
import time
from typing import Dict

from aiecommerce.services.upscale_images_impl.selector import UpscaleHighResSelector
from aiecommerce.tasks.upscale_images import process_highres_image_task

logger = logging.getLogger(__name__)


class UpscaleHighResOrchestrator:
    def __init__(self, selector: UpscaleHighResSelector):
        self.selector = selector

    def run(
        self,
        product_code: str | None = None,
        dry_run: bool = False,
        delay: float = 0.5,
    ) -> Dict[str, int]:
        logger.info(f"Starting upscale high-res orchestrator with product_code={product_code}, dry_run={dry_run}, delay={delay}")
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
