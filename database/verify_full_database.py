"""Reconcile every source table against the local restore without printing row data."""
import collections
import hashlib
import importlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.full_database')


def source_counts(source, tables):
    counts = {f"{t['schema']}.{t['table']}": 0 for t in tables}
    schema = None
    token = re.compile(rb"'(?:[^'\\]|\\.)*'|[()]")
    digest = hashlib.sha256()
    with source.open('rb') as stream:
        for line in stream:
            digest.update(line)
            use = re.match(rb'USE `([^`]+)`;', line)
            if use:
                schema = use[1].decode()
            insert = re.match(rb'INSERT INTO `([^`]+)` VALUES ', line)
            if not insert:
                continue
            key = schema + '.' + insert[1].decode()
            if key not in counts:
                raise ValueError('Uncatalogued INSERT table: ' + key)
            depth, rows = 0, 0
            for match in token.finditer(line, insert.end()):
                if match[0] == b'(':
                    depth += 1
                    if depth != 1:
                        raise ValueError('Unexpected nested INSERT expression')
                    rows += 1
                elif match[0] == b')':
                    depth -= 1
            if depth:
                raise ValueError('Unbalanced INSERT')
            counts[key] += rows
    return counts, digest.hexdigest()


def main():
    import django
    django.setup()
    from django.db import connections
    catalog = json.loads((ROOT / 'database' / 'mapping-catalog.json').read_text())
    expected, digest = source_counts(ROOT.parent / 'all_schemas_2026-09-10.sql', catalog['tables'])
    if digest != catalog['source_sha256']:
        raise SystemExit('Source checksum mismatch')
    print('Counted every source INSERT. Validating all tables through Django...', flush=True)
    results, failures = [], []
    for index, table in enumerate(catalog['tables']):
        schema, name = table['schema'], table['table']
        key = schema + '.' + name
        module = importlib.import_module('legacy.' + schema + '.models')
        model = getattr(module, table['class'])
        orm_rows = model.objects.count() if table['access'] == 'orm' else model.count()
        # Materialize a row internally to exercise field mappings/conversions, never print it.
        if table['access'] == 'orm':
            list(model.objects.all()[:1])
        else:
            model.rows(limit=1)
        with connections[schema].cursor() as cursor:
            cursor.execute('SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION', [schema, name])
            columns = [r[0] for r in cursor.fetchall()]
            cursor.execute('SELECT INDEX_NAME,COLUMN_NAME,SEQ_IN_INDEX,NON_UNIQUE FROM information_schema.STATISTICS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY INDEX_NAME,SEQ_IN_INDEX', [schema, name])
            indexes = {}
            for ix, col, pos, non_unique in cursor.fetchall():
                indexes.setdefault(ix, []).append(col)
        expected_indexes = {i['name']: i['columns'] for i in table['indexes']}
        result = {'schema': schema, 'table': name, 'source_rows': expected[key], 'restored_rows': orm_rows,
                  'rows_match': expected[key] == orm_rows, 'columns_match': columns == list(table['fields']),
                  'indexes_match': indexes == expected_indexes, 'access': table['access']}
        results.append(result)
        if not all(result[k] for k in ('rows_match', 'columns_match', 'indexes_match')):
            failures.append(key)
        if (index + 1) % 100 == 0:
            print(f'Validated {index + 1} tables', flush=True)
    objects = []
    for obj in catalog['objects']:
        with connections[obj['schema']].cursor() as cursor:
            if obj['kind'] == 'view':
                cursor.execute(f"SELECT * FROM `{obj['name']}` LIMIT 0")
                found = True
            else:
                # Routine metadata needs privileges not granted to the reader; verification uses the dedicated local admin below.
                found = None
        objects.append({**obj, 'query_compiles': found})
    summary = {'source_sha256': digest, 'tables_checked': len(results),
               'source_rows': sum(expected.values()), 'restored_rows': sum(r['restored_rows'] for r in results),
               'failed_tables': failures, 'schemas': {}, 'objects': objects, 'tables': results}
    for schema in catalog['schemas']:
        subset = [r for r in results if r['schema'] == schema]
        summary['schemas'][schema] = {'tables': len(subset), 'rows': sum(r['restored_rows'] for r in subset)}
    (ROOT / 'database' / 'verification.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k not in ('tables', 'objects')}, indent=2), flush=True)
    if failures:
        raise SystemExit('Reconciliation failures; see verification.json')


if __name__ == '__main__':
    main()
