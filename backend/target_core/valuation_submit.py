"""Compatibility import; implementation lives in apps.valuations.submission."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.valuations.submission")
