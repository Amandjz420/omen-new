"""Restore the original full dump into the dedicated NEW local baseline only."""
import hashlib
import json
import subprocess
from pathlib import Path
from bootstrap import ROOT, STATE, NAME

SOURCE = ROOT.parent / 'all_schemas_2026-09-10.sql'
EXPECTED = '9231eb899811774ecf4ed86eab4d9d04c003f39311dc4459367bd3d003e810e8'


def main():
    digest = hashlib.file_digest(SOURCE.open('rb'), 'sha256').hexdigest()
    if digest != EXPECTED:
        raise SystemExit('Dump checksum differs from reviewed snapshot. Refusing restore.')
    cfg = json.loads((STATE / 'connection.json').read_text())
    if cfg['container'] != NAME:
        raise SystemExit('Unexpected target container')
    password = (STATE / 'container.env').read_text().strip().split('=', 1)[1]
    cmd = ['docker', 'exec', '-i', '-e', 'MYSQL_PWD=' + password, NAME, 'mariadb', '-uroot', '--max-allowed-packet=256M']
    count = subprocess.run(cmd + ['-N', '-e', "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema IN ('ebioserver','lead_mngt','smldb','uam_user','uam_user_uat','lead_mngt_uat','smldb_uat')"], check=True, capture_output=True, text=True)
    if count.stdout.strip() != '0':
        raise SystemExit('Target contains source tables already. Refusing destructive replay.')
    print('Restoring checksum-verified full dump into isolated container...', flush=True)
    # Error text can contain SQL/data. Keep it private; expose only success/failure here.
    with SOURCE.open('rb') as source, (STATE / 'restore.log').open('wb') as log:
        result = subprocess.run(cmd, stdin=source, stdout=log, stderr=log)
    status = {'source_sha256': digest, 'container': NAME, 'returncode': result.returncode,
              'status': 'restored_pending_validation' if result.returncode == 0 else 'failed_partial_restore'}
    (STATE / 'restore-status.json').write_text(json.dumps(status, indent=2))
    print(json.dumps(status), flush=True)
    if result.returncode:
        raise SystemExit('Restore failed; inspect private log. Target retained, not automatically retried.')


if __name__ == '__main__':
    main()
