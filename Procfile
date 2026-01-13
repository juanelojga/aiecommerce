web: python manage.py migrate && gunicorn aiecommerce.wsgi
worker: celery -A aiecommerce worker -l info
beat: celery -A aiecommerce beat -l info
