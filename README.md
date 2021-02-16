# dockerlogs

Home-grown log shipper to logstash. Found the landscape to be too confusing, rolled my own

## configuration

```

Options:
  --output-type [print|syslog|udp]
  --output-url TEXT
```
Example:

```
dockerlogs --output-type udp --output-url udp://logstash.example.com:5000
```

Can also be configured with environment variables, prefixed with `DOCKERLOGS_`.

Example:

```
DOCKERLOGS_DOCKER=1
DOCKERLOGS_OUTPUT_TYPE=udp
DOCKERLOGS_OUTPUT_URL=udp://logstash.example.com:5000
dockerlogs
```
