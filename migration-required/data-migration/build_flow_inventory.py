"""Generate a source-code route and table coverage appendix; no DB writes.

This is a static Java annotation inventory, not proof each legacy endpoint executes.
Commented-out annotations are excluded; GET/POST-unspecified routes are marked ANY.
"""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT.parent / 'omen-lead-new/src/main/java/com/awzpact/lead/controller'
DEST = ROOT / 'migration-required/data-migration/LEAD_FLOW_INVENTORY.md'
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*[\s\S]*?\*/')


def uncomment(text):
    return TOKEN.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m[0])
                     if m[0].startswith(('//','/*')) else m[0], text)


def main():
    lines = ['# Legacy lead flow source inventory', '',
        'Generated from the current Java controllers and Django import specifications. '
        'See [LEAD_FLOW_MIGRATION_AUDIT.md](LEAD_FLOW_MIGRATION_AUDIT.md) for business meaning, execution checks and gaps.', '',
        'Java mappings are static evidence. ANY means no HTTP method restriction is specified in the annotation; '
        'it does not authorize carrying that behavior into Django. Paths may have multiple class aliases.', '',
        '## Every source controller and declared action', '']
    total = 0
    for path in sorted(SOURCE.glob('*.java')):
        text = uncomment(path.read_text())
        declaration = re.search(r'\bclass\s+\w+', text)
        if not declaration:
            continue
        annotations = list(re.finditer(r'@RequestMapping\s*\((.*?)\)', text, flags=re.S))
        bases = ['/']
        for a in annotations:
            if a.start() < declaration.start():
                bases = re.findall(r'"([^"]*)"', a[1]) or ['/']
        lines += [f'### {path.stem}', '', '| HTTP | Full path(s) | Source |', '|---|---|---|']
        for a in annotations:
            if a.start() < declaration.start():
                continue
            methods = re.findall(r'RequestMethod\.(\w+)', a[1])
            suffixes = re.findall(r'"([^"]*)"', a[1]) or ['']
            paths = ['/'+'/'.join(x.strip('/') for x in (base, suffix) if x.strip('/'))
                     for base in bases for suffix in suffixes]
            number = text.count('\n', 0, a.start())+1
            link = '../../omen-lead-new/src/main/java/com/awzpact/lead/controller/'+path.name
            lines.append(f'| {", ".join(methods) or "ANY"} | '+ '<br>'.join(f'`{p}`' for p in paths) +
                         f' | [{path.name}:{number}]({link}#L{number}) |')
            total += 1
        lines.append('')
    tree = ast.parse((ROOT/'backend/target_core/sync.py').read_text())
    specs = next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SPECS' for t in n.targets))
    targets = {}
    for spec in specs.elts:
        schema, table = spec.elts[0].value, spec.elts[1].value
        targets[(schema,table)] = spec.elts[3].attr
    report = json.loads((ROOT/'migration-required/import-runs/imports/target-import-final.json').read_text())['tables']
    # Native dump baseline tables, sourced from the existing disposition register.
    register = (ROOT/'migration-required/data-migration/SOURCE_TO_TARGET.md').read_text().split('## lead_mngt\n',1)[1].split('\n## ',1)[0]
    lines += ['## Every lead_mngt source table', '',
        'Counts below are from the preserved source inventory and last saved full import report, not a fresh import. '
        'A model/import mapping is not an operational API.', '',
        '| Source table | Source rows | Target model | Imported-source outcomes (accepted / quarantine) |', '|---|---:|---|---|']
    tables = []
    for line in register.splitlines():
        cells = [c.strip() for c in line.split('|')]
        if len(cells) < 6 or not cells[2].replace(',','').isdigit():
            continue
        table, count = cells[1:3]
        tables.append(table)
        model = targets.get(('lead_mngt',table),'No current mapping')
        r = report.get('lead_mngt.'+table)
        outcome = f"{r['source_rows']-r['quarantined']:,} / {r['quarantined']:,}" if r else 'Not imported by current pipeline'
        lines.append(f'| `{table}` | {count} | {model} | {outcome} |')
    lines += ['', f'Coverage: {len(list(SOURCE.glob("*.java")))} controller files, {total} active method mappings, '
              f'{len(tables)} LEAD source tables, {sum(("lead_mngt",t) in targets for t in tables)} mapped LEAD source tables.', '',
              '## Target route source', '', '```python', (ROOT/'backend/config/urls.py').read_text().strip(), '```', '']
    DEST.write_text('\n'.join(lines))
    print(f'Wrote {DEST.name}: {total} method mappings; {len(tables)} LEAD tables')


if __name__ == '__main__':
    main()
