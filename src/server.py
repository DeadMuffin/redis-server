import socket
import threading
import argparse
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
from replication import handshake
from client_handler import handle_client
from utils.format_log import setup_logging

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RedisServer:
    '''A basic implementation of a Redis-like server supporting basic commands and master-slave replication.'''
    
    CACHE: Dict[str, str] = field(default_factory=dict)
    TTL: Dict[str, int] = field(default_factory=dict)
    SLAVES: List[Tuple[str, str]] = field(default_factory=list)
    PORT: int = 6379
    role: str = "master"
    master_replid: str = "8371b4fb1155b71f4a04d3e1bc3e18c4a990aeeb"
    master_repl_offset: int = 0
    master_host: str = "localhost"
    master_port: int = 6379
    running: bool = True
    server_socket: socket.socket = None
 
    def start_server(self):
        '''Starts the slave server, listening for incoming connections and performing the initial handshake with the master server.'''

        server_socket = socket.create_server(("0.0.0.0", self.PORT), reuse_port=True)
        logger.info(f"{self.role.capitalize()} Server listening on port {self.PORT}")
        self.server_socket = server_socket

        if self.role == "slave":
            threading.Thread(target=handshake, args=(self,)).start()


        while self.running:
            try:
                server_socket.settimeout(1)
                connection, address = server_socket.accept()
                logger.info(f"Accepted connection from {address}")
                threading.Thread(target=handle_client, args=(self, connection, address)).start()
            except socket.timeout:
                continue

    def shutdown(self):
        self.running = False
        self.server_socket.close()
        logger.info("Server shutdown initiated")



def main():
    parser = argparse.ArgumentParser(description="Simple Redis server")
    parser.add_argument('--port', type=int, default=6379, help='Port number to use')
    parser.add_argument('--replicaof', type=str, help='Master host and port number to use for slave')
    args = parser.parse_args()

    if args.replicaof is None:
        server = RedisServer(PORT=args.port, role="master")
    else:
        master_host, master_port = args.replicaof.split()
        server = RedisServer(PORT=args.port, role="slave", master_host=master_host, master_port=int(master_port))

    server.start_server()

if __name__ == "__main__":
    import sys
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
