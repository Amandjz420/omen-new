"""Compatibility for explicit imports; test discovery lives in apps.reports.test_reports."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.reports.test_reports"), name)
