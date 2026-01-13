"""AIEcommerce Test Suite."""

from aiecommerce.config.celery import app as celery_app

# This setting makes Celery tasks execute synchronously in tests.
# This is useful for testing task logic without a running Celery worker.
celery_app.conf.update(task_always_eager=True)
