import os

from celery import Celery

# Set the default Django settings module to 'aiecommerce.settings'
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aiecommerce.settings")

# Use the name of your project package
app = Celery("aiecommerce")

# Load config from Django settings, namespace='CELERY' means keys must start with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
