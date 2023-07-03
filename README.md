# Intelligram Bot

## About The Project
A personal telegram bot application built with python 

## Installation

### Docker Compose
```yaml
services:
    intelligram-bot:
        image: ghcr.io/klementng/intelligram-bot:latest
        container_name: intelligram-bot
        environment:
            - BOT_TOKEN=
        ports:
            - 88:88
        volumes:
            - /path/to/data:/config
        restart: unless-stopped
```

### Docker Cli

```sh
docker create \
  --name=intelligram-bot \
  -e - BOT_TOKEN= \
  --restart unless-stopped \
  ghcr.io/klementng/intelligram-bot:latest
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Configuration

<table>
  <tr>
    <th>Environment Variable</th>
    <th>Description</th>
    <th>Default Value</th>
  </tr>
  
  <tr>
    <td>BOT_TOKEN</td>
    <td>Telegram bot API token (required)</td>
    <td>null</td>
  </tr>

  <tr>
    <td>BOT_CONFIG_DIR</td>
    <td>Working directory for storing configuration & data (optional)</td>
    <td>/config</td>
  </tr>

  <tr>
    <td>BOT_DB_PATH</td>
    <td>Path to SQlite database file (optional)</td>
    <td>{BOT_CONFIG_DIR}/data/data.db</td>
  </tr>

  <tr>
    <td>BOT_SERVER_HOSTNAME</td>
    <td>Hostname or IP for bot (optional)</td>
    <td>(current public ip address)</td>
  </tr>


  <tr>
    <td>BOT_SERVER_PUBLISHED_PORT</td>
    <td>Published for telegram server to send request to. Allowed ports:443, 80, 88 and 8443 (optional)</td>
    <td>88</td>
  </tr>

  <tr>
    <td>BOT_SERVER_PORT</td>
    <td>Internal Server Port (optional)</td>
    <td>88</td>
  </tr>

  <tr>
    <td>BOT_SERVER_CERT_PATH</td>
    <td>Path to signed ssl public cert (optional). Both BOT_SERVER_CERT_PATH & BOT_SERVER_KEY_PATH must be set. Else an self-signed cert & key will be generated using openssl at {BOT_CONFIG_DIR}/ssl/cert.pem & {BOT_CONFIG_DIR}/ssl/key.pem </td>
    <td>null</td>
  </tr>

  <tr>
    <td>BOT_SERVER_KEY_PATH</td>
    <td>see above</td>
    <td>null</td>
  </tr>

</table>
