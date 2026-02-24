#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."

# Wait for database connecting
while ! python -c "
import sys, psycopg2, os
try:
    psycopg2.connect(dbname=os.getenv('POSTGRES_DB', 'postgres'), user=os.getenv('POSTGRES_USER', 'postgres'), password=os.getenv('POSTGRES_PASSWORD', 'postgres'), host=os.getenv('POSTGRES_HOST', 'db'), port=os.getenv('POSTGRES_PORT', '5432'))
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
"; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

echo "PostgreSQL is up - continuing"

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Create superuser (fail silently if it already exists)
echo "Ensuring superuser exists..."
export DJANGO_SUPERUSER_USERNAME=${DJANGO_SUPERUSER_USERNAME:-admin}
export DJANGO_SUPERUSER_EMAIL=${DJANGO_SUPERUSER_EMAIL:-admin@example.com}
export DJANGO_SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-admin123}

python manage.py createsuperuser --noinput || true

echo "Starting server..."
# Pass all arguments to python manage.py runserver 0.0.0.0:8000 by default, or execute provided command
if [ "$#" -eq 0 ]; then
    exec python manage.py runserver 0.0.0.0:8000
else
    exec "$@"
fi
