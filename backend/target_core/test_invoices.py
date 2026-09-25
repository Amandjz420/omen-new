"""Compatibility for explicit imports; test discovery lives in apps.billing.tests."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.billing.tests"), name)
