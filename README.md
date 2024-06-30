# ProxyRotationServer

Welcome to **ProxyRotationServer** – a powerful, multi-threaded proxy server for rotating proxies, written in Python. This server is designed to handle HTTP requests, forward them through a proxy to a target server, and return the response to the client, all while offering robust features and easy setup. 

## ✨ Features

- **Multi-threaded** handling of client connections for high performance
- **Proxy rotation** from a list of proxies
- **Request and response parsing** for efficient processing
- **Logging** of connection details and errors for transparency
- **Blocking** of blacklisted hosts to maintain security
- **Static responses** for blocked requests and unsupported HTTP versions

## 📋 Requirements

- Python 3.6+
- `requests` library

## 📦 Installation

1. **Clone the repository**:

    ```sh
    git clone https://github.com/PersonaNormale/ProxyRotationServer.git
    cd ProxyRotationServer
    ```

2. **Install the required dependencies**:

    ```sh
    pip install -r requirements.txt
    ```

3. **Create a proxies list file** in the root directory and add your proxy addresses, one per line. (Format: `"ip:port"` or `"user:password@ip:port"`)

## 🚀 Usage

Usage:

```sh
usage: proxy_server.py [-h] --host HOST --port PORT --proxy-file PROXY_FILE
                       [--log LOG]
                       [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]

Proxy Server

options:
  -h, --help            show this help message and exit
  --host HOST           Host for the proxy server
  --port PORT           Port for the proxy server
  --proxy-file PROXY_FILE
                        File containing list of proxies
  --log LOG             Log file path
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Log level
```

## 🔧 Configuration
You can configure the server by modifying the following constants in proxy_server.py:

- BACKLOG: The number of unaccepted connections that the system will allow before refusing new connections (default: 50).
- MAX_THREADS: The maximum number of threads in the thread pool (default: 200).
- BLACKLISTED: List of blacklisted hosts that the server will block.
- MAX_CHUNK_SIZE: The maximum chunk size for data exchange (default: 16 * 1024).
- PROXY_LIST_FILE: The file containing the list of proxies (default: proxies.txt).

## Details
- Proxies are loaded from proxies.txt.
- Proxies are tested (Not Working || Black Listed) for reliability using a request to https://www.google.com.
- Only usable proxies are used for forwarding requests.
- Running the Server
- Start the server by running proxy_server.py.
- The server listens on localhost:8000 by default and handles incoming connections using a thread pool for multi-threading support.
