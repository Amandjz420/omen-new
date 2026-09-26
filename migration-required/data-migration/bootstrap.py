"""Provision a NEW isolated local full-dump baseline. Never targets an existing DB."""
import json
import os
import secrets
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / 'database' / '.local'
NAME = 'omen-full-database-20260916'
IMAGE = 'mariadb:10.11'


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def main():
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = STATE / 'connection.json'
    if config.exists():
        raise SystemExit('Already provisioned. See connection.json; refusing to overwrite.')
    probe = subprocess.run(['docker', 'inspect', NAME], capture_output=True)
    if probe.returncode == 0:
        raise SystemExit('Container name exists; refusing to reuse or modify it.')
    root_password = secrets.token_urlsafe(40)
    password = secrets.token_urlsafe(40)
    envfile = STATE / 'container.env'
    envfile.write_text('MARIADB_ROOT_PASSWORD=' + root_password + '\n')
    envfile.chmod(0o600)
    run(['docker', 'pull', IMAGE])
    run(['docker', 'run', '-d', '--name', NAME, '--label', 'omen.migration=full-baseline',
         '-p', '127.0.0.1:3307:3306', '--env-file', str(envfile),
         '-v', NAME + ':/var/lib/mysql', IMAGE,
         '--lower-case-table-names=1', '--max-allowed-packet=256M',
         '--innodb-buffer-pool-size=512M', '--sql-mode=NO_ENGINE_SUBSTITUTION'])
    for _ in range(120):
        result = subprocess.run(['docker', 'exec', NAME, 'healthcheck.sh', '--connect', '--innodb_initialized'], capture_output=True)
        if result.returncode == 0:
            break
        time.sleep(1)
    else:
        raise SystemExit('Container did not become ready; it has been retained for diagnosis.')
    # The dump uses omen_user as DEFINER. Create a locked definer with local-only database privileges.
    sql = f"CREATE USER 'omen_user'@'%' ACCOUNT LOCK; CREATE USER 'django_reader'@'%' IDENTIFIED BY '{password}';"
    for schema in ['ebioserver', 'lead_mngt', 'smldb', 'uam_user', 'uam_user_uat', 'lead_mngt_uat', 'smldb_uat']:
        sql += f"GRANT ALL ON `{schema}`.* TO 'omen_user'@'%'; GRANT SELECT, SHOW VIEW ON `{schema}`.* TO 'django_reader'@'%';"
    run(['docker', 'exec', '-i', '-e', 'MYSQL_PWD=' + root_password, NAME, 'mariadb', '-uroot'], input=sql.encode())
    config.write_text(json.dumps({'container': NAME, 'host': '127.0.0.1', 'port': 3307, 'user': 'django_reader', 'password': password}))
    config.chmod(0o600)
    print('Created isolated full-database container and read-only Django connection.', flush=True)


if __name__ == '__main__':
    main()
