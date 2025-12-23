# Avoid importing celery at module initialization to prevent issues with mypy and pre-commit hooks
# The celery app is still available when needed via: from aiecommerce.config.celery import app


def __getattr__(name):
    if name == "celery_app":
        from aiecommerce.config.celery import app as celery_app

        return celery_app
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
