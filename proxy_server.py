import sys
import socket
import threading
import select
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import requests
import random
from base64 import b64encode
import argparse

# Function to set up logging


def setup_logging(log_file=None, log_level=logging.INFO):
    logger = logging.getLogger("ProxyServer")
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Constants
BACKLOG = 50
MAX_THREADS = 200
BLACKLISTED = []
MAX_CHUNK_SIZE = 16 * 1024
proxies = []
usable_proxies = []


class StaticResponse:
    BLOCK_RESPONSE = b"HTTP/1.1 403 Forbidden\r\n\r\n"
    CONNECTION_ESTABLISHED = b"HTTP/1.1 200 Connection Established\r\n\r\n"


class Error:
    STATUS_503 = "Service Unavailable"
    STATUS_505 = "HTTP Version Not Supported"


class ProxyConnectionError(Exception):
    """Custom exception for proxy connection errors."""
    pass


class RequestParsingError(Exception):
    """Custom exception for errors in request parsing."""
    pass


class ResponseParsingError(Exception):
    """Custom exception for errors in response parsing."""
    pass


for key in filter(lambda x: x.startswith("STATUS"), dir(Error)):
    _, code = key.split("_")
    value = getattr(Error, f"STATUS_{code}")
    setattr(Error, f"STATUS_{code}",
            f"HTTP/1.1 {code} {value}\r\n\r\n".encode())


class Method:
    GET = "GET"
    PUT = "PUT"
    HEAD = "HEAD"
    POST = "POST"
    PATCH = "PATCH"
    DELETE = "DELETE"
    OPTIONS = "OPTIONS"
    CONNECT = "CONNECT"


class Protocol:
    HTTP10 = "HTTP/1.0"
    HTTP11 = "HTTP/1.1"
    HTTP20 = "HTTP/2.0"
    HTTP30 = "HTTP/3.0"


class Request:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.headers = {}
        self.method = ""
        self.path = ""
        self.protocol = ""
        self.host = ""
        self.port = 80  # Default port

        try:
            self.parse_request(raw)
        except ValueError as e:
            logger.error(f"Failed to parse request: {e}")
            raise RequestParsingError(f"Failed to parse request: {e}")

    def parse_request(self, raw: bytes):
        lines = raw.split(b"\r\n")
        self.parse_request_line(lines[0].decode())

        for line in lines[1:]:
            if line.strip():
                key, value = line.decode().split(":", 1)
                self.headers[key.strip().lower()] = value.strip()

        if 'host' in self.headers:
            self.parse_host_port(self.headers['host'])

    def parse_request_line(self, request_line: str):
        parts = request_line.split()
        if len(parts) != 3:
            raise ValueError("Invalid request line format")
        self.method, self.path, self.protocol = parts

    def parse_host_port(self, host_header: str):
        match = re.match(r"^(.*?)(?::(\d+))?$", host_header)
        if match:
            self.host = match.group(1)
            self.port = int(match.group(2)) if match.group(
                2) else 80  # Default port 80 if not specified
        else:
            raise ValueError(f"Invalid host header: {host_header}")

        if self.protocol == Protocol.HTTP20 or self.protocol == Protocol.HTTP30:
            self.port = 443

        if ":" in self.path:
            self.path = "/" + "/".join(self.path.split(":")[1:])

    def header(self):
        return self.headers


class Response:
    def __init__(self, raw: bytes):
        self.raw = raw
        self.headers = {}
        self.status_line = ""
        self.protocol = ""
        self.status = ""
        self.status_str = ""

        self.parse_response(raw)

    def parse_response(self, raw: bytes):
        try:
            lines = raw.split(b"\r\n")
            self.parse_status_line(lines[0].decode())

            for line in lines[1:]:
                if line.strip():
                    key, value = line.decode().split(":", 1)
                    self.headers[key.strip().lower()] = value.strip()
        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            raise ResponseParsingError(f"Failed to parse response: {e}")

    def parse_status_line(self, status_line: str):
        parts = status_line.split()
        if len(parts) >= 3:
            self.protocol = parts[0]
            self.status = parts[1]
            self.status_str = " ".join(parts[2:])
        else:
            raise ValueError("Invalid status line format")

    def header(self):
        return self.headers


def load_proxies(filepath: str) -> list:
    proxies = []
    try:
        with open(filepath, 'r') as file:
            for line in file:
                proxy = line.strip()
                if proxy:
                    proxies.append(proxy)
    except Exception as e:
        logger.error(f"Failed to read proxy list from {filepath}: {e}")
    return proxies


def test_proxy(proxy: str) -> bool:
    logger.info(f"Starting testing {proxy} reliability.")
    try:
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        }
        response = requests.get("https://www.google.com",
                                proxies=proxies, timeout=5)
        if response.status_code != 200:
            logger.debug(
                f"Proxy {proxy} is not reliable ({response.status_code}).")
            return False
        logger.debug(f"Finished testing {proxy} reliability.")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Proxy {proxy} failed: {e}")
        return False


