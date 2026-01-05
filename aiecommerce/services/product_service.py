from aiecommerce.models import ProductMaster


def update_product_sku(product_id: int, new_sku: str) -> ProductMaster:
    """
    Updates the SKU for a given product.

    Args:
        product_id: The ID of the ProductMaster to update.
        new_sku: The new SKU to set.

    Returns:
        The updated ProductMaster instance.
    """
    product = ProductMaster.objects.get(pk=product_id)
    product.sku = new_sku
    product.save(update_fields=["sku"])
    return product
