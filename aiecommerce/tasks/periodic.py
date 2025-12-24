"""Periodic tasks for Celery Beat."""

from celery import shared_task
from django.core.management import call_command


@shared_task
def run_scrape_tecnomega():
    """Run the scrape_tecnomega management command."""
    call_command("scrape_tecnomega")


@shared_task
def run_sync_price_list():
    """Run the sync_price_list management command."""
    call_command("sync_price_list")


@shared_task
def run_prune_scrapes():
    """Run the prune_scrapes management command."""
    call_command("prune_scrapes")


@shared_task
def run_normalize_products():
    """Run the normalize_products management command."""
    call_command("normalize_products")
