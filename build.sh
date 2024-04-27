#!/bin/bash

# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install all the packages:
pip install -r requirements.txt

# Start Redis for the catalog service
redis-server &

# Start the catalog server
cd src/catalog
python manage.py makemigrations && python manage.py migrate
python manage.py runserver 8001 &

# Start the periodic task to restock products for the catalog server
celery -A catalog worker --loglevel=info --beat &

# Start the order server replicas
cd ../order
python manage.py makemigrations && DB_NAME=db1.sqlite3 python manage.py migrate
ORDER_SERVER_ID=3 DB_NAME=db1.sqlite3 python manage.py runserver 8002 &
python manage.py makemigrations && DB_NAME=db2.sqlite3 python manage.py migrate
ORDER_SERVER_ID=2 DB_NAME=db2.sqlite3 python manage.py runserver 8003 &
python manage.py makemigrations && DB_NAME=db3.sqlite3 python manage.py migrate
ORDER_SERVER_ID=1 DB_NAME=db3.sqlite3 python manage.py runserver 8004 &

# Start the frontend server
cd ../frontend
python manage.py makemigrations && python manage.py migrate
USE_CACHE=True python manage.py runserver 8000 &