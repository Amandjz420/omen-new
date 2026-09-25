"""Compatibility for explicit imports; test discovery lives in apps.valuations.test_extras."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.valuations.test_extras"), name)
