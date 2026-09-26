"""Explicit table access by reviewed schema/table identity, including keyless tables."""
import importlib
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def catalog():
    path = Path(__file__).resolve().parents[2] / 'migration-required/data-migration/mapping-catalog.json'
    return {(t['schema'], t['table']): t for t in json.loads(path.read_text())['tables']}


def table(schema, name):
    spec = catalog().get((schema, name))
    if spec is None:
        raise ValueError('Unknown schema/table identity')
    return getattr(importlib.import_module(f'legacy.{schema}.models'), spec['class'])
