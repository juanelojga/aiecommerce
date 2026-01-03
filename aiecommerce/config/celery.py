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
        "schedule": crontab(minute=0, hour="8-19", day_of_week="mon-sat"),
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
        "schedule": crontab(minute=10, hour="8-19", day_of_week="mon-sat"),
    },
    "enrich-hourly-mon-sat": {
        "task": "aiecommerce.tasks.periodic.run_enrich_products",
        "schedule": crontab(minute=15, hour="8-19", day_of_week="mon-sat"),
    },
    "ml-eligibility-hourly-mon-sat": {
        "task": "aiecommerce.tasks.periodic.run_ml_eligibility_update",
        "schedule": crontab(minute=20, hour="8-19", day_of_week="mon-sat"),
    },
    "image-fetcher-hourly-mon-sat": {
        "task": "aiecommerce.tasks.periodic.run_image_fetcher",
        "schedule": crontab(minute=25, hour="8-19", day_of_week="mon-sat"),
    },
}
