#!/usr/bin/python3 -u

import sys

from dockerlogs.tailers import LogTailers
from dockerlogs.outputs import LogOutput
from dockerlogs import __version__

from loguru import logger
import click

logger.remove()

@click.command()
@click.option('--output-type', default="print",
              type=click.Choice(LogOutput.list_outputs()))
@click.option('--output-url')
def _dockertailer(output_type, output_url):

    dockerlogs = LogTailers()
    output = LogOutput.get(output_type, output_url)

    for logline in dockerlogs.iter_lines():
        output.handle(logline)

@click.option('--output-type', default="print",
              type=click.Choice(LogOutput.list_outputs()))
@click.option('--output-url')
@click.option('--file')
@click.option('--app-name')
def _filetailer(output_type, output_url, file, app_name):
    pass

def dockertailer():
    return _dockertailer(auto_envvar_prefix="DOCKERLOGS")

def filetailer():
    return _filetailer(auto_envvar_prefix="DOCKERLOGS")
