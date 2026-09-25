"""Compatibility for explicit imports; test discovery lives in apps.valuations.test_forms."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.valuations.test_forms"), name)
