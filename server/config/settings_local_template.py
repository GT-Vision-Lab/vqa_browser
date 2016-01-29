##
## LOCAL DJANGO SETTINGS
##

##
## IMPORTANT SETTINGS
##

import os

# SECURITY WARNING: keep the secret key used in production secret!
# Make something random up like below.
SECRET_KEY = 'fgcrj$k(#))z55hr5023*)ll0x#84r^tflz6y%ww0@pg(c-*-m'

# Directory where the postgres database files will live
# Ideally on a separate volume in case instance breaks
DATABASE_DIR = '/aws_db'
DATABASE_DIR = '/ssd_local/web_apps/vqa_browser/db'
                                                  
# Directory where the large files (e.g., images, backups) will live
# Ideally on a separate volume in case instance breaks
# Maybe even separate from DATABASE_DIR
DATA_DIR ='/aws_data'
DATA_DIR='/ssd_local/web_apps/vqa_browser/data' 
DATABASE_BACKUP_DIR = os.path.join(DATA_DIR, 'db_backup')

# Directory where the annotation files live,
# i.e., instances, captions, vqa
ANN_FILE_DIR='/srv/share/vqa/release_data/browser_data'

# Change some of these parameters accordingly
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': 'postgres', # Not sure what this is for
        'NAME': 'DB_NAME',
        'PASSWORD': 'DB_PASS',
        'PORT': 'DB_PORT',
        'USER': 'DB_USER',
    }
}

# The common folder name to mount the project directory to in containers
DOCKER_DIR = '/docker_share'                                             

# What the db hostname will be in containers
DOCKER_DB_HOST = 'db'
