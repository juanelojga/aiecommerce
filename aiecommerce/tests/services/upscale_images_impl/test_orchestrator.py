from unittest.mock import MagicMock, patch

import pytest

from aiecommerce.services.upscale_images_impl.orchestrator import UpscaleHighResOrchestrator


class TestUpscaleHighResOrchestrator:
    @pytest.fixture
    def mock_selector(self):
        return MagicMock()

    @pytest.fixture
    def orchestrator(self, mock_selector):
        return UpscaleHighResOrchestrator(selector=mock_selector)

    @pytest.fixture
    def mock_products(self):
        p1 = MagicMock()
        p1.code = "PROD1"
        p2 = MagicMock()
        p2.code = "PROD2"
        return [p1, p2]

    def test_run_dry_run_true(self, orchestrator, mock_selector, mock_products):
        mock_selector.get_candidates.return_value = mock_products

        with patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task") as mock_task, patch("aiecommerce.services.upscale_images_impl.orchestrator.time.sleep") as mock_sleep:
            result = orchestrator.run(dry_run=True)

            assert result == {"total": 2, "processed": 2}
            mock_selector.get_candidates.assert_called_once_with(product_code=None)
            mock_task.delay.assert_not_called()
            mock_sleep.assert_not_called()

    def test_run_dry_run_false(self, orchestrator, mock_selector, mock_products):
        mock_selector.get_candidates.return_value = mock_products

        with patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task") as mock_task, patch("aiecommerce.services.upscale_images_impl.orchestrator.time.sleep") as mock_sleep:
            delay_val = 0.1
            result = orchestrator.run(dry_run=False, delay=delay_val)

            assert result == {"total": 2, "processed": 2}
            assert mock_task.delay.call_count == 2
            mock_task.delay.assert_any_call("PROD1")
            mock_task.delay.assert_any_call("PROD2")
            assert mock_sleep.call_count == 2
            mock_sleep.assert_called_with(delay_val)

    def test_run_with_product_code(self, orchestrator, mock_selector):
        p1 = MagicMock()
        p1.code = "PROD1"
        mock_selector.get_candidates.return_value = [p1]

        with patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task") as mock_task, patch("aiecommerce.services.upscale_images_impl.orchestrator.time.sleep"):
            result = orchestrator.run(product_code="PROD1", dry_run=False)

            assert result == {"total": 1, "processed": 1}
            mock_selector.get_candidates.assert_called_once_with(product_code="PROD1")
            mock_task.delay.assert_called_once_with("PROD1")

    def test_run_empty_candidates(self, orchestrator, mock_selector):
        mock_selector.get_candidates.return_value = []

        with patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task") as mock_task:
            result = orchestrator.run()

            assert result == {"total": 0, "processed": 0}
            mock_task.delay.assert_not_called()

    def test_run_product_without_code_skips_task(self, orchestrator, mock_selector):
        p_no_code = MagicMock()
        p_no_code.code = None
        mock_selector.get_candidates.return_value = [p_no_code]

        with patch("aiecommerce.services.upscale_images_impl.orchestrator.process_highres_image_task") as mock_task, patch("aiecommerce.services.upscale_images_impl.orchestrator.time.sleep") as mock_sleep:
            result = orchestrator.run(dry_run=False)

            assert result == {"total": 1, "processed": 1}
            mock_task.delay.assert_not_called()
            # It still sleeps because time.sleep(delay) is outside the if product.code: block but inside the if not dry_run block
            assert mock_sleep.called
