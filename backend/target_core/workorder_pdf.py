"""Compatibility import; implementation lives in apps.workorders.pdf."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.workorders.pdf")
