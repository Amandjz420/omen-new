"""Compatibility import; implementation lives in apps.dispatch.management.commands.link_dispatch_items."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.dispatch.management.commands.link_dispatch_items")
