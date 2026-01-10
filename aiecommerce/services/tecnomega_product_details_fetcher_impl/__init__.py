# aiecommerce/services/scrape_tecnomega_impl/tecnomega_product_details_fetcher_impl/__init__.py
from .detail_fetcher import TecnomegaDetailFetcher
from .detail_parser import TecnomegaDetailParser

__all__ = ["TecnomegaDetailFetcher", "TecnomegaDetailParser"]
