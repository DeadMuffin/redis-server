import logging
import time
import socket
from utils.utils import encode_resp, decode_resp

logger = logging.getLogger(__name__)

def handle_client(server, connection, address):
    '''Handles communication with a connected client, processing commands and returning appropriate responses.'''
        
    try:
        while server.running:
            data = connection.recv(4096)

            if not data:
                break
            
            logger.debug(f"Received data: {data}")
            
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
                for i in range(len(command)):
                    if isinstance(command[i], bytes):
                        command[i] = command[i].decode()
                logger.info(f"Received command: {command}")
                response = encode_resp(None)
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
                    server.CACHE[key] = value

                    if len(command) > 3 and command[3].lower() == 'px':
                        logger.debug(f"Setting TTL for key {key} to {command[4]} milliseconds")
                        server.TTL[key] = time.time() + int(command[4]) / 1000

                    if server.role == "master":
                        response = encode_resp('OK')
                        for slave in server.SLAVES:
                            slave_host, slave_port = slave
                            logger.debug(f"Sending {command} to slave at {slave_host}:{slave_port}")
                            slave_socket = socket.create_connection((slave_host, int(slave_port)))
                            slave_socket.sendall(encode_resp(command))
                            slave_socket.close()
                elif cmd_type == 'del':
                    key: str = str(command[1])
                    
                    if key in server.CACHE:
                        del server.CACHE[key]
    
                        if key in server.TTL:    
                            del server.TTL[key]

                        response = encode_resp(1)
                        logger.debug(f"Deleting key {key}")
                    else:
                        logger.debug(f"No key {key} to delete")
                        response = encode_resp(0)
                elif cmd_type == 'get':
                    logger.debug(f"Getting key {command[1]}")
                    if command[1] in server.TTL and server.TTL[command[1]] < time.time():
                        del server.CACHE[command[1]]
                        del server.TTL[command[1]]
                    value = server.CACHE.get(command[1], None)
                    logger.debug(f"Value for key {command[1]} is {value}")
                    response = encode_resp(value.encode() if value is not None else None)
                elif cmd_type == 'info':
                    logger.debug(f"Sending server info role:{server.role}, connected_slaves:{len(server.SLAVES)}, master_replid:{server.master_replid}, master_repl_offset:{server.master_repl_offset}")
                    response = encode_resp(f"role:{server.role}, connected_slaves:{len(server.SLAVES)}, master_replid:{server.master_replid}, master_repl_offset:{server.master_repl_offset}")
                elif cmd_type == 'replconf':
                    if command[1].lower() == "listening-port":
                        logger.debug(f"Received REPLCONF listening-port {command[2]}")
                        server.SLAVES.append((address[0], command[2]))
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
                        response = encode_resp(f"FULLRESYNC {server.master_replid} {server.master_repl_offset}")
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
                    logger.debug(f"Checking if key {key} exists, it {"does" if key in server.CACHE else "does not"}")
                    response = encode_resp(1 if key in server.CACHE else 0)
                elif cmd_type == 'shutdown':
                    logger.info("Shutting down server")
                    server.shutdown()
                    response = encode_resp('OK')

                elif cmd_type == 'unknown':
                    logger.debug("Recieved unknown command")
                    response = encode_resp(None)
                elif cmd_type == 'ignore':
                    continue
                else:
                    continue

                connection.sendall(response)
    except ConnectionRefusedError:
        logger.error(f"Connection refused by {address}")
    except ConnectionResetError:
        logger.warning(f"Connection reset by {address}")
    except Exception as e:
        logger.error(f"Error occured handling: {e}")

    finally:
        connection.close()
