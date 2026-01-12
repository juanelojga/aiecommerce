from unittest.mock import MagicMock, patch

from aiecommerce.services.mercadolibre_publisher_impl.orchestrator import PublisherOrchestrator


class TestPublisherOrchestrator:
    @patch("aiecommerce.services.mercadolibre_publisher_impl.orchestrator.ProductSelector")
    def test_run_product_found(self, mock_selector):
        # Arrange
        mock_publisher = MagicMock()
        orchestrator = PublisherOrchestrator(publisher=mock_publisher, sandbox=True)

        product_code = "TEST-CODE"
        dry_run = False
        sandbox = True

        mock_product = MagicMock()
        mock_selector.get_product_by_code.return_value = mock_product

        # Act
        orchestrator.run(product_code, dry_run, sandbox)

        # Assert
        mock_selector.get_product_by_code.assert_called_once_with(product_code)
        mock_publisher.publish_product.assert_called_once_with(mock_product, dry_run=dry_run, test=sandbox)

    @patch("aiecommerce.services.mercadolibre_publisher_impl.orchestrator.ProductSelector")
    @patch("aiecommerce.services.mercadolibre_publisher_impl.orchestrator.logger")
    def test_run_product_not_found(self, mock_logger, mock_selector):
        # Arrange
        mock_publisher = MagicMock()
        orchestrator = PublisherOrchestrator(publisher=mock_publisher, sandbox=True)

        product_code = "NON-EXISTENT"
        dry_run = False
        sandbox = True

        mock_selector.get_product_by_code.return_value = None

        # Act
        orchestrator.run(product_code, dry_run, sandbox)

        # Assert
        mock_selector.get_product_by_code.assert_called_once_with(product_code)
        mock_publisher.publish_product.assert_not_called()
        mock_logger.warning.assert_called_once()
        assert f"Product with code '{product_code}' not found" in mock_logger.warning.call_args[0][0]