def select_random_proxy() -> str:
    if not usable_proxies:
        raise Exception("No usable proxies available")
    return random.choice(usable_proxies)


class ConnectionHandler(threading.Thread):
    def __init__(self, client_conn: socket.socket):
        threading.Thread.__init__(self)
        self.client_conn = client_conn
        self.server_conn = None

    def run(self):
        try:
            raw_request = self.client_conn.recv(MAX_CHUNK_SIZE)
            if not raw_request:
                return

            request = Request(raw_request)

            if request.protocol == Protocol.HTTP20:
                self.client_conn.send(Error.STATUS_505)
                return

            if request.protocol == Protocol.HTTP30:
                self.client_conn.send(Error.STATUS_505)
                return

            if request.host in BLACKLISTED:
                self.client_conn.send(StaticResponse.BLOCK_RESPONSE)
                logger.info(
                    f"{request.method:<8} {request.path} {request.protocol} BLOCKED")
                return

            proxy = select_random_proxy()
            self.server_conn = self.connect_via_proxy(
                proxy, request.host, request.port)
            logger.info(
                f"Using proxy {proxy} for {request.host}:{request.port}")

            if request.method != Method.CONNECT:
                self.server_conn.sendall(raw_request)

            if request.method == Method.CONNECT:
                self.client_conn.sendall(StaticResponse.CONNECTION_ESTABLISHED)

            self.handle_data_exchange()

        except Exception as e:
            logger.error(f"Error in handling connection: {e}")
        finally:
            self.cleanup()

    def connect_via_proxy(self, proxy: str, host: str, port: int) -> socket.socket:
        match = re.match(r'^(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$', proxy)
        if not match:
            raise ValueError("Invalid proxy format")

        username, password, proxy_host, proxy_port = match.groups()
        proxy_port = int(proxy_port)

        try:
            s = socket.socket()
            s.connect((proxy_host, proxy_port))

            connect_str = f"CONNECT {host}:{port} HTTP/1.1\r\n"
            connect_str += f"Host: {host}\r\n"

            if username and password:
                auth_str = f"{username}:{password}"
                auth_b64 = b64encode(auth_str.encode()).decode()
                connect_str += f"Proxy-Authorization: Basic {auth_b64}\r\n"

            connect_str += "\r\n"
            logger.debug(
                f"Sending CONNECT request to proxy {proxy_host}:{proxy_port} for {host}:{port}")
            s.sendall(connect_str.encode())

            response = s.recv(MAX_CHUNK_SIZE)
            logger.debug(f"Received response: {response}")

            if b"200 OK" not in response:
                raise ProxyConnectionError(
                    "Failed to establish connection through proxy")

            return s

        except Exception as e:
            logger.error(f"Proxy connection error: {e}")
            raise

    def handle_data_exchange(self):
        logger.debug("Data exchange started between client and server.")
        sockets = [self.client_conn, self.server_conn]
        while True:
            readable, _, exceptional = select.select(sockets, [], sockets, 1)
            if exceptional:
                break
            for sock in readable:
                try:
                    data = sock.recv(MAX_CHUNK_SIZE)
                    if not data:
                        return
                    if sock is self.client_conn:
                        self.server_conn.sendall(data)
                    else:
                        self.client_conn.sendall(data)
                except Exception as e:
                    logger.error(f"Error during data exchange: {e}")
                    return

    def cleanup(self):
        try:
            if self.client_conn:
                self.client_conn.close()
        except Exception as e:
            logger.error(f"Error closing client connection: {e}")
        try:
            if self.server_conn:
                self.server_conn.close()
        except Exception as e:
            logger.error(f"Error closing server connection: {e}")


class Server:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((host, port))
        self.server_socket.listen(BACKLOG)
        self.executor = ThreadPoolExecutor(max_workers=MAX_THREADS)

    def start(self):
        logger.info(f"Starting server on {self.host}:{self.port}")
        try:
            while True:
                client_conn, _ = self.server_socket.accept()
                handler = ConnectionHandler(client_conn)
                self.executor.submit(handler.run)
        except Exception as e:
            logger.error(f"Error in server: {e}")
        finally:
            self.stop()

    def stop(self):
        self.executor.shutdown(wait=True)
        self.server_socket.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Proxy Server")
    parser.add_argument("--host", type=str, required=True,
                        help="Host for the proxy server")
    parser.add_argument("--port", type=int, required=True,
                        help="Port for the proxy server")
    parser.add_argument("--proxy-file", type=str, required=True,
                        help="File containing list of proxies")
    parser.add_argument("--log", type=str, help="Log file path")
    parser.add_argument("--log-level", type=str, choices=[
                        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], default="INFO", help="Log level")

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = setup_logging(args.log, log_level)

    proxies = load_proxies(args.proxy_file)
    usable_proxies = [proxy for proxy in proxies if test_proxy(proxy)]

    if not usable_proxies:
        logger.error("No usable proxies found. Exiting.")
        sys.exit(1)

    server = Server(host=args.host, port=args.port)
    server.start()
