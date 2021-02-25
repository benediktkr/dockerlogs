#!/usr/bin/python3 -u

import sys

from dockerlogs.tailers import LogTailers
from dockerlogs.outputs import LogOutput
from dockerlogs import __version__
from itertools import cycle

from loguru import logger
import click

@click.command()
@click.option('--output-type', default="print",
              type=click.Choice(LogOutput.list_outputs()))
@click.option('--output-url')
@click.option('--debug/--no-debug')
def main(output_type, output_url, debug):
    if not debug:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    spinners = cycle(['|', '/', '-', '\\'])

    dockerlogs = LogTailers()
    output = LogOutput.get(output_type, output_url)

    logger.info("started")

    for logline in dockerlogs.iter_lines():
        output.handle(logline)
        print(next(spinners), end='\r')
