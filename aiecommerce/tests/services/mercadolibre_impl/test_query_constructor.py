from unittest.mock import MagicMock, patch

from aiecommerce.models.product import ProductMaster
from aiecommerce.services.mercadolibre_impl.query_constructor import QueryConstructor


class TestQueryConstructor:
    def test_initialization_defaults(self):
        qc = QueryConstructor()
        assert qc.noisy_terms == QueryConstructor.DEFAULT_NOISY_TERMS
        assert qc.query_suffix == QueryConstructor.DEFAULT_QUERY_SUFFIX

    def test_initialization_with_args(self):
        qc = QueryConstructor(noisy_terms="foo", query_suffix="bar")
        assert qc.noisy_terms == "foo"
        assert qc.query_suffix == "bar"

    def test_initialization_with_settings(self):
        with patch("aiecommerce.services.mercadolibre_impl.query_constructor.settings") as mock_settings:
            mock_settings.IMAGE_SEARCH_NOISY_TERMS = "SETTING_NOISY"
            mock_settings.IMAGE_SEARCH_QUERY_SUFFIX = "SETTING_SUFFIX"

            qc = QueryConstructor()
            assert qc.noisy_terms == "SETTING_NOISY"
            assert qc.query_suffix == "SETTING_SUFFIX"

    def test_build_query_with_specs(self):
        product = MagicMock(spec=ProductMaster)
        product.specs = {"brand": "Apple", "model": "iPhone 15", "category": "Smartphone"}
        product.description = "Some description"

        qc = QueryConstructor(query_suffix="white background")
        query = qc.build_query(product)

        assert "Apple" in query
        assert "iPhone 15" in query
        assert "Smartphone" in query
        assert "white background" in query
        # Specs prioritized over description
        assert "Some description" not in query

    def test_build_query_falls_back_to_description(self):
        product = MagicMock(spec=ProductMaster)
        product.specs = {}
        product.description = "Samsung Galaxy S23 Ultra Awesome Phone"

        qc = QueryConstructor(query_suffix="official")
        query = qc.build_query(product)

        assert "Samsung Galaxy S23 Ultra" in query
        assert "official" in query

    def test_build_query_removes_noisy_terms(self):
        product = MagicMock(spec=ProductMaster)
        product.specs = {}
        # 'Precio' and 'Stock' are in DEFAULT_NOISY_TERMS
        product.description = "Laptop Dell Latitude Precio Stock"

        qc = QueryConstructor(query_suffix="image")
        query = qc.build_query(product)

        assert "Precio" not in query
        assert "Stock" not in query
        assert "Laptop Dell Latitude" in query

    def test_build_query_cleans_special_characters(self):
        product = MagicMock(spec=ProductMaster)
        product.specs = {"brand": "Sony", "model": "PS5!", "category": "Console?"}

        qc = QueryConstructor(query_suffix="white-background")
        query = qc.build_query(product)

        assert "PS5" in query
        assert "Console" in query
        assert "!" not in query
        assert "?" not in query
        # final_query = "Sony PS5! Console? white-background"
        # cleaned = re.sub(r"[^\w\s]", "", final_query) -> "Sony PS5 Console whitebackground"
        assert "whitebackground" in query

    def test_build_query_truncation(self):
        long_brand = "B" * 60
        long_model = "M" * 60
        product = MagicMock(spec=ProductMaster)
        product.specs = {"brand": long_brand, "model": long_model}

        qc = QueryConstructor()
        query = qc.build_query(product)

        assert len(query) <= 100
        assert query.startswith(long_brand)
