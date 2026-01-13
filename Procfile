web: gunicorn aiecommerce.wsgi --bind 0.0.0.0:$PORT
worker: celery -A aiecommerce worker -l info
beat: celery -A aiecommerce beat -l info
