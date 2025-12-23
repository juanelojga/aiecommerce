import logging
import time

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def test_celery_worker():
    """
    A simple task to verify that the Celery worker is running
    and can connect to the Redis broker.
    """
    logger.info("Test task received. Waiting 3 seconds...")
    time.sleep(3)
    logger.info("Test task completed successfully.")
    return "Worker is alive and processing!"
