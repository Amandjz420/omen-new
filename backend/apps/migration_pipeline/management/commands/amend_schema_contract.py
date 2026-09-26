"""Record a deliberate schema or API change in the pre-split contract.

The architecture test compares every model with the contract captured before the
domain split, so an intended change fails it until recorded. This records one only
when the models that differ are exactly those named, so an accidental change can
never be absorbed alongside an intended one. Pre-split entries keep their history
through a dated amendment note, and the file keeps its original two-space format.

    manage.py amend_schema_contract --models BankReport --migration 0022_... --reason "..."
    manage.py amend_schema_contract --add-routes api/receipts/ ... --migration none --reason "..."

New API routes are recorded the same way: only when the routes added are exactly
those named, and never when a recorded route has disappeared.
"""
import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.urls import URLPattern, get_resolver
from django.db.migrations.state import ModelState
from django.db.migrations.writer import MigrationWriter
from django.utils import timezone

CONTRACT = Path(__file__).resolve().parents[2] / 'fixtures' / 'pre_split_contract.json'


def entry(model):
    state = ModelState.from_model(model)
    state.options.setdefault('abstract', False)
    return {'label': model._meta.label, 'table': model._meta.db_table,
            'fields': {name: MigrationWriter.serialize(field)[0] for name, field in state.fields.items()},
            'options': MigrationWriter.serialize(state.options)[0]}


def api_routes(resolver=None, prefix=''):
    """Every api/ route, enumerated as the architecture test does."""
    for item in (resolver or get_resolver()).url_patterns:
        route = prefix + str(item.pattern)
        if isinstance(item, URLPattern):
            if route.startswith('api/'):
                yield route
        elif not route.startswith('admin/'):
            yield from api_routes(item, route)


class Command(BaseCommand):
    help = 'Record an intended schema change in the architecture contract.'

    def add_arguments(self, parser):
        parser.add_argument('--models', nargs='*', default=[])
        parser.add_argument('--add-routes', nargs='*', default=[])
        parser.add_argument('--migration', required=True)
        parser.add_argument('--reason', required=True)

    def handle(self, *args, **options):
        contract = json.loads(CONTRACT.read_text())
        actual = {model.__name__: entry(model) for model in apps.get_app_config('target_core').get_models()}
        differing = sorted(name for name in set(actual) | set(contract['models'])
                           if actual.get(name) != contract['models'].get(name))
        named = sorted(options['models'])
        if differing != named:
            raise CommandError(f'Models that differ: {differing}; named: {named}. Refusing to record.')
        routes = list(api_routes())
        missing = sorted(set(contract['routes']) - set(routes))
        if missing:
            raise CommandError(f'Recorded routes have disappeared: {missing}. Refusing to record.')
        new_routes = sorted(set(routes) - set(contract['routes']))
        if new_routes != sorted(options['add_routes']):
            raise CommandError(f'Routes added: {new_routes}; named: {sorted(options["add_routes"])}. Refusing to record.')
        if not named and not new_routes:
            raise CommandError('Nothing differs from the contract.')
        added = [n for n in named if n not in contract['models']]
        for name in named:
            contract['models'][name] = actual[name]
        contract['routes'] = contract['routes'] + new_routes
        amendment = {'date': timezone.localdate().isoformat(), 'migration': options['migration'],
                     'changed_models': [n for n in named if n not in added], 'added_models': added,
                     'reason': options['reason']}
        if new_routes:
            amendment['added_routes'] = new_routes
        contract.setdefault('amendments', []).append(amendment)
        CONTRACT.write_text(json.dumps(contract, indent=2) + '\n')
        self.stdout.write(f'Recorded models {named} and routes {new_routes} in the contract.')
