import os

from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module to 'aiecommerce.settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aiecommerce.settings")

# Use the name of your project package
app = Celery("aiecommerce")

# Load config from Django settings, namespace='CELERY' means keys must start with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()


# Celery Beat Settings
app.conf.beat_schedule = {
    "scrape-hourly-mon-sat": {
        "task": "aiecommerce.tasks.periodic.run_scrape_tecnomega",
        "schedule": crontab(minute=1, hour="8-18/2", day_of_week="mon-sat"),
    },
    "sync-price-list-daily": {
        "task": "aiecommerce.tasks.periodic.run_sync_price_list",
        "schedule": crontab(minute=0, hour=10),
    },
    "prune-scrapes-daily": {
        "task": "aiecommerce.tasks.periodic.run_prune_scrapes",
        "schedule": crontab(minute=0, hour=0),
    },
    "normalize-hourly-mon-sat": {
        "task": "aiecommerce.tasks.periodic.run_normalize_products",
        "schedule": crontab(minute=10, hour="8-18/2", day_of_week="mon-sat"),
    },
    "run_sync_ml_listings-hourly": {
        "task": "aiecommerce.tasks.periodic.run_sync_ml_listings",
        "schedule": crontab(minute=2, hour="8-18/2", day_of_week="mon-sat"),
    },
    "enrich-products-details-hourly": {
        "task": "aiecommerce.tasks.periodic.run_enrich_products_details",
        "schedule": crontab(minute=15, hour="8-18/2", day_of_week="mon-sat"),
    },
    "enrich-products-content-hourly": {
        "task": "aiecommerce.tasks.periodic.run_enrich_products_content",
        "schedule": crontab(minute=20, hour="8-18/2", day_of_week="mon-sat"),
    },
    "enrich-products-images-hourly": {
        "task": "aiecommerce.tasks.periodic.run_enrich_products_images",
        "schedule": crontab(minute=25, hour="8-18/2", day_of_week="mon-sat"),
    },
    "enrich-products-specs-hourly": {
        "task": "aiecommerce.tasks.periodic.run_enrich_products_specs",
        "schedule": crontab(minute=30, hour="8-18/2", day_of_week="mon-sat"),
    },
}
