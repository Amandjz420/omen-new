"""Compatibility import; implementation lives in apps.common.words."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.common.words")
