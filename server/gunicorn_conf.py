# Gunicorn configuration file

bind = '0.0.0.0:8000'

loglevel = 'info'
errorlog = '-'
accesslog = '-'

timeout = 600
workers = 4
