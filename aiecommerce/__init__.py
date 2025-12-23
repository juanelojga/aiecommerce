try:
    # When Celery is installed, expose the real Celery app for Django/Celery integration
    from aiecommerce.config.celery import app as celery_app  # type: ignore
except ModuleNotFoundError:
    # Allow type checkers (e.g., MyPy with Django plugin) to import settings
    # without requiring Celery to be installed. Provide a minimal stub.
    celery_app = None  # type: ignore[assignment]

__all__ = ("celery_app",)
