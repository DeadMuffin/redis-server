DELIMITER = b"\r\n"

def encode_resp(data):
    '''Encodes data into the Redis Serialization Protocol (RESP) format.'''

    if isinstance(data, str):
        return f"+{data}\r\n".encode()
    elif isinstance(data, bytes):
        return f"${len(data)}\r\n".encode() + data + b"\r\n"
    elif isinstance(data, int):
        return f":{data}\r\n".encode()
    elif isinstance(data, list):
        encoded_elements = b''.join([encode_resp(element) for element in data])
        return f"*{len(data)}\r\n".encode() + encoded_elements
    elif data is None:
        return b"$-1\r\n"
    else:
        raise TypeError(f"Unknown type: {type(data)}")

def decode_resp(data):
    '''Decodes data from the Redis Serialization Protocol (RESP) format.'''

    if data == b'':
        return None, data

    prefix = data[0:1]

    if prefix == b'+':  # Simple string
        end_index = data.find(DELIMITER)
        return data[1:end_index].decode(), data[end_index + 2:]
    
    elif prefix == b'-':  # Error message
        end_index = data.find(DELIMITER)
        return data[1:end_index].decode(), data[end_index + 2:]

    elif prefix == b':':  # Integer
        end_index = data.find(DELIMITER)
        return int(data[1:end_index]), data[end_index + 2:]

    elif prefix == b'$':  # Bulk string
        length_end_index = data.find(DELIMITER)
        length = int(data[1:length_end_index])
        if length == -1:
            return None, data[length_end_index + 2:]
        start = length_end_index + 2
        end = start + length
        return data[start:end], data[end + 2:]

    elif prefix == b'*':  # Array
        length_end_index = data.find(DELIMITER)
        length = int(data[1:length_end_index])
        elements = []
        rest = data[length_end_index + 2:]
        for _ in range(length):
            element, rest = decode_resp(rest)
            elements.append(element)
        return elements, rest

    elif data.startswith(b'REDIS'): # ignore RBB Files
        return b'IGNORE', None

    else:
        raise ValueError(f"Unknown RESP type: {data[:1]}")

def identify_running_threads():
    '''Identifies and prints the names of all running threads.'''
    import threading
    running_threads = []
    for thread in threading.enumerate():
        if thread.is_alive():
            running_threads.append(thread)
            print(f"Thread {thread.name} is still running.")
    return running_threads

# Test cases for encode_resp and decode_resp
if __name__ == "__main__":
    test_data = [
        "OK",
        123,
        None,
        ["SET", "key", "value"],
        b"hello",
        ":1000",
        "+PONG\r\n",
        "-Error message\r\n"
    ]
    
    for data in test_data:
        encoded = encode_resp(data)
        print(f"Encoded: {encoded}")
        decoded, _ = decode_resp(encoded)
        print(f"Decoded: {decoded}\n")



