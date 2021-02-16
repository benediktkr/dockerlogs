#!/usr/bin/python3 -u

import sys

from dockerlogs.tailers import LogTailers
from dockerlogs.outputs import LogOutput
from dockerlogs import __version__

from loguru import logger
import click

@click.command()
@click.option('--output-type', default="print",
              type=click.Choice(LogOutput.list_outputs()))
@click.option('--output-url')
def cli(output_type, output_url):

    logger.info(f"dockerlogs v{__version__}")
    print(LogOutput.list_outputs())

    dockerlogs = LogTailers()
    output = LogOutput.get(output_type, output_url)

    for logline in dockerlogs.iter_lines():
        output.handle(logline)

def main():
    logger.remove()
    #logger.add(sys.stdout, serialize=True)
    return cli(auto_envvar_prefix="DOCKERLOGS")
