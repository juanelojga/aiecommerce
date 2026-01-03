from unittest.mock import patch

from aiecommerce.tasks.periodic import run_image_fetcher, run_ml_eligibility_update


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_ml_eligibility_update(mock_call_command):
    """Verify that the run_ml_eligibility_update task calls the correct management command."""
    run_ml_eligibility_update()
    mock_call_command.assert_called_once_with("update_ml_eligibility")


@patch("aiecommerce.tasks.periodic.call_command")
def test_run_image_fetcher(mock_call_command):
    """Verify that the run_image_fetcher task calls the correct management command."""
    run_image_fetcher()
    mock_call_command.assert_called_once_with("fetch_ml_images")
