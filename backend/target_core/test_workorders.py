"""Compatibility for explicit imports; test discovery lives in apps.workorders.tests."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.workorders.tests"), name)
