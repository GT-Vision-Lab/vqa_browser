#!/usr/bin/python

from string import Template

import server.config.settings_local as settings


db_settings = settings.DATABASES['default']

docker_db_fn = 'pg_pass_file'
docker_template_fn = 'docker-compose_template.yml'
docker_fn = docker_template_fn.replace('_template', '')

# Need to quote values if there are any special characters
d = {
    'ann_dir': "{}".format(settings.ANN_FILE_DIR),
    'data_dir': "{}".format(settings.DATA_DIR),
    'db_dir': "{}".format(settings.DATABASE_DIR),
    'db_name': "{}".format(db_settings['NAME']),
    'db_pass': "{}".format(db_settings['PASSWORD']),
    'db_port': "{}".format(db_settings['PORT']),
    'db_user': "{}".format(db_settings['USER']),
    'dock_share': "{}".format(settings.DOCKER_DIR),
}

with open(docker_template_fn, 'r') as inf, open(docker_fn, 'wt') as outf:
    for line in inf:
        new_line = Template(line).substitute(d)
        outf.write(new_line)

# Create pg_pass_file
# settings.DOCKER_DB_HOST
with open(docker_db_fn, 'wt') as outf:
    outf.write("{}:{}:{}:{}:{}".format(settings.DOCKER_DB_HOST,
                                       d['db_port'],
                                       d['db_name'],
                                       d['db_user'],
                                       d['db_pass']))
    outf.write('\n')
    outf.write("{}:{}:{}:{}:{}".format(settings.DOCKER_DB_HOST,
                                       d['db_port'],
                                       '*',
                                       d['db_user'],
                                       d['db_pass']))
