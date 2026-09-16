"""Verify all restored database programs and declared foreign keys by identity."""
import json
import subprocess
from pathlib import Path
from bootstrap import ROOT, STATE, NAME


def main():
    catalog = json.loads((ROOT / 'database/mapping-catalog.json').read_text())
    schemas = ','.join("'" + s + "'" for s in catalog['schemas'])
    sql = f"""SELECT TABLE_SCHEMA,TABLE_NAME,'view' FROM information_schema.VIEWS WHERE TABLE_SCHEMA IN ({schemas})
UNION ALL SELECT TRIGGER_SCHEMA,TRIGGER_NAME,'trigger' FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA IN ({schemas})
UNION ALL SELECT ROUTINE_SCHEMA,ROUTINE_NAME,LOWER(ROUTINE_TYPE) FROM information_schema.ROUTINES WHERE ROUTINE_SCHEMA IN ({schemas});
SELECT CONSTRAINT_SCHEMA,TABLE_NAME,CONSTRAINT_NAME FROM information_schema.TABLE_CONSTRAINTS WHERE CONSTRAINT_TYPE='FOREIGN KEY' AND CONSTRAINT_SCHEMA IN ({schemas});"""
    password = (STATE / 'container.env').read_text().strip().split('=', 1)[1]
    result = subprocess.run(['docker', 'exec', '-i', '-e', 'MYSQL_PWD=' + password, NAME, 'mariadb', '-uroot', '-N', '-B'],
                            input=sql, capture_output=True, text=True, check=True)
    rows = [tuple(line.split('\t')) for line in result.stdout.splitlines()]
    objects = {r for r in rows if r[2] in {'view', 'trigger', 'procedure', 'function'}}
    constraints = set(rows) - objects
    expected = {(o['schema'], o['name'], o['kind']) for o in catalog['objects']}
    expected_fk = {(t['schema'], t['table'], f['name']) for t in catalog['tables'] for f in t['foreign_keys']}
    report = {'objects_match': objects == expected, 'foreign_keys_match': constraints == expected_fk,
              'restored_objects': sorted(objects), 'restored_foreign_keys': sorted(constraints),
              'missing_objects': sorted(expected - objects), 'unexpected_objects': sorted(objects - expected),
              'missing_foreign_keys': sorted(expected_fk - constraints), 'unexpected_foreign_keys': sorted(constraints - expected_fk),
              'behavior_status': 'Definitions restored; trigger/procedure execution parity not tested.'}
    (ROOT / 'database/object-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps({k:v for k,v in report.items() if not k.startswith('restored_')}, indent=2))
    if not report['objects_match'] or not report['foreign_keys_match']:
        raise SystemExit('Database object reconciliation failed')


if __name__ == '__main__':
    main()
