import logging
from typing import Dict, Optional

from aiecommerce.models.product import ProductRawWeb
from aiecommerce.services.scrape_tecnomega_impl.mapper import ProductMapper


class TestToEntity:
    def test_maps_all_fields_and_defaults_image_url(self):
        mapper = ProductMapper()

        raw: Dict[str, Optional[str]] = {
            "distributor_code": "SKU123",
            "raw_description": "Laptop 8GB RAM",
            "stock_principal": "Si",
            "stock_colon": "No",
            "stock_sur": "Si",
            "stock_gye_norte": "No",
            "stock_gye_sur": "Si",
            # image_url intentionally omitted to test default
        }

        entity = mapper.to_entity(raw, scrape_session_id="session-1", search_term="laptops")

        assert isinstance(entity, ProductRawWeb)
        # Field mappings
        assert entity.distributor_code == "SKU123"
        assert entity.raw_description == "Laptop 8GB RAM"
        assert entity.stock_principal == "Si"
        assert entity.stock_colon == "No"
        assert entity.stock_sur == "Si"
        assert entity.stock_gye_norte == "No"
        assert entity.stock_gye_sur == "Si"
        # Default for missing image_url
        assert entity.image_url == ""
        # Metadata
        assert entity.scrape_session_id == "session-1"
        assert entity.search_term == "laptops"


class TestMapToModels:
    def test_returns_empty_list_when_no_raw_products(self):
        mapper = ProductMapper()
        result = mapper.map_to_models([], scrape_session_id="s1", search_term="monitors")
        assert result == []

    def test_maps_multiple_products_and_logs_info(self, caplog):
        mapper = ProductMapper()
        raw_products: list[dict[str, Optional[str]]] = [
            {
                "distributor_code": "A1",
                "raw_description": "Item A",
                "stock_principal": "Si",
                "stock_colon": "No",
                "stock_sur": "Si",
                "stock_gye_norte": "No",
                "stock_gye_sur": "Si",
                "image_url": "https://img/a.jpg",
            },
            {
                "distributor_code": "B2",
                "raw_description": "Item B",
                "stock_principal": "No",
                "stock_colon": "Si",
                "stock_sur": "No",
                "stock_gye_norte": "Si",
                "stock_gye_sur": "No",
                # image_url omitted -> default ""
            },
        ]

        with caplog.at_level(logging.INFO):
            models = mapper.map_to_models(raw_products, scrape_session_id="sess-2", search_term="keyboards")

        # Return types and length
        assert len(models) == 2
        assert all(isinstance(m, ProductRawWeb) for m in models)

        # First product
        p1 = models[0]
        assert p1.distributor_code == "A1"
        assert p1.raw_description == "Item A"
        assert p1.image_url == "https://img/a.jpg"
        assert p1.scrape_session_id == "sess-2"
        assert p1.search_term == "keyboards"

        # Second product (image_url default)
        p2 = models[1]
        assert p2.distributor_code == "B2"
        assert p2.raw_description == "Item B"
        assert p2.image_url == ""
        assert p2.scrape_session_id == "sess-2"
        assert p2.search_term == "keyboards"

        # Logging assertions
        messages = [rec.getMessage() for rec in caplog.records if rec.levelno == logging.INFO]
        assert any("Mapping 2 raw products" in m and "keyboards" in m for m in messages)
        assert any("Successfully mapped 2 products" in m for m in messages)
