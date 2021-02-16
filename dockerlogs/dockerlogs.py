#!/usr/bin/python3

from dataclasses import dataclass, field

from os import path
import select


HOSTNAME = gethostname()


def test():
    dl = DockerLogReader()
    for line in dl.readlines():
        print(line)
