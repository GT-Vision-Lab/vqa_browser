#!/usr/bin/python

import os
import sys
import subprocess
import datetime

cur_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(cur_dir, '..'))

import server.config.settings_local as settings


def dir_path(dname):
    '''If the directory doesn't exist, then make it.'''

    try:
        os.makedirs(dname)
    except os.error:
        pass
    return dname

backup_dir = settings.DATABASE_BACKUP_DIR
dir_path(backup_dir)

time = datetime.datetime.utcnow()
fn = '{}.sql'.format(str(time).replace(' ', '--').replace(':', '.'))
fl = os.path.join(backup_dir, fn)
str_cmd = ('docker-compose run postgres-cmd pg_dump -w -Fc -f {0} && '
           'zip -j {0}.zip {0} && '
           'rm -f {0}'.format(fl))

# TODO Make more platform agnostic
subprocess.call(str_cmd, shell=True)
