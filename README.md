# dockerlogs

[![Build Status](https://jenkins.sudo.is/buildStatus/icon?job=ben%2Fopenldap-docker%2Fmaster&style=flat-square)](https://jenkins.sudo.is/job/ben/job/dockerlogs/job/master/)

Home-grown log shipper to logstash. Found the landscape to be too confusing, rolled my own

## configuration

```
Usage: dockerlogs [OPTIONS]

Options:
  --output-type [print|syslog|udp]
  --output-url TEXT
  --debug / --no-debug
  --help                          Show this message and exit.

```
Example:

```
dockerlogs --output-type udp --output-url udp://logstash.example.com:5000
```

Can also be configured with environment variables, prefixed with `DOCKERLOGS_`.

Example:

```
DOCKERLOGS_OUTPUT_TYPE=udp
DOCKERLOGS_OUTPUT_URL=udp://logstash.example.com:5000
dockerlogs
```
