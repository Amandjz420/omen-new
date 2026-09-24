"""Settings for the one-time SQLite -> PostgreSQL transfer.

Adds the retired SQLite file as a read-only source alias beside the PostgreSQL
default. Kept out of the main settings so the test runner never creates a test
database for it.
"""
from .settings import *  # noqa: F401,F403

DATABASES['sqlite'] = {'ENGINE': 'django.db.backends.sqlite3', 'NAME': SQLITE_PATH}
