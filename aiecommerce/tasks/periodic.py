"""Periodic tasks for Celery Beat."""

from celery import shared_task
from django.core.management import call_command


@shared_task
def run_create_ml_test_user():
    """Run the create_ml_test_user management command."""
    call_command("create_ml_test_user")


@shared_task
def run_enrich_mercadolibre_category():
    """Run the enrich_mercadolibre_category management command."""
    call_command("enrich_mercadolibre_category")


@shared_task
def run_enrich_products_content():
    """Run the enrich_products_content management command."""
    call_command("enrich_products_content")


@shared_task
def run_enrich_products_details():
    """Run the enrich_products_details management command."""
    call_command("enrich_products_details")


@shared_task
def run_enrich_products_images():
    """Run the enrich_products_images management command."""
    call_command("enrich_products_images")


@shared_task
def run_enrich_products_specs():
    """Run the enrich_products_specs management command."""
    call_command("enrich_products_specs")


@shared_task
def run_normalize_products():
    """Run the normalize_products management command."""
    call_command("normalize_products")


@shared_task
def run_prune_scrapes():
    """Run the prune_scrapes management command."""
    call_command("prune_scrapes")


@shared_task
def run_publish_ml_product():
    """Run the publish_ml_product management command."""
    call_command("publish_ml_product")


@shared_task
def run_scrape_tecnomega():
    """Run the scrape_tecnomega management command."""
    call_command("scrape_tecnomega")


@shared_task
def run_sync_price_list():
    """Run the sync_price_list management command."""
    call_command("sync_price_list")


@shared_task
def run_update_ml_eligibility():
    """Run the update_ml_eligibility management command."""
    call_command("update_ml_eligibility")


@shared_task
def run_sync_ml_listings():
    """Run the sync_ml_listings management command."""
    call_command("sync_ml_listings")


@shared_task
def run_upscale_scraped_images():
    """Run the sync_ml_listings management command."""
    call_command("upscale_scraped_images")
