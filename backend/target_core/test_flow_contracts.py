"""Compatibility for explicit imports; test discovery lives in apps.leads.test_flow_contracts."""
from importlib import import_module

def __getattr__(name):
    return getattr(import_module("apps.leads.test_flow_contracts"), name)
