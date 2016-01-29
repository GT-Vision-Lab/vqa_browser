FROM python:3.4-onbuild

ENV DJANGO_CONFIGURATION Docker

CMD ["gunicorn", "-c", "gunicorn_conf.py", "config.wsgi:application", "--reload"]

