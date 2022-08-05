from click import argument, group, option, pass_context
from cloud.mdb.cli.common.formatting import print_response
from cloud.mdb.clickhouse.tools.chadmin.internal.table import get_table, get_tables

from cloud.mdb.clickhouse.tools.chadmin.internal.utils import execute_query


@group('table')
def table_group():
    """Table management commands."""
    pass


@table_group.command('get')
@argument('database')
@argument('table')
@option('--active-parts', is_flag=True, help='Account only active data parts.')
@pass_context
def get_command(ctx, database, table, active_parts):
    """
    Get table.
    """
    table = get_table(ctx, database, table, active_parts=active_parts)
    print_response(ctx, table, default_format='yaml')


@table_group.command('list')
@option('--database', help='Filter tables to output by the specified database.')
@option('-t', '--table', help='Output only the specified table.')
@option('--exclude-table', help='Do not output the specified table.')
@option('--engine', help='Filter tables to output by the specified engine.')
@option('--format', default='PrettyCompact')
@option('--active-parts', is_flag=True, help='Account only active data parts.')
@option('-v', '--verbose', is_flag=True)
@option('-l', '--limit', type=int, default=1000, help='Limit the max number of objects in the output.')
@pass_context
def list_command(ctx, database, table, exclude_table, engine, active_parts, verbose, format, limit):
    """
    List tables.
    """
    tables = get_tables(
        ctx,
        database=database,
        table=table,
        exclude_table=exclude_table,
        engine=engine,
        active_parts=active_parts,
        verbose=verbose,
        limit=limit,
    )
    print_response(ctx, tables, default_format='table')


@table_group.command('columns')
@argument('database')
@argument('table')
@pass_context
def columns_command(ctx, database, table):
    query = """
        SELECT
            name,
            type,
            default_kind,
            default_expression,
            formatReadableSize(data_compressed_bytes) "disk_size",
            formatReadableSize(data_uncompressed_bytes) "uncompressed_size",
            marks_bytes
        FROM system.columns
        WHERE database = '{{ database }}'
          AND table = '{{ table }}'
        """
    print(execute_query(ctx, query, database=database, table=table))


@table_group.command('delete')
@pass_context
@option('-n', '--dry-run', is_flag=True)
@option('-a', '--all', is_flag=True)
@option('--database')
@option('-t', '--table')
@option('--exclude-table')
@option('--cluster')
def delete_command(ctx, dry_run, all, database, table, exclude_table, cluster):
    """
    Delete one or several tables.
    """
    if not any((all, database, table)):
        ctx.fail('At least one of --all, --database and --table options must be specified.')

    for t in get_tables(ctx, database=database, table=table, exclude_table=exclude_table):
        query = """
            DROP TABLE `{{ database }}`.`{{ table }}`
            {% if cluster %}
            ON CLUSTER '{{ cluster }}'
            {% endif %}
            NO DELAY
            """
        execute_query(ctx, query, database=t['database'], table=t['table'], cluster=cluster, echo=True, dry_run=dry_run)


@table_group.command('detach')
@pass_context
@option('-n', '--dry-run', is_flag=True)
@option('-a', '--all', is_flag=True)
@option('--database')
@option('-t', '--table')
@option('--engine', help='Filter tables to detach by the specified engine.')
@option('--exclude-table')
@option('--cluster')
def detach_command(ctx, dry_run, all, database, table, engine, exclude_table, cluster):
    """
    Detach one or several tables.
    """
    if not any((all, database, table)):
        ctx.fail('At least one of --all, --database or --table options must be specified.')

    for t in get_tables(ctx, database=database, table=table, engine=engine, exclude_table=exclude_table):
        query = """
            DETACH TABLE `{{ database }}`.`{{ table }}`
            {% if cluster %}
            ON CLUSTER '{{ cluster }}'
            {% endif %}
            NO DELAY
            """
        execute_query(ctx, query, database=t['database'], table=t['table'], cluster=cluster, echo=True, dry_run=dry_run)


@table_group.command('get-statistics')
@option('--database')
@pass_context
def get_statistics_command(ctx, database):
    query = """
        SELECT count() count
        FROM system.query_log
        WHERE type != 1
        AND query LIKE '%{{ table }}%'
    """

    for t in get_tables(ctx, database=database):
        stats = execute_query(ctx, query, table=t['table'], format='JSON')['data'][0]
        print('{0}: {1}'.format(t['table'], stats['count']))