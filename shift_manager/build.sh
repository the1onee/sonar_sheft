#!/usr/bin/env bash
# exit on error
set -o errexit

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run database migrations
python manage.py migrate --no-input

# Create superuser if it doesn't exist (optional)
# python manage.py createsuperuser --no-input --username admin --email admin@example.com || true

echo "Build completed successfully!"

