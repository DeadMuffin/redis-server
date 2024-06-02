import socket
import argparse
import sys
from utils.utils import decode_resp, encode_resp

def send_command(command, port):
    # Connect to the server
    server_address = ('localhost',port)  # Change this if your server is running on a different port or host
    sock = socket.create_connection(server_address)

    try:
        # Send command to the server
        sock.sendall(encode_resp(command))

        # Receive response from the server
        response = receive_response(sock)
        print(f"Response: {response}")

    finally:
        sock.close()

def receive_response(sock):
    data = sock.recv(1024)
    return decode_resp(data)

def main():
    parser = argparse.ArgumentParser(description="Send commands to Redis server")
    parser.add_argument('--port', type=int, default=6379, help='Port number to use')
    parser.add_argument('commands', nargs='+', help='Commands to send to the server')
    args = parser.parse_args()

    # Convert all arguments to a list, handling types appropriately
    commands = [arg if not arg.isdigit() else int(arg) for arg in args.commands]
    send_command(commands, args.port)
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
