#!/usr/bin/env python3
import csv
import logging
import os
import yaml
from argparse import ArgumentParser
from dataclasses import dataclass
from datetime import datetime
from http.client import HTTPSConnection
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlencode

DEFAULT_CONFIG_PATH = '/etc/asl-connection-hooks/config.yaml'

EMOJI_CONNECTED = "🔌"
EMOJI_DISCONNECTED = "❌"
EMOJI_BLOCKED = "🚫"

@dataclass
class NodeConfig:
    my_nodes: List[int]
    private_nodes: List[int]
    blocked_nodes: List[int]
    echolink: Optional[int]

@dataclass
class PushoverConfig:
    enabled: bool
    api_token: str
    user_key: str

@dataclass
class PathConfig:
    node_db: Path

class Config:
    def __init__(self, config_path: str = DEFAULT_CONFIG_PATH):
        self.config_path = config_path
        self._load_config()

    def _load_config(self) -> None:
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)

            nodes = config['nodes']
            self.nodes = NodeConfig(
                my_nodes=[int(x) for x in nodes['my_nodes']],
                private_nodes=[int(x) for x in nodes['private_nodes']],
                blocked_nodes=[int(x) for x in nodes['blocked_nodes']],
                echolink=int(nodes['echolink']) if nodes['echolink'] else None
            )

            self.pushover = PushoverConfig(**config['pushover'])
            self.paths = PathConfig(node_db=Path(config['paths']['node_db']))

        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required configuration key: {e}")

class NodeDatabase:
    def __init__(self, db_path: Path, delimiter: str = '|'):
        self.db_path = db_path
        self.delimiter = delimiter

    def get_node_info(self, node_number: int) -> str:
        try:
            with open(self.db_path, "r", encoding="Latin-1") as csvfile:
                reader = csv.reader(csvfile, delimiter=self.delimiter, quotechar="'")
                for line in reader:
                    if not line or line[0].startswith(';'):
                        continue
                    if node_number == int(line[0]):
                        return f"({line[1]} {line[2]} in {line[3]})"
            return "(unknown)"
        except Exception as e:
            logging.error(f"Error reading node database: {e}")
            return "(error reading db)"

class PushoverNotifier:
    def __init__(self, config: PushoverConfig):
        self.config = config

    def send(self, message: str) -> None:
        if not self.config.enabled:
            return

        logging.debug(f"Sending Pushover notification: {message}")
        try:
            conn = HTTPSConnection("api.pushover.net:443")
            conn.request(
                "POST",
                "/1/messages.json",
                urlencode({
                    "token": self.config.api_token,
                    "user": self.config.user_key,
                    "message": message,
                }),
                {"Content-type": "application/x-www-form-urlencoded"}
            )
            response = conn.getresponse()
            logging.debug(f"Pushover response status: {response.status}")
        except Exception as e:
            logging.error(f"Failed to send Pushover notification: {e}")

class NodeMonitor:
    def __init__(self, config: Config):
        self.config = config
        self.node_db = NodeDatabase(config.paths.node_db)
        self.notifier = PushoverNotifier(config.pushover)

    def handle_blocked_node(self, my_node: int, their_node: int) -> None:
        cmd = f'asterisk -rx "rpt fun {my_node} *1{their_node}"'
        os.system(cmd)
        
        status = (f"{EMOJI_BLOCKED} Blocked node {their_node} "
                 f"{self.node_db.get_node_info(their_node)} was auto disconnected from "
                 f"{my_node} {self.node_db.get_node_info(my_node)} at "
                 f"{datetime.now().strftime('%H:%M:%S')}")
        
        self.notifier.send(status)

    def handle_connection_status(self, conn_status: int, my_node: int, their_node: int) -> None:
        if (their_node in self.config.nodes.blocked_nodes):
            self.handle_blocked_node(my_node, their_node)
            return

        if (their_node in self.config.nodes.my_nodes or 
            their_node in self.config.nodes.private_nodes):
            return

        emoji = EMOJI_CONNECTED if conn_status == 1 else EMOJI_DISCONNECTED
        action = "connected to" if conn_status == 1 else "disconnected from"
        
        if my_node == self.config.nodes.echolink:
            target = f"Echolink ({my_node})"
        else:
            target = f"{my_node} {self.node_db.get_node_info(my_node)}"

        status = (f"{emoji} Node {their_node} {self.node_db.get_node_info(their_node)} "
                 f"{action} {target} at {datetime.now().strftime('%H:%M:%S')}")
        
        self.notifier.send(status)

def setup_logging(debug: bool = False) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def parse_args():
    parser = ArgumentParser(description='AllStar Node Connection Monitor')
    parser.add_argument('conn_status', type=int, help='Connection status (1=connected, 0=disconnected)')
    parser.add_argument('my_node', type=int, help='Local node number')
    parser.add_argument('their_node', type=int, help='Remote node number')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH, help='Path to config file')
    return parser.parse_args()

def main():
    args = parse_args()
    setup_logging(args.debug)
    
    try:
        config = Config(args.config)
        monitor = NodeMonitor(config)
        monitor.handle_connection_status(args.conn_status, args.my_node, args.their_node)
    except Exception as e:
        logging.error(f"Application error: {e}")
        raise

if __name__ == "__main__":
    main()
