"""Compatibility import; implementation lives in apps.accounts.management.commands.provision_accounts."""
import sys
from importlib import import_module
sys.modules[__name__] = import_module("apps.accounts.management.commands.provision_accounts")
