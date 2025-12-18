import logging
from typing import Dict, List, Optional

from aiecommerce.services.price_list_impl.domain import (
    ParserConfig,
    StandardCategoryResolver,
)
from aiecommerce.services.price_list_impl.exceptions import IngestionError
from aiecommerce.services.price_list_impl.infrastructure import (
    RequestsFileDownloader,
    TecnomegaUrlResolver,
)
from aiecommerce.services.price_list_impl.interfaces import (
    FileDownloader,
    PriceListParser,
    UrlResolver,
)
from aiecommerce.services.price_list_impl.parser import XlsPriceListParser

logger = logging.getLogger(__name__)


class PriceListIngestionService:
    """Orchestrates the price list ingestion process."""

    def __init__(
        self,
        url_resolver: Optional[UrlResolver] = None,
        downloader: Optional[FileDownloader] = None,
        parser: Optional[PriceListParser] = None,
    ):
        self.url_resolver = url_resolver or TecnomegaUrlResolver()
        self.downloader = downloader or RequestsFileDownloader()
        self.parser = parser or XlsPriceListParser(
            config=ParserConfig(),
            category_resolver=StandardCategoryResolver(),
        )

    def process(self, base_url: str) -> List[Dict]:
        """
        Resolves the download URL, downloads the file, parses it, and returns the data.

        Args:
            base_url: The base URL to start the process from.

        Returns:
            A list of dictionaries representing the parsed product data,
            or an empty list if an error occurs.
        """
        try:
            logger.info("Starting price list ingestion for base_url: %s", base_url)

            resolved_url = self.url_resolver.resolve(base_url)
            logger.info("Resolved price list URL to: %s", resolved_url)

            file_content = self.downloader.download(resolved_url)
            logger.info("Successfully downloaded file from %s", resolved_url)

            parsed_data = self.parser.parse(file_content)
            logger.info("Successfully parsed %d items from the price list.", len(parsed_data))

            return parsed_data

        except IngestionError as e:
            logger.error(
                "An error occurred during price list ingestion: %s",
                e,
                exc_info=True,
            )
            return []
