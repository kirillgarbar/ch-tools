import json

import click

from ch_tools.chadmin.cli.object_storage_group import (
    ORPHANED_OBJECTS_SIZE_FIELD,
    STORE_STATE_PATH,
)
from ch_tools.common.result import CRIT, OK, WARNING, Result


@click.command("orphaned-objects")
@click.option(
    "-c",
    "--critical",
    "crit",
    type=int,
    default=10 * 1024**3,
    help="Critical threshold.",
)
@click.option(
    "-w",
    "--warning",
    "warn",
    type=int,
    default=100 * 1024**2,
    help="Warning threshold.",
)
@click.pass_context
def orphaned_objects_command(
    _: click.Context,
    crit: int,
    warn: int,
) -> Result:
    try:
        with open(STORE_STATE_PATH, mode="r", encoding="utf-8") as file:
            total_size = json.load(file).get(ORPHANED_OBJECTS_SIZE_FIELD)
    except FileNotFoundError:
        total_size = 0
    msg = f"Total size: {total_size}"
    if total_size >= crit:
        return Result(CRIT, msg)
    if total_size >= warn:
        return Result(WARNING, msg)
    return Result(OK, msg)
