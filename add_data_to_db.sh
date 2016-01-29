#!/bin/sh

docker-compose run django python manage.py browser_add_base_urls
docker-compose run django python manage.py browser_add_data
