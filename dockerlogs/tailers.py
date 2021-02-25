#!/usr/bin/python3

from dataclasses import dataclass, field
import subprocess
import json
import select
from os import path
from socket import gethostname
import shlex
from time import time

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

    def __del__(self):
        logger.debug(f"tailer for {self.fname} deleted")


    def start_tailer(self):
        ps = subprocess.Popen(
            ['tail', '-F', self.fname],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE
        )
        return ps

    def parse_loguru_plain(self, log):
        s = log.split('|')
        name, message = s[2].split(" - ", 1)
        return {'logger_timestamp': s[0].strip(),
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


    def parse_redis(self, log):
        s = log.split(" * ", 1)
        if len(s) == 1:
            s = log.split(" # ", 1)
        return {'message': s[1].strip(),
                'logger_timestamp': s[0].strip() }

    def parse_jellyfin(self, log):
        s = log.split(" ", 3)
        logger_name, message = s[3].split(": ", 1)
        _severity = s[1][1:-1]
        if _severity == "INF":
            severity = "INFO"
        elif _severity == "ERR":
            severity = "ERROR"
        elif _severity == "WRN":
            severity = "WARN"
        else:
            severity = _severity

        return {'severity': severity,
                'message': message.strip(),
                'logger_timestamp': s[0][1:-1],
                'logger_raw': log,
                'logger_name': logger_name.strip()}

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
        try:
            parsed = self.parse_format(log)
        except Exception as e:
            print(e)
            print(log)
            print("---")
            parsed = self.parse_plain(log)
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

        if self.format == "json":
            self.parse_format = self.parse_json
        elif self.format == "loguru_plain":
            self.parse_format = self.parse_loguru_plain
        elif self.format == "nextcloud":
            self.parse_format = self.parse_nextcloud_apache
        elif self.format == "jellyfin":
            self.parse_format = self.parse_jellyfin
        elif self.format == "redis":
            self.parse_format = self.parse_redis
        else:
            self.parse_format = self.parse_plain

        # tail the *-json.log file in /var/lib/docker/containers/{id}
        logname = f"{self.full_id}-json.log"
        self.fname = path.join(CONTAINERS_DIR, self.full_id, logname)

        try:
            image = self.container.image.tags[0]
        except IndexError:
            image = self.container.image.id
        self.envelope = {
            'type': 'dockerlogs',
            'container_name': self.container.name,
            'container_id': self.container.id,
            'container_short_id': self.container.short_id,
            'container_image': image,
            **self.base_envelope
        }
        self.ps = None
        self.stdout = None
        self.fileno = None

    def start(self):
        if self.ps is not None:
            raise ValueError(f"tailer already running: {self.ps}")
        self.ps = self.start_tailer()
        self.stdout = self.ps.stdout
        self.fileno = self.ps.stdout.fileno()




@dataclass
class LogTailers:
    tailers: dict[int, BaseLogTailer] = field(default_factory=dict)

    def __post_init__(self):
        self.docker_client = docker.from_env()
        self.poller = select.poll()

        self.update_at = 0.0
        self.update_tailers()

    def update_tailers(self):
        now = time()
        if now > self.update_at:
            logger.debug("updating tailers")
            self.update_docker_tailers()
            self.update_at = now + 6

    def add_tailer(self, tailer):
        tailer.start()
        self.tailers[tailer.fileno] = tailer
        self.poller.register(tailer.stdout, select.POLLIN)
        logger.info(f"added tailer for '{tailer.name}', container '{tailer.short_id}'")


    def update_docker_tailers(self):
        # dict {'container_id': docker.Container }
        containers = {a.id: a for a in self.docker_client.containers.list()}

        # dict {'container_id': dockerlogs.DockerContainerTailer}
        tailed_ids = {tailer.full_id: tailer for _fileno, tailer in self.tailers.items()}

        new = set(containers.keys()) - set(tailed_ids.keys())
        dead = set(tailed_ids.keys()) - set (containers.keys())

        for full_id in new:
            item = containers[full_id]
            self.add_tailer(DockerContainerTailer(item))

        for full_id in dead:
            item = containers[full_id]
            del self.tailers[item.fileno]
            logger.info(f"dead containter: {item.name} ({item.short_id})")


    def iter_lines(self):
        while True:
            p = self.poller.poll(1*1000)
            for item in p:
                tailer = self.tailers[item[0]]
                yield tailer.parse_line()
            self.update_tailers()


    def run(self, output):
        for logline in self.iter_lines():
            output.handle(logline)
