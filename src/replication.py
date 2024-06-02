import logging
import socket

from utils.utils import encode_resp, decode_resp



logger = logging.getLogger(__name__)

def handshake(server):
    '''Performs the initial handshake with the master server to establish replication.'''
    
    logger.info(f"Connecting to master at {server.master_host}:{server.master_port}")
    master_socket = socket.create_connection((server.master_host, server.master_port))
    logger.info("Sending PING to master")
    master_socket.sendall(encode_resp(["PING"]))
    response, _ = decode_resp(master_socket.recv(4096))
    logger.info(f"Received from master: {response}")

    if response == "PONG":
        logger.info("Sending REPLCONF port to master")
        master_socket.sendall(encode_resp(["REPLCONF", "listening-port", str(server.PORT)]))
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
