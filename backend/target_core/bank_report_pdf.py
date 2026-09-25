"""Compatibility import; implementation lives in apps.reports.pdf."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.reports.pdf")
