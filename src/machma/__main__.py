
import code
import logging
import sys
from typing import Optional

import click

from machma.tests.dummy_data import create_dummy_data
from . import api, bot, db
from .bot import config

LOGGER = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.option('--ethereal-db', is_flag=True, help='Use an ethereal in-memory DB. Implies --create-tables.')
@click.option('--dummy-data', is_flag=True, help='Initialize the ethereal DB with dummy data.')
@click.option('--create-tables', is_flag=True, help='Create tables when initializing the DB connection.')
@click.option('--sql-debug', is_flag=True, help='Echo SQL statements as they get executed.')
@click.pass_context
def cli(
    ctx: click.Context,
    ethereal_db: bool,
    dummy_data: bool,
    create_tables: bool,
    sql_debug: bool,
) -> None:
    """
    Machma10 Telegram Bot.

    Run without a sub-command to start the bot.
    """

    logging.basicConfig(level=logging.INFO)

    if ethereal_db:
        config.database_url = 'sqlite:///:memory:'
        create_tables = True
    if dummy_data:
        if not ethereal_db:
            LOGGER.error('--dummy-data requires that the --ethereal-db option is present.')
            sys.exit(1)

    db.initialize_db(config.database_url, create_tables=create_tables, echo=sql_debug)
    if dummy_data:
        with db.make_session():
            create_dummy_data()

    if not ctx.invoked_subcommand:
        bot.run()


@cli.command()
@click.option('-c', help='Execute the specified Python code and exit.')
def repl(c: Optional[str]):
    """
    Start an interactive interpreter session with the database API.
    """

    local = {k: getattr(db, k) for k in db.__all__}
    local['session'] = db.session
    local['api'] = api

    with db.make_session():
        if c:
            exec(c, local, local)  # pylint: disable=exec-used
        else:
            code.interact(local=local)


if __name__ == '__main__':
    cli()  # pylint: disable=no-value-for-parameter
