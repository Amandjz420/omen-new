"""Compatibility import; implementation lives in apps.billing.services."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.billing.services")
