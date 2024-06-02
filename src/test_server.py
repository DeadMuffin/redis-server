import unittest
import socket
import threading
import time

from server import RedisServer




def tag(*tags):
    '''Custom decorator for tagging test methods'''
    
    def decorator(test_method):
        setattr(test_method, '_tags', tags)
        return test_method
    return decorator


class TestRedisServer(unittest.TestCase):
    def setUp(self):
        '''Set up the test environment'''
        self.server = RedisServer(PORT=6380, role="master")
        self.server_thread = threading.Thread(target=self.server.start_server)
        self.server_thread.start()
        time.sleep(0.1) # Wait for server to start

    def tearDown(self):
        '''Tear down the test environment'''
        self.server.shutdown()
        self.server_thread.join()


    def send_command(self, command, host="localhost", port=6380):
        '''Send a command to the Redis server and return the response'''
        client_socket = socket.create_connection((host, port))
        client_socket.sendall(command)
        response = client_socket.recv(4096)
        client_socket.close()
        return response
    


    @tag('ping')
    def test_ping(self):
        '''Test the PING command'''
        response = self.send_command(b"*1\r\n$4\r\nPING\r\n")
        self.assertEqual(response, b"+PONG\r\n")

    @tag('echo')
    def test_echo(self):
        '''Test the ECHO command'''
        response = self.send_command(b"*2\r\n$4\r\nECHO\r\n$5\r\nhello\r\n")
        self.assertEqual(response, b"$5\r\nhello\r\n")

    @tag('setget')
    def test_set_get(self):
        '''Test the SET and GET commands'''
        response = self.send_command(b"*3\r\n$3\r\nSET\r\n$4\r\ntest\r\n$5\r\nvalue\r\n")
        self.assertEqual(response, b"+OK\r\n")

        response = self.send_command(b"*2\r\n$3\r\nGET\r\n$4\r\ntest\r\n")
        self.assertEqual(response, b"$5\r\nvalue\r\n")

    @tag('del')
    def test_del(self):
        '''Test the DEL command'''
        # Set a key-value pair to ensure there is something to delete
        self.send_command(b"*3\r\n$3\r\nSET\r\n$3\r\nfoo\r\n$3\r\nbar\r\n")
        
        # Delete the key
        response = self.send_command(b"*2\r\n$3\r\nDEL\r\n$3\r\nfoo\r\n")
        self.assertEqual(response, b":1\r\n")
        
        # Ensure the key is actually deleted
        response = self.send_command(b"*2\r\n$6\r\nEXISTS\r\n$3\r\nfoo\r\n")
        self.assertEqual(response, b":0\r\n")

    @tag('setttl')
    def test_set_with_ttl(self):
        '''Test the SET command with TTL'''
        response = self.send_command(b"*5\r\n$3\r\nSET\r\n$4\r\ntest\r\n$5\r\nvalue\r\n$2\r\nPX\r\n$3\r\n100\r\n")
        self.assertEqual(response, b"+OK\r\n")

        response = self.send_command(b"*2\r\n$3\r\nGET\r\n$4\r\ntest\r\n")
        self.assertEqual(response, b"$5\r\nvalue\r\n")

        time.sleep(0.1)  # Wait for TTL to expire

        response = self.send_command(b"*2\r\n$3\r\nGET\r\n$4\r\ntest\r\n")
        self.assertEqual(response, b"$-1\r\n")

    @tag('info')
    def test_info(self):
        '''Test the INFO command'''
        response = self.send_command(b"*1\r\n$4\r\nINFO\r\n")
        expected_info = f"role:master, connected_slaves:0, master_replid:{self.server.master_replid}, master_repl_offset:{self.server.master_repl_offset}"
        self.assertIn(expected_info.encode(), response)

    @tag('psync')
    def test_psync(self):
        '''Test the PSYNC command'''
        response = self.send_command(b"*2\r\n$5\r\nPSYNC\r\n$1\r\n?\r\n")
        self.assertIn(b"+FULLRESYNC", response)
        self.assertIn(self.server.master_replid.encode(), response)

        
    @tag('setmulti')
    def test_set_multiple_keys(self):
        '''Test setting and getting multiple keys'''
        keys_values = [("key1", "value1"), ("key2", "value2"), ("key3", "value3")]

        for key, value in keys_values:
            response = self.send_command(f"*3\r\n$3\r\nSET\r\n${len(key)}\r\n{key}\r\n${len(value)}\r\n{value}\r\n".encode())
            self.assertEqual(response, b"+OK\r\n")

        for key, value in keys_values:
            response = self.send_command(f"*2\r\n$3\r\nGET\r\n${len(key)}\r\n{key}\r\n".encode())
            self.assertEqual(response, f"${len(value)}\r\n{value}\r\n".encode())

    @tag('unknown')
    def test_unknown_command(self):
        '''Test an unknown command'''
        response = self.send_command(b"*1\r\n$7\r\nUNKNOWN\r\n")
        self.assertEqual(response, b"$-1\r\n")

    @tag('setgetempty')
    def test_set_get_empty_value(self):
        '''Test setting and getting an empty value'''
        response = self.send_command(b"*3\r\n$3\r\nSET\r\n$4\r\ntest\r\n$0\r\n\r\n")
        self.assertEqual(response, b"+OK\r\n")

        response = self.send_command(b"*2\r\n$3\r\nGET\r\n$4\r\ntest\r\n")
        self.assertEqual(response, b"$0\r\n\r\n")

    @tag('propagation')
    def test_propagation(self):
        '''Test key propagation to a slave server'''
        # Start a slave server
        slave_server = RedisServer(PORT=8000, role="slave", master_host="localhost", master_port=self.server.PORT)
        slave_thread = threading.Thread(target=slave_server.start_server)
        slave_thread.start()

        # Wait for servers to start
        time.sleep(0.1)

        # Set a key on the master
        self.send_command(b"*3\r\n$3\r\nSET\r\n$4\r\nkey1\r\n$5\r\nvalue\r\n")

        # Check if the key is replicated to the slave
        response = self.send_command(b"*2\r\n$3\r\nGET\r\n$4\r\nkey1\r\n", host="localhost", port=slave_server.PORT)
        self.assertEqual(response, b"$5\r\nvalue\r\n")

        slave_server.shutdown()
        slave_thread.join()

    @tag('shutdown')
    def test_shutdown(self):
        '''Test the SHUTDOWN command'''
        response = self.send_command(b"*1\r\n$8\r\nSHUTDOWN\r\n")
        self.assertEqual(response, b"+OK\r\n")

        # Ensure the server is actually shutdown
        with self.assertRaises(ConnectionRefusedError):
            self.send_command(b"*1\r\n$4\r\nPING\r\n")


if __name__ == "__main__":
    # Pass tags_filter as command-line arguments
    import sys
    tags_filter = set(sys.argv[1:]) if len(sys.argv) > 1 else set()

    # Collect tests based on tags
    test_suite = unittest.TestSuite()
    for test_name in dir(TestRedisServer):
        test_method = getattr(TestRedisServer, test_name)
        if callable(test_method) and hasattr(test_method, '_tags'):
            if not tags_filter or set(test_method._tags).intersection(tags_filter):
                test_suite.addTest(TestRedisServer(test_name))

    # Run the test suite
    try:
        unittest.TextTestRunner().run(test_suite)
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    
