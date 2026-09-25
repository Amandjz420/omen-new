import json
from django.core.management.base import BaseCommand, CommandError
from target_core.sync import MySQLSource, synchronize


class Command(BaseCommand):
    help='Refresh managed target entities directly from the read-only main MySQL schemas. Attendance is excluded.'
    def add_arguments(self, parser):
        parser.add_argument('--dry-run',action='store_true')
        parser.add_argument('--report',help='Write non-sensitive per-table reconciliation JSON to this path')
    def handle(self,*args,**options):
        try:
            report=synchronize(MySQLSource(),dry_run=options['dry_run'],progress=self.stdout.write)
        except Exception as exc:
            raise CommandError(f'{type(exc).__name__}: {exc}') from exc
        if options['report']:
            from pathlib import Path
            Path(options['report']).write_text(json.dumps({'dry_run':options['dry_run'],'tables':report},indent=2))
