# Railway Deployment Guide

This guide provides instructions for deploying the Django application to Railway.

## 1. Environment Variables

The following environment variables are required for the application to run on Railway. Some of these are provided automatically by Railway when you provision services (like `DATABASE_URL` and `REDIS_URL`).

### Django & Application

- `SECRET_KEY`: A strong, unique secret key. You can generate one using `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`.
- `DEBUG`: Set to `False` for production.
- `ALLOWED_HOSTS`: A comma-separated list of your domains (e.g., `your-app.up.railway.app`).
- `CSRF_TRUSTED_ORIGINS`: Your full domain scheme (e.g., `https://your-app.up.railway.app`).
- `DATABASE_URL`: Automatically provided by the Railway PostgreSQL service.
- `CELERY_BROKER_URL`: Railway provides `REDIS_URL`, so you can use that here.
- `SESSION_COOKIE_SECURE`: Set to `True`.
- `CSRF_COOKIE_SECURE`: Set to `True`.
- `API_KEY`: A secret key for authenticating API requests via the `X-API-KEY` header. Generate a strong random value (e.g. `python -c 'import secrets; print(secrets.token_urlsafe(32))'`).
- `API_ALLOWED_IPS`: Comma-separated list of IPs/CIDRs allowed to access the API (e.g. `203.0.113.5,10.0.0.0/8`). Leave empty to allow all IPs (not recommended for production).

### Third-Party Services

- `OPENROUTER_API_KEY`: Your API key for OpenRouter.
- `MERCADOLIBRE_CLIENT_ID`: Your Mercado Libre application client ID.
- `MERCADOLIBRE_CLIENT_SECRET`: Your Mercado Libre application client secret.
- `MERCADOLIBRE_REDIRECT_URI`: The full callback URL for Mercado Libre OAuth (e.g., `https://your-app.up.railway.app/mercadolibre/callback/`).
- `GOOGLE_API_KEY`: Your Google API key for custom search.
- `GOOGLE_SEARCH_ENGINE_ID`: Your Google Custom Search Engine ID.
- `AWS_STORAGE_BUCKET_NAME`: Your S3 bucket name for media files.
- `AWS_ACCESS_KEY_ID`: Your AWS access key.
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key.
- `AWS_S3_REGION_NAME`: The AWS region for your S3 bucket.
- `EAN_SEARCH_TOKEN`: Your token for the EAN search service.

## 2. Standard Web Access

To expose the web service to the internet, you need to generate a domain.

1.  Navigate to your project's dashboard on Railway.
2.  Select the `web` service.
3.  Go to the **Settings** tab.
4.  Under the "Networking" section, click **Generate Domain**. Railway will provide a public `*.up.railway.app` domain.

## 3. Service Commands (Procfile)

Railway uses the `Procfile` to determine how to run the services.

- **web**: The web service runs the Django application using Gunicorn. It also runs migrations on startup.
  ```
  web: python manage.py migrate && gunicorn aiecommerce.wsgi
  ```
- **worker**: The Celery worker for processing asynchronous tasks.
  ```
  worker: celery -A aiecommerce worker -l info
  ```
- **beat**: The Celery beat scheduler for periodic tasks.
  ```
  beat: celery -A aiecommerce beat -l info
  ```

## 4. Troubleshooting

### Database Connection Issues

- **Symptom**: Application fails to start with errors related to database authentication or connection.
- **Solution**:
  1.  Ensure you have a PostgreSQL service provisioned in your Railway project.
  2.  Verify that the `DATABASE_URL` environment variable is present in your service's settings. Railway should inject this automatically if the database is linked.
  3.  The `dj-database-url` package is used to parse this URL, so no other `POSTGRES_*` variables are needed.

### Static File (CSS/JS) Issues

- **Symptom**: The deployed site has no styling, and the browser console shows 404 errors for CSS and JavaScript files.
- **Solution**: This project uses `whitenoise` to serve static files directly from Gunicorn.
  1.  Ensure `whitenoise` is listed in your `requirements.txt`.
  2.  The `web` command in your `Procfile` does not need to run `collectstatic`. `whitenoise` handles finding the files.
  3.  Check that your `aiecommerce/settings.py` includes the `whitenoise.middleware.WhiteNoiseMiddleware` in the `MIDDLEWARE` list, near the top.
  4.  Verify that `STORAGES` is configured for `whitenoise` as per the project's settings.
