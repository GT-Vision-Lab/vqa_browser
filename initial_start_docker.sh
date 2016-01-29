#!/bin/sh

docker-compose build
docker-compose up -d
docker-compose stop postgres-cmd
docker-compose rm -f postgres-cmd
docker-compose ps
sleep 4 
docker-compose run django python manage.py makemigrations home
docker-compose run django python manage.py makemigrations vqa_browser
docker-compose run django python manage.py migrate
