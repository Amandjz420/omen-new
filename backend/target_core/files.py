"""Compatibility import; implementation lives in apps.documents.storage."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.documents.storage")
