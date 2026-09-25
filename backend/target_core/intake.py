"""Compatibility import; implementation lives in apps.leads.services."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.leads.services")
