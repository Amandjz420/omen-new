"""Compatibility for explicit imports; test discovery lives in apps.migration_pipeline.tests."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.migration_pipeline.tests"), name)
