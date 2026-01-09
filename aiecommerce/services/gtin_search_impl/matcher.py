from rapidfuzz import fuzz


class ProductMatcher:
    """
    A utility service to calculate the confidence score of a product name match against a set of specifications.
    """

    @staticmethod
    def calculate_confidence(api_product_name: str, specs: dict[str, str]) -> float:
        """
        Calculates a confidence score based on how well the product name matches key specs.

        This method constructs a 'search target string' from core specifications (CPU, RAM, storage)
        and uses a token set ratio to compare it against the provided product name. This handles
        potential differences in word order.

        Args:
            api_product_name: The product name from the API.
            specs: A dictionary of product specifications.

        Returns:
            A confidence score between 0.0 and 1.0.
        """
        core_specs = [
            specs.get("cpu", ""),
            specs.get("ram", ""),
            specs.get("storage", ""),
        ]
        search_target = " ".join(filter(None, core_specs))

        if not search_target:
            return 0.0

        # token_set_ratio is effective for matching strings with different word order
        score = fuzz.token_set_ratio(api_product_name, search_target)

        return score / 100.0
