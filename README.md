
# RedisServer

## Introduction

**Project Name**: RedisServer

**Description**: RedisServer is a lightweight, in-memory key-value data store inspired by the Redis database. This project provides basic Redis functionalities such as setting and getting values, handling key expiration, and simple replication between master and slave servers.

**Features**:
- Basic Redis commands: `PING`, `ECHO`, `SET`, `GET`, `DEL`, `INFO`, `EXISTS`, `SHUTDOWN`
- Key expiration with TTL
- Simple master-slave replication
- Customizable logging with colored output
- Simple Client CLI
- Unit tests for core functionalities

## Installation

### Prerequisites
- Python 3.6 or higher
- `unittest` library (comes with standard Python library)
- `socket` library (comes with standard Python library)
- `argparse` library (comes with standard Python library)
- `logging` library (comes with standard Python library)
- `threading` library (comes with standard Python library)

### Installation Steps
Clone the repository:
```bash
git clone https://github.com/DeadMuffin/redis-server.git
cd RedisServer
```

## Usage

### Basic Usage

1. **Start the Redis server:**
    ```bash
    python src/server.py --port 8000 --replicaof "localhost 6379"
    ```
    Arguments:
    - `--port`: (Optional, Default: 6379) Port number to use
    - `--replicaof`: (Optional) Master host and port number to use for slave

    **Note:** The server will be in Slave mode when `--replicaof` is passed.

2. **Use the provided client to send commands:**
    ```bash
    python src/client.py --port 6379 PING
    ```

### Examples for Using `client.py`

1. **Sending a PING command:**
    ```bash
    python src/client.py --port 6379 PING
    ```

2. **Setting a key-value pair:**
    ```bash
    python src/client.py --port 6379 SET mykey "Hello, World!"
    ```

3. **Getting the value of a key:**
    ```bash
    python src/client.py --port 6379 GET mykey
    ```

4. **Deleting a key:**
    ```bash
    python src/client.py --port 6379 DEL mykey
    ```

5. **Checking if a key exists:**
    ```bash
    python src/client.py --port 6379 EXISTS mykey
    ```

These examples illustrate how to interact with the Redis server using the `client.py` script by specifying the appropriate commands and arguments.

## License

**License Type**: not decided yet
