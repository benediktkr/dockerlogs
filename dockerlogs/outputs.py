#!/usr/bin/python3

import sys
import socket
from urllib.parse import urlparse, ParseResult
from logging.handlers import SysLogHandler

from dataclasses import dataclass, field

from loguru import logger

@dataclass
class LogOutput:
    def handle(self, logline):
        raise NotImplementedError

    @classmethod
    def get(cls, output_type, output_url=""):
        output = urlparse(output_url)
        if output_type == "print":
            return PrintLogOutput()
        elif output_type == "udp":
            return UdpLogOutput(output)
        elif output_type == "syslog":
            return SyslogLogOutput(output)

    @classmethod
    def list_outputs(cls):
        class_names = [cls.__name__ for cls in cls.__subclasses__()]
        cutoff = len(cls.__name__)
        return [c[:-cutoff].lower() for c in class_names]

@dataclass
class PrintLogOutput(LogOutput):

    def __post_init__(self):
        logger.add(sys.stdout, format="{message}",
                   filter=lambda x: "print_output" in x['extra'])

    def handle(self, logline):
        logger.bind(print_output=True).info(logline)

@dataclass
class SyslogLogOutput(LogOutput):
    # TODO: this doesnt work
    output: ParseResult
    def __post_init__(self):
        if not self.output.scheme == "udp":
            raise ValueError("please specify syslog url with udp://")
        self.host, port = self.output.netloc.split(":")
        self.port = int(port)
        syslog = SysLogHandler(address=(self.host, self.port))
        logger.add(syslog, format="{message}",
                   filter=lambda x: "syslog_output" in x['extra'])

    def handle(self, logline):
        logger.bind(syslog_output=True).info(logline)


@dataclass
class UdpLogOutput(LogOutput):
    output: ParseResult
    def __post_init__(self):
        if not self.output.scheme == "udp":
            raise ValueError("please specify url with udp://")
        self.host, port = self.output.netloc.split(":")
        self.port = int(port)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, logline):
        self.sock.sendto(logline.encode(), (self.host, self.port))

    def handle(self, logline):
        self.send(logline)
