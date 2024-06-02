import socket
import threading
import argparse
import logging
from dataclasses import dataclass, field
import time
from typing import Dict, List, Tuple
from utils.format_log import setup_logging
from utils.utils import encode_resp, decode_resp

setup_logging(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RedisServer:
    '''A basic implementation of a Redis-like server supporting basic commands and master-slave replication.'''
    
    CACHE: Dict[str, str] = field(default_factory=dict)
    TTL: Dict[str, int] = field(default_factory=dict)
    PORT: int = 6379
    shutdown_event: threading.Event = threading.Event()
    SLAVES: List[socket.socket]= field(default_factory=list)
    
    role: str = "master"
    master_replid: str = "8371b4fb1155b71f4a04d3e1bc3e18c4a990aeeb"
    master_repl_offset: int = 0
    master_host: str = "localhost"
    master_port: int = 6379
    master_socket: socket.socket = None

    def start_server(self):
        '''Starts the slave server, listening for incoming connections and performing the initial handshake with the master server.'''
        self.shutdown_event.clear()
        server_socket = socket.create_server(("0.0.0.0", self.PORT), reuse_port=True)
        logger.info(f"{self.role.capitalize()} Server listening on port {self.PORT}")

        if self.role == "slave":
            threading.Thread(target=self.handshake, daemon=True).start()


        while not self.shutdown_event.is_set():
            try:
                server_socket.settimeout(1)
                connection, address = server_socket.accept()
                logger.info(f"Accepted connection from {address}")
                threading.Thread(target=self.handle_client, args=(connection, address), daemon=True).start()
            except socket.timeout:
                continue

    def shutdown(self):
        self.shutdown_event.set()
        logger.info("Server shutdown initiated")

    def handle_client(self, connection, address):
        '''Handles communication with a connected client, processing commands and returning appropriate responses.'''
            
        try:
            while not self.shutdown_event.is_set():
                data = connection.recv(4096)

                if not data:
                    break
                
                logger.debug(f"{self.role.capitalize()} Received data: {data}")
                
                all_commands = []
                # Split multiple lists into individual commands
                if data.count(b'*') > 1:
                    commands = data.split(b'*')
                    for cmd in commands:
                        if not cmd or not isinstance(cmd, list):
                            continue
                        tmp, _ = decode_resp(b'*' + cmd)
                        all_commands.append(tmp)
                else:
                    tmp, _ = decode_resp(data)
                    all_commands.append(tmp)

                logger.debug(f"Decoded commands: {all_commands}")
                for command in all_commands:
                    if not command:
                        continue
                    for i in range(len(command)):
                        if isinstance(command[i], bytes):
                            command[i] = command[i].decode()
                    logger.info(f"Received command: {command}")
                    response = None
                    cmd_type = command[0].lower() if type(command[0]) is str else command[0]

                    if cmd_type == 'ping':
                        logger.debug("Sending PONG")
                        response = encode_resp('PONG')
                    elif cmd_type == 'echo':
                        logger.debug(f"Echoing back {command[1]}")
                        response = encode_resp(command[1].encode())
                    elif cmd_type == 'set':
                        key: str = str(command[1])
                        value: str = str(command[2])
                        logger.debug(f"Setting key {key} to value {value}")
                        self.CACHE[key] = value

                        if len(command) > 3 and command[3].lower() == 'px':
                            logger.debug(f"Setting TTL for key {key} to {command[4]} milliseconds")
                            self.TTL[key] = time.time() + int(command[4]) / 1000

                        if connection is not self.master_socket:
                            response = encode_resp('OK')
                        
                        if self.role == "master":
                            for socket in self.SLAVES:
                                logger.debug(f"Sending {command} to slave at {socket.getpeername()}")
                                try:
                                    socket.sendall(encode_resp(command))
                                except Exception as e:
                                    logger.error(f"Error sending to slave: {e}")
                                    socket.close()
                                    self.SLAVES.remove(socket)
                    elif cmd_type == 'del':
                        key: str = str(command[1])
                        
                        if key in self.CACHE:
                            del self.CACHE[key]
        
                            if key in self.TTL:    
                                del self.TTL[key]

                            response = encode_resp(1)
                            logger.debug(f"Deleting key {key}")
                        else:
                            logger.debug(f"No key {key} to delete")
                            response = encode_resp(0)
                    elif cmd_type == 'get':
                        logger.debug(f"Getting key {command[1]}")
                        if command[1] in self.TTL and self.TTL[command[1]] < time.time():
                            del self.CACHE[command[1]]
                            del self.TTL[command[1]]
                        value = self.CACHE.get(command[1], None)
                        logger.debug(f"Value for key {command[1]} is {value}")
                        response = encode_resp(value.encode() if value is not None else None)
                    elif cmd_type == 'info':
                        logger.debug(f"Sending server info role:{self.role}, connected_slaves:{len(self.SLAVES)}, master_replid:{self.master_replid}, master_repl_offset:{self.master_repl_offset}")
                        response = encode_resp(f"role:{self.role}, connected_slaves:{len(self.SLAVES)}, master_replid:{self.master_replid}, master_repl_offset:{self.master_repl_offset}")
                    elif cmd_type == 'replconf':
                        if command[1].lower() == "listening-port":
                            logger.debug(f"Received REPLCONF listening-port {command[2]}")
                            self.SLAVES.append(connection)
                            logger.debug(f"Added slave {address} to list of slaves {self.SLAVES}")
                            response = encode_resp('OK')
                        elif command[1].lower() == "capa":
                            response = encode_resp('OK')
                        elif command[1].lower() == "getack":
                            logger.debug(f"Received ACK from slave {address}")
                            response = encode_resp(['REPLECONF','ACK',0])
                        else:
                            logger.debug(f"Received unknown REPLCONF command: {command}")
                            response = encode_resp('OK')
                    elif cmd_type == 'psync':
                        if command[1] == "?":
                            response = encode_resp(f"FULLRESYNC {self.master_replid} {self.master_repl_offset}")
                            rdb_hex = "524544495330303131fa0972656469732d76657205372e322e30fa0a72656469732d62697473c040fa056374696d65c26d08bc65fa08757365642d6d656dc2b0c41000fa08616f662d62617365c000fff06e3bfec0ff5aa2"
                            rdb_content = bytes.fromhex(rdb_hex)
                            length = len(rdb_content)
                            header = f"${length}\r\n".encode()
                            logger.debug("Sending RDP file to SLAVE")
                            response += header + rdb_content
                    elif cmd_type == 'fullresync':
                        logger.debug("Receiving RDB file from master")
                    elif cmd_type == 'exists':
                        key: str = str(command[1])
                        logger.debug(f"Checking if key {key} exists, it {"does" if key in self.CACHE else "does not"}")
                        response = encode_resp(1 if key in self.CACHE else 0)
                    elif cmd_type == 'shutdown':
                        logger.info("Shutting down server")
                        self.shutdown()
                        response = encode_resp('OK')

                    elif cmd_type == 'unknown':
                        logger.debug("Recieved unknown command")
                        response = encode_resp(None)
                    elif cmd_type == 'ignore':
                        continue
                    else:
                        continue
                    
                    if response:
                        connection.sendall(response)
        except ConnectionRefusedError:
            logger.error(f"Connection refused by {address}")
        except ConnectionResetError:
            logger.warning(f"Connection reset by {address}")
        except Exception as e:
            logger.error(f"{self.role} Error occured handling: {e}")

        finally:
            connection.close()

    def handshake(self):
        '''Performs the initial handshake with the master server to establish replication.'''
    
        while not self.shutdown_event.is_set():
            try:
                logger.info(f"Connecting to master at {self.master_host}:{self.master_port}")
                self.master_socket = master_socket = socket.create_connection((self.master_host, self.master_port))
                logger.info("Sending PING to master")
                master_socket.sendall(encode_resp(["PING"]))
                response, _ = decode_resp(master_socket.recv(4096))
                logger.info(f"Received from master: {response}")

                if response == "PONG":
                    logger.info("Sending REPLCONF port to master")
                    master_socket.sendall(encode_resp(["REPLCONF", "listening-port", str(self.PORT)]))
                    response, _ = decode_resp(master_socket.recv(4096))
                    logger.info(f"Received from master: {response}")
                    logger.info("Sending REPLCONF capa to master")
                    master_socket.sendall(encode_resp(["REPLCONF", "capa", "eof", "capa", "psync2"]))
                    response, _ = decode_resp(master_socket.recv(4096))
                    logger.info(f"Received from master: {response}")

                    if response == "OK":
                        logger.info("Sending PSYNC to master")
                        master_socket.sendall(encode_resp(["PSYNC", "?", "-1"]))
                        logger.info("Handshake complete")
                        self.handle_client(master_socket, (self.master_host, self.master_port))
            except Exception as e:
                logger.error(f"Error in handshake: {e}")
                time.sleep(5)  # Wait before trying again

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
    # Close all slave connections
    if server.role == "master":
            for sock in server.SLAVES:
                sock.close()
            server.SLAVES.clear()
            
    if server.master_socket:
        server.master_socket.close()

if __name__ == "__main__":
    import sys
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nExiting...")
        sys.exit(0)
