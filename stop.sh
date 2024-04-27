#!/bin/bash

# Stop Redis
pkill redis-server

# Stop Celery
pkill -f 'celery'

# Stop Django servers
pkill -f runserver

echo "All applications stopped."