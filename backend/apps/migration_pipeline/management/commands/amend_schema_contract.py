"""Record a deliberate schema change in the pre-split contract.

The architecture test compares every model with the contract captured before the
domain split, so an intended change fails it until recorded. This records one only
when the models that differ are exactly those named, so an accidental change can
never be absorbed alongside an intended one. Pre-split entries keep their history
through a dated amendment note, and the file keeps its original two-space format.

    manage.py amend_schema_contract --models BankReport --migration 0022_... --reason "..."
"""
import json
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
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


class Command(BaseCommand):
    help = 'Record an intended schema change in the architecture contract.'

    def add_arguments(self, parser):
        parser.add_argument('--models', nargs='+', required=True)
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
        added = [n for n in named if n not in contract['models']]
        for name in named:
            contract['models'][name] = actual[name]
        contract.setdefault('amendments', []).append({
            'date': timezone.localdate().isoformat(), 'migration': options['migration'],
            'changed_models': [n for n in named if n not in added], 'added_models': added,
            'reason': options['reason']})
        CONTRACT.write_text(json.dumps(contract, indent=2) + '\n')
        self.stdout.write(f'Recorded {named} in the contract.')
