"""Compatibility import; implementation lives in apps.migration_pipeline.management.commands.transfer_sqlite_to_postgres."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.migration_pipeline.management.commands.transfer_sqlite_to_postgres")
