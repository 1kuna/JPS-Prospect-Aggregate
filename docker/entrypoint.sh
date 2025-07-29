#!/bin/bash
set -e

echo "Starting JPS Prospect Aggregate application..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready!"

# Run database migrations
echo "Running database migrations..."
cd /app
python -m alembic upgrade head

# Start the application
echo "Starting application..."
exec "$@"