"""
Check ClickHouse backups: its state, age and count.
"""

import json
import subprocess
from datetime import datetime, timedelta, timezone

import click

from cloud.mdb.clickhouse.tools.common.backup import BackupConfig
from cloud.mdb.clickhouse.tools.monrun_checks.exceptions import die

DATE_FORMAT = '%Y-%m-%d %H:%M:%S %z'


@click.command('backup')
def backup_command():
    """
    Check ClickHouse backups: its state, age and count.
    """
    backup_config = BackupConfig.load()
    backups = get_backups()

    check_valid_backups_exist(backups)
    check_last_backup_not_failed(backups)
    check_backup_age(backups)
    check_backup_count(backup_config, backups)


def check_valid_backups_exist(backups):
    """
    Check that valid backups exist.
    """
    for backup in backups:
        if backup['state'] == 'created':
            return

    die(2, 'No valid backups found')


def check_last_backup_not_failed(backups):
    """
    Check that the last backup is not failed. Its status must be 'created' or 'creating'.
    """
    counter = 0
    for i, backup in enumerate(backups):
        state = backup['state']

        if state == 'created':
            break

        if state == 'failed' or (state == 'creating' and i > 0):
            counter += 1

    if counter == 0:
        return

    status = 2 if counter >= 3 else 1
    if counter > 1:
        message = f'Last {counter} backups failed'
    else:
        message = 'Last backup failed'
    die(status, message)


def check_backup_age(backups, age_threshold=1):
    """
    Check that the last backup is not too old.
    """
    # To avoid false warnings the check is skipped if ClickHouse uptime is less then age threshold.
    if clickhouse_uptime().days < age_threshold:
        return

    checking_backup = None
    for i, backup in enumerate(backups):
        state = backup['state']
        if state == 'created' or (state == 'creating' and i == 0):
            checking_backup = backup
            break

    backup_age = get_backup_age(checking_backup)
    if backup_age.days < age_threshold:
        return

    if checking_backup['state'] == 'creating':
        message = f'Last backup was started {backup_age.days} days ago'
    else:
        message = f'Last backup was created {backup_age.days} days ago'
    die(1, message)


def check_backup_count(config: BackupConfig, backups: list) -> None:
    """
    Check that the number of backups is not too large.
    """
    max_count = config.retain_count + config.deduplication_age_limit.days + 1

    count = len(backups)
    if count > max_count:
        die(1, f'Too many backups exist: {count} > {max_count}')


def get_backups():
    """
    Get ClickHouse backups.
    """
    return json.loads(run('sudo ch-backup list -a -v --format json'))


def get_backup_age(backup):
    """
    Calculate and return age of ClickHouse backup.
    """
    backup_time = datetime.strptime(backup['start_time'], DATE_FORMAT)
    return datetime.now(timezone.utc) - backup_time


def clickhouse_uptime():
    """
    Get uptime of ClickHouse server.
    """
    seconds = int(run('clickhouse-client --readonly 1 -q "SELECT uptime()"'))
    return timedelta(seconds=seconds)


def run(command, data=None):
    """
    Run the command and return its output.
    """
    proc = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    encoded_data = data.encode() if data else None

    stdout, stderr = proc.communicate(input=encoded_data)

    if proc.returncode:
        raise RuntimeError(f'Command "{command}" failed with code {proc.returncode}')

    return stdout.decode()
