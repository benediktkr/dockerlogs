#!/usr/bin/python3

from dataclasses import dataclass, field
import subprocess
import json
import select
from os import path
from socket import gethostname
import shlex

import docker
from docker.models.containers import Container
from loguru import logger

HOSTNAME=gethostname()
CONTAINERS_DIR = "/var/lib/docker/containers"

@dataclass
class BaseLogTailer:

    base_envelope = {
        'hostname': HOSTNAME,
    }

    def start_tailer(self):
        ps = subprocess.Popen(
            ['tail', '-F', self.fname],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE
        )
        return ps

    def parse_loguru_plain(self, log):
        s = log.split('|')
        name, message = s[2].split(" - ", 1)
        return {'loguru_timestamp': s[0].strip(),
                'severity': s[1].strip(),
                'logger_name': name.strip(),
                'message': message.strip(),
                }

    def parse_json(self, log):
        try:
            jlog = json.loads(log)
            level = jlog.get('level', 'UNKNOWN')
            return {'message': jlog[self.json_msg_key],
                    'severity': level,
                    'json': jlog}
        except json.decoder.JSONDecodeError as e:
            return {'message': log,
                    'parse_error': str(e)}

    def parse_nextcloud_apache(self, log):

        s = shlex.split(log)
        try:
            return {
                'message': log,
                'nextcloud': {
                    'ip': s[0],
                    'unknown_1': s[1],
                    'user': s[2],
                    'time': " ".join(s[3:5]),
                    'request': s[5],
                    'returncode': s[6],
                    'bytes': s[7],
                    'unknown_8': s[8],
                    'user_agent': s[9],
                }
            }
        except IndexError as e:
            print(log)
            return {'message': log,
                    'parser_error': str(e)}

    def parse_plain(self, log):
        return {'message': log }

    def parse_log(self, jline):
        log = jline['log'].strip()
        parsed = self.parse_format(log)
        return {**parsed, **self.envelope, '@timestamp': jline['time']}

    def readline(self):
        return self.stdout.readline()

    def parse_line(self, line=None):
        if not line:
             line = self.readline()

        jline = json.loads(line)
        parsed = self.parse_log(jline)

        return json.dumps(parsed)


@dataclass
class FileTailer(BaseLogTailer):
    fname: str
    app_name: str
    def __post_init__(self):
        self.name = path.split(self.fname)[1]

        self.envelope = {
            'app_name': self.app_name,
            'type': 'filetailer'
        }

@dataclass
class DockerContainerTailer(BaseLogTailer):
    container: Container

    def __post_init__(self):
        self.name = self.container.name
        self.full_id = self.container.id
        self.short_id = self.container.short_id

        labels = self.container.labels
        self.format = labels.get('dockerlogs_format', '').lower()
        self.is_json = self.format == "json"
        self.json_msg_key = labels.get('dockerlogs_json_msg_key', "message")

        if format == "json":
            self.parse_format = self.parse_json
        elif format == "loguru_plain":
            self.parse_format = self.parse_loguru_plain
        elif format == "nextcloud":
            self.parse_format = self.parse_nextcloud_apache
        else:
            self.parse_format = self.parse_plain

        # tail the *-json.log file in /var/lib/docker/containers/{id}
        logname = f"{self.full_id}-json.log"
        self.fname = path.join(CONTAINERS_DIR, self.full_id, logname)

        self.ps = self.start_tailer()
        self.stdout = self.ps.stdout
        self.fileno = self.ps.stdout.fileno()

        self.envelope = {
            'type': 'dockerlogs',
            'container_name': self.container.name,
            'container_id': self.container.id,
            'container_short_id': self.container.short_id,
            'container_image': self.container.image.tags[0],
            **self.base_envelope
        }


@dataclass
class LogTailers:
    tailers: dict[int, BaseLogTailer] = field(default_factory=dict)

    def __post_init__(self):
        self.docker_client = docker.from_env()
        self.poller = select.poll()

        self.update_tailers()

    def update_tailers(self):
        self.add_docker_tailers()

    def add_tailer(self, tailer):
        self.tailers[tailer.fileno] = tailer
        self.poller.register(tailer.stdout, select.POLLIN)


    def add_docker_tailers(self):
        containers = self.docker_client.containers.list()
        for c in containers:
            self.add_tailer(DockerContainerTailer(c))


    def iter_lines(self):
        while True:
            p = self.poller.poll(1*1000)
            for item in p:
                tailer = self.tailers[item[0]]
                yield tailer.parse_line()
