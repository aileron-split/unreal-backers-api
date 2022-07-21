#!/bin/sh

>&2 echo "Migrating database"

./manage.py collectstatic --no-input
./manage.py migrate
./manage.py createsuperuser --no-input

>&2 echo "Running server"

./manage.py runserver 0.0.0.0:8000

