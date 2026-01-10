from typing import Any, List

import instructor

from aiecommerce.models.product import ProductMaster


class MercadolibreAIAttributeFiller:
    def __init__(self, client: instructor.Instructor) -> None:
        self.client = client

    def fill_and_validate(
        self,
        product: ProductMaster,
        attributes: List[dict],
    ) -> Any:
        return {}
