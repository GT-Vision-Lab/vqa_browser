#!/usr/bin/python

import os
import sys
import subprocess
import datetime

cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))

import server.config.settings_local as settings

backup_dir = settings.DATABASE_BACKUP_DIR

flz = os.path.join(backup_dir, sys.argv[1])
fl = flz.replace('.zip', '')

zip_cmd = 'unzip {0} -d {1}'
db_cmd = 'dropdb -w $PGDATABASE && createdb -w -T template0 && pg_restore -w -d $PGDATABASE -C {2}'
dock_cmd = "docker-compose run postgres-cmd sh -c '{}'".format(db_cmd)
rm_cmd = 'rm -f {2}'

str_cmd = ' && '.join([zip_cmd, dock_cmd, rm_cmd])
str_cmd = str_cmd.format(flz, backup_dir, fl)
print(str_cmd)
# TODO Make more platform agnostic
subprocess.call(str_cmd, shell=True)
