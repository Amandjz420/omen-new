"""Guard the database and URL contract captured before the domain split."""
import importlib
import json
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.core.management import get_commands, load_command_class
from django.db.migrations.state import ModelState
from django.db.migrations.writer import MigrationWriter
from django.test import SimpleTestCase
from django.urls import URLPattern, get_resolver, resolve


class DomainCompatibilityTests(SimpleTestCase):
    def test_all_model_fields_tables_and_constraints_match_the_pre_split_contract(self):
        contract = json.loads((Path(__file__).parent / 'fixtures/pre_split_contract.json').read_text())
        actual = {}
        for model in apps.get_app_config('target_core').get_models():
            state = ModelState.from_model(model)
            # Explicit Meta replaces an inherited abstract=False; both mean concrete.
            state.options.setdefault('abstract', False)
            actual[model.__name__] = {
                'label': model._meta.label, 'table': model._meta.db_table,
                'fields': {name: MigrationWriter.serialize(field)[0] for name, field in state.fields.items()},
                'options': MigrationWriter.serialize(state.options)[0],
            }
        self.assertEqual(actual, contract['models'])

    def test_every_existing_api_pattern_remains_available_once(self):
        contract = json.loads((Path(__file__).parent / 'fixtures/pre_split_contract.json').read_text())
        def patterns(resolver, prefix=''):
            for item in resolver.url_patterns:
                route = prefix + str(item.pattern)
                if isinstance(item, URLPattern):
                    if route.startswith('api/'):
                        yield route
                elif not route.startswith('admin/'):
                    yield from patterns(item, route)
        self.assertCountEqual(list(patterns(get_resolver())), contract['routes'])
        self.assertEqual(resolve('/api/login/').func.__module__, 'apps.accounts.api')
        self.assertEqual(resolve('/api/intake/offices/').func.__module__, 'apps.directory.services')
        self.assertEqual(resolve('/api/intake/catalog/').func.__module__, 'apps.catalog.api')

    def test_model_imports_and_admin_use_the_same_registered_classes(self):
        owners = json.loads((settings.BASE_DIR / 'apps/model_ownership.json').read_text())
        old = importlib.import_module('target_core.models')
        for name, domain in owners.items():
            with self.subTest(model=name):
                model = getattr(importlib.import_module(f'apps.{domain}.models'), name)
                self.assertIs(model, getattr(old, name))
                self.assertIs(model, apps.get_model('target_core', name))
                self.assertIn(model, admin.site._registry)

    def test_commands_and_credential_location_are_preserved(self):
        for name in ('sync_legacy', 'provision_accounts', 'setup_admin_accounts',
                     'sanitize_staged_credentials', 'transfer_sqlite_to_postgres', 'link_dispatch_items'):
            command = load_command_class(get_commands()[name], name)
            old = importlib.import_module(f'target_core.management.commands.{name}')
            self.assertIs(type(command), old.Command)
        from apps.accounts.management.commands.setup_admin_accounts import SECRET_DIR
        self.assertEqual(SECRET_DIR, settings.BASE_DIR.parent / 'database/.local')

    def test_pdf_letterhead_survives_module_relocation(self):
        from apps.reports.pdf import LETTERHEAD
        self.assertTrue(LETTERHEAD.is_file())
