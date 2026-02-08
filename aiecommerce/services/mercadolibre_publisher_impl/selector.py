from aiecommerce.models import ProductMaster


class ProductSelector:
    @staticmethod
    def get_product_by_code(code: str) -> ProductMaster | None:
        try:
            return (
                ProductMaster.objects.select_related("mercadolibre_listing")
                .prefetch_related("images")
                .get(
                    code=code,
                    is_for_mercadolibre=True,
                )
            )
        except ProductMaster.DoesNotExist:
            return None
