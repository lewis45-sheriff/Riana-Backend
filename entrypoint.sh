#!/usr/bin/env sh
set -e

echo "Applying migrations..."
python manage.py migrate --noinput

echo "Ensuring care-rep login exists..."
python manage.py seed_user || echo "seed_user skipped/failed; continuing"

if [ "${SEED_ON_START:-true}" = "true" ]; then
  echo "Seeding demo data (if empty)..."
  python manage.py seed || echo "Seed skipped/failed; continuing"
fi

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
