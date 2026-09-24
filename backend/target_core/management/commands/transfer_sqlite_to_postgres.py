"""One-time copy of the retired SQLite target into PostgreSQL.

Run with --settings=config.transfer, after `migrate` has built the PostgreSQL
schema. The schema comes from the migrations, never from SQLite, so every
constraint and index matches the models exactly.

Every table except django_migrations is truncated in PostgreSQL and reloaded
from SQLite, including content types and permissions, so all internal ids and
the references between them survive unchanged. Nothing is written to SQLite.

Values needing conversion:
  * booleans are 0/1 integers in SQLite;
  * datetimes are naive UTC strings in SQLite (Django's convention with
    USE_TZ=True), so the session loads them as UTC;
  * UUIDs are 32-character hex in SQLite, which PostgreSQL accepts directly.

Foreign-key triggers are suspended during the load because PostgreSQL does not
recheck rows when they are re-enabled, so integrity is verified explicitly
afterwards across every foreign key the models declare.
"""
import time

from django.apps import apps
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connections

SKIP = {'django_migrations'}
CHUNK = 20000


class Command(BaseCommand):
    help = 'Copy all data from the SQLite target into the PostgreSQL target, then verify.'

    def add_arguments(self, parser):
        parser.add_argument('--verify-only', action='store_true')

    def handle(self, *args, **options):
        if 'sqlite' not in connections.databases:
            raise CommandError('Run with --settings=config.transfer')
        src, dst = connections['sqlite'], connections['default']
        if dst.vendor != 'postgresql':
            raise CommandError('The default database is not PostgreSQL')

        with src.cursor() as c:
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
            tables = [r[0] for r in c.fetchall() if r[0] not in SKIP]
        with dst.cursor() as c:
            c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            present = {r[0] for r in c.fetchall()}
        missing = [t for t in tables if t not in present]
        if missing:
            raise CommandError(f'Schema drift, absent in PostgreSQL: {missing}. Run migrate first.')

        if not options['verify_only']:
            self.load(src, dst, tables)
        self.verify(src, dst, tables)

    def load(self, src, dst, tables):
        raw = dst.connection if dst.connection else (dst.ensure_connection() or dst.connection)
        with dst.cursor() as c:
            c.execute("SET TIME ZONE 'UTC'")
            c.execute("SET session_replication_role = replica")
            c.execute('TRUNCATE ' + ', '.join(f'"{t}"' for t in tables) + ' RESTART IDENTITY CASCADE')
        started = time.time()
        for table in tables:
            with src.cursor() as c:
                c.execute(f'PRAGMA table_info("{table}")')
                columns = [r[1] for r in c.fetchall()]
            with dst.cursor() as c:
                c.execute("""SELECT column_name, data_type FROM information_schema.columns
                             WHERE table_schema='public' AND table_name=%s""", [table])
                types = dict(c.fetchall())
            booleans = [i for i, col in enumerate(columns) if types.get(col) == 'boolean']
            copied = 0
            with src.cursor() as read, dst.cursor() as write:
                read.execute(f'SELECT {", ".join(chr(34)+c+chr(34) for c in columns)} FROM "{table}"')
                target = ', '.join(f'"{c}"' for c in columns)
                with write.cursor.copy(f'COPY "{table}" ({target}) FROM STDIN') as copy:
                    while True:
                        batch = read.fetchmany(CHUNK)
                        if not batch:
                            break
                        for row in batch:
                            if booleans:
                                row = list(row)
                                for i in booleans:
                                    if row[i] is not None:
                                        row[i] = bool(row[i])
                            copy.write_row(row)
                        copied += len(batch)
            self.stdout.write(f'{table:48s} {copied:>10,}')
        with dst.cursor() as c:
            c.execute("SET session_replication_role = DEFAULT")
        self.stdout.write(f'loaded {len(tables)} tables in {time.time() - started:.0f}s; resetting sequences')
        for app in ('auth', 'contenttypes', 'sessions', 'admin', 'target_core'):
            from io import StringIO
            out = StringIO()
            call_command('sqlsequencereset', app, stdout=out, database='default')
            if out.getvalue().strip():
                with dst.cursor() as c:
                    c.execute(out.getvalue())

    def verify(self, src, dst, tables):
        mismatched = []
        total = 0
        for table in tables:
            with src.cursor() as c:
                c.execute(f'SELECT COUNT(*) FROM "{table}"'); a = c.fetchone()[0]
            with dst.cursor() as c:
                c.execute(f'SELECT COUNT(*) FROM "{table}"'); b = c.fetchone()[0]
            total += b
            if a != b:
                mismatched.append((table, a, b))
        self.stdout.write(f'row counts: {len(tables)} tables, {total:,} rows, mismatches {len(mismatched)}')
        for t, a, b in mismatched:
            self.stdout.write(self.style.ERROR(f'  {t}: sqlite {a:,} != postgres {b:,}'))

        orphans = 0
        checked = 0
        for model in apps.get_models():
            for field in model._meta.concrete_fields:
                if not field.is_relation or not field.many_to_one and not field.one_to_one:
                    continue
                child, col = model._meta.db_table, field.column
                parent, pk = field.related_model._meta.db_table, field.target_field.column
                with dst.cursor() as c:
                    c.execute(f'SELECT COUNT(*) FROM "{child}" x WHERE x."{col}" IS NOT NULL AND NOT EXISTS '
                              f'(SELECT 1 FROM "{parent}" p WHERE p."{pk}" = x."{col}")')
                    n = c.fetchone()[0]
                checked += 1
                if n:
                    orphans += n
                    self.stdout.write(self.style.ERROR(f'  orphan: {child}.{col} -> {parent}: {n}'))
        self.stdout.write(f'foreign keys: {checked} checked, {orphans} orphaned rows')
        if mismatched or orphans:
            raise CommandError('Verification failed')
        self.stdout.write(self.style.SUCCESS('transfer verified: counts identical, no orphaned references'))
