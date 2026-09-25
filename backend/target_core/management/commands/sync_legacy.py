"""Compatibility import; implementation lives in apps.migration_pipeline.management.commands.sync_legacy."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.migration_pipeline.management.commands.sync_legacy")
