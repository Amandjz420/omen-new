"""Compatibility import; implementation lives in apps.migration_pipeline.management.commands.sanitize_staged_credentials."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.migration_pipeline.management.commands.sanitize_staged_credentials")
