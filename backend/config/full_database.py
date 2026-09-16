"""Opt-in full database configuration; never used implicitly by the preview."""
import json
from .settings import *

connection_file = BASE_DIR.parent / 'database' / '.local' / 'connection.json'
cfg = json.loads(connection_file.read_text())
SCHEMAS = ['ebioserver', 'lead_mngt', 'smldb', 'uam_user', 'uam_user_uat', 'lead_mngt_uat', 'smldb_uat']
INSTALLED_APPS = [*INSTALLED_APPS, *[f'legacy.{s}.apps.LegacyConfig' for s in SCHEMAS]]
DATABASE_ROUTERS = ['legacy.base.LegacyRouter']
for schema in SCHEMAS:
    DATABASES[schema] = {'ENGINE': 'django.db.backends.mysql', 'NAME': schema,
                         'USER': cfg['user'], 'PASSWORD': cfg['password'], 'HOST': cfg['host'], 'PORT': cfg['port'],
                         'OPTIONS': {'charset': 'utf8mb4'}, 'CONN_MAX_AGE': 0}
