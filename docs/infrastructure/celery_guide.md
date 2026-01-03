# Celery Asynchronous Task Processing Guide

This guide provides a comprehensive overview of the asynchronous task processing system in the `aiecommerce` project, which uses Celery with Redis as a message broker.

## 1. Architecture Overview

Our asynchronous architecture consists of four main components that work together to handle background jobs efficiently.

-   **Django Producer**: The main Django web application. When a background task needs to be executed (e.g., processing an uploaded file, sending an email), the application "produces" a task by sending a message to the broker.

-   **Redis Broker**: We use Redis as our message broker. It's a high-performance in-memory data store that temporarily stores task messages in a queue. It acts as the central hub, decoupling the Django application from the workers.

-   **Celery Workers**: These are standalone processes that are constantly connected to the broker. They "consume" tasks from the queue as they become available. Each worker executes one task at a time, allowing the main Django application to remain responsive to user requests. We can run multiple workers to process tasks in parallel.

-   **Celery Beat Scheduler**: This is a special-purpose process responsible for scheduling and dispatching periodic tasks based on a predefined schedule. For example, it triggers our hourly data processing pipeline.

The flow is as follows:
1.  Django sends a task message to Redis.
2.  Redis adds the message to a specific queue.
3.  A Celery worker retrieves the message from the queue.
4.  The worker executes the corresponding task.
5.  Celery Beat runs separately to trigger scheduled tasks according to the configured times.

## 2. Configuration

The core Celery configuration is centralized in two key files.

### Celery Application (`aiecommerce/config/celery.py`)

This file initializes the Celery application instance. It sets the default Django settings module, configures Celery to use settings with the `CELERY_` prefix, and automatically discovers tasks defined in the installed Django apps (in files named `tasks.py`).

```python
# aiecommerce/config/celery.py
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aiecommerce.settings")

app = Celery("aiecommerce")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()
```

### Django Settings (`settings.py`)

The main `settings.py` file contains the broker and backend configuration, along with other operational settings.

```python
# settings.py

# Celery Configuration
# Default to local Redis (matches your docker-compose redis service).
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=CELERY_BROKER_URL)
CELERY_TIMEZONE = "America/Guayaquil"
CELERY_ENABLE_UTC = True
```
*   `CELERY_BROKER_URL`: URL for the Redis message broker, read from environment variables.
*   `CELERY_RESULT_BACKEND`: URL for the Redis database used to store task results.
*   `CELERY_TIMEZONE`: The timezone used for scheduling tasks.
*   `CELERY_ENABLE_UTC`: Set to `True` to use UTC internally.

## 3. Local Development

To run the asynchronous system locally, you need to start three separate services: the broker, a worker, and the scheduler.

### Start the Redis Broker

We use Docker to manage the Redis instance.

```bash
docker-compose up -d redis
```

### Start the Celery Worker

The worker process connects to Redis and waits for tasks. Open a new terminal and run:

```bash
celery -A aiecommerce worker --loglevel=info
```

### Start the Celery Beat Scheduler

The beat scheduler triggers periodic tasks. Open another terminal and run:

```bash
celery -A aiecommerce beat --loglevel=info
```

## 4. Periodic Task Schedule

The `aiecommerce` project runs a data processing pipeline at various intervals to keep product information up-to-date. This schedule is defined in `aiecommerce/config/celery.py` and managed by Celery Beat.

The main hourly pipeline runs from 8 AM to 7 PM, Monday through Saturday.

| Task                          | Schedule                                   | Description                                            |
|-------------------------------|--------------------------------------------|--------------------------------------------------------|
| `run_scrape_tecnomega`        | Hourly at minute :00 (8am-7pm, Mon-Sat)    | Kicks off the web scraping process for new raw data.   |
| `run_normalize_products`      | Hourly at minute :10 (8am-7pm, Mon-Sat)    | Cleans and standardizes the scraped data.              |
| `run_enrich_products`         | Hourly at minute :15 (8am-7pm, Mon-Sat)    | Augments product data from external and internal APIs. |
| `run_ml_eligibility_update`   | Hourly at minute :20 (8am-7pm, Mon-Sat)    | Determines if products are eligible for Mercado Libre. |
| `run_image_fetcher`           | Hourly at minute :25 (8am-7pm, Mon-Sat)    | Downloads and processes images for eligible products.  |
| `run_sync_price_list`         | Daily at 10:00 AM                          | Synchronizes the internal price list from a source.    |
| `run_prune_scrapes`           | Daily at midnight (00:00)                  | Prunes old scraped data to keep the database clean.    |

This workflow is managed by Celery Beat, which triggers each task independently based on its `crontab` schedule.

## 5. Best Practices for Creating Tasks

Follow these guidelines to ensure your tasks are robust, scalable, and easy to debug.

### Use `@shared_task`

Always use the `@shared_task` decorator for your task functions. This allows your tasks to be defined within Django apps without having to depend on a specific Celery app instance.

```python
from celery import shared_task

@shared_task
def process_data(item_id):
    # Task logic here
    ...
```

### Pass IDs, Not Objects

To prevent race conditions and ensure data freshness, **never pass full Django model objects** as arguments to tasks. The object's state might change between the time the task is enqueued and when it's actually executed.

Instead, pass the object's primary key (ID) and retrieve the object from the database inside the task.

```python
# Good Practice
from .models import Product

@shared_task
def update_product_price(product_id, new_price):
    product = Product.objects.get(id=product_id)
    product.price = new_price
    product.save()

# Bad Practice: Don't do this!
@shared_task
def update_product_price_bad(product, new_price):
    # 'product' could be stale here
    product.price = new_price
    product.save()
```

### Use `on_commit` for Transactional Safety

When triggering a task after a database write (create, update, delete), wrap the `.delay()` or `.apply_async()` call in `transaction.on_commit`. This ensures the task is only enqueued after the database transaction has been successfully committed, preventing the task from running before the data is visible in the database.

```python
from django.db import transaction

def create_product(request_data):
    product = Product.objects.create(**request_data)
    # The task will only run if the transaction succeeds
    transaction.on_commit(lambda: update_product_price.delay(product.id, 20.00))
    return product
```

## 6. Monitoring & Troubleshooting

### Real-Time Monitoring with Flower

Flower is a web-based tool for real-time monitoring of Celery tasks and workers. It provides a dashboard to inspect task progress, worker status, and other details.

To start Flower, you can add it as a service or run its command.
```bash
celery -A aiecommerce flower --address=127.0.0.1 --port=5555
```

### Local Debugging with `CELERY_ALWAYS_EAGER`

For debugging tasks locally without needing a separate worker, you can set `CELERY_ALWAYS_EAGER = True` in your local `settings.py`. This forces all tasks to be executed synchronously and locally within the process that triggered them, allowing you to use standard debuggers like `pdb`.

**Note**: Remember to set this back to `False` or remove it for regular development, as it defeats the purpose of asynchronous processing.

### Checking Logs

The first step in troubleshooting any issue is to **check the logs** from your Celery worker and Celery Beat processes. Common errors include:
-   **Broker Connection Errors**: Ensure Redis is running and accessible at the configured URL.
-   **"No Results Found" or `DoesNotExist`**: Often caused by a race condition. Make sure you are using `transaction.on_commit` when enqueuing tasks after database writes.
-   **Serialization Errors**: Ensure the data you pass to tasks is serializable (e.g., JSON-compatible). Avoid passing complex, non-serializable objects.
