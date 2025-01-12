# asl-connection-hooks

A Python-based notification system for AllstarLink nodes that sends connection/disconnection alerts via Pushover.

## Description

[AllstarLink](https://www.allstarlink.org/) (ASL) is a VOIP Ham Radio application that allows linking of repeaters and radios. This script leverages ASL's built-in capability to execute scripts on node connections/disconnections to provide notifications and simple access control.

Features:
- Pushover notifications for node connections/disconnections
- Node blocking functionality
- Configurable node groups (personal, private, etc.)
- Integration with ASL's node database for detailed node information

## Requirements

- Python 3.7+
- PyYAML
- AllstarLink system

## Installation

1. Update your system:
```bash
sudo apt update && sudo apt upgrade
```

2. Install required packages:
```bash
sudo apt install python3-yaml
```

3. Clone or copy the script files to your desired location.

## Configuration

1. Create a `config.yaml` file based on the template below:

```yaml
nodes:
  my_nodes:
    - 12345
  private_nodes: []
  blocked_nodes: []
  echolink: null

paths:
  node_db: /var/lib/asterisk/astdb.txt

pushover:
  enabled: true
  api_token: your_api_token
  user_key: your_user_key
```

2. Configure AllstarLink:

Edit `/etc/asterisk/rpt.conf` and add these lines to your node stanzas:

```ini
connpgm = /usr/local/asl-connection-hooks/handle.py 1
discpgm = /usr/local/asl-connection-hooks/handle.py 0
```

## Testing

Grab the latest `astdb.txt` from [AllmonDB](https://allmondb.allstarlink.org/):

```bash
wget -O astdb.txt https://allmondb.allstarlink.org/astdb.txt
```

Test the script manually with:

```bash
python3 /usr/local/asl-connection-hooks/handle.py 1 12345 54321
```

This simulates node 54321 connecting to node 12345.
