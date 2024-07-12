import socket
import threading
import selectors
import re
from base64 import b64encode
from logger_config import logger
from constants import MAX_CHUNK_SIZE, BLACKLISTED
from constants import Protocol, StaticResponse, Method
from request import Request

# Connection Handler


class ProxyConnectionError(Exception):
    """Raised when there's an error connecting to a proxy."""

    pass


class ConnectionHandler(threading.Thread):
    def __init__(self, client_conn, proxy_pool):
        super().__init__()
        self.client_conn = client_conn
        self.server_conn = None
        self.proxy_pool = proxy_pool

    def run(self):
        try:
            raw_request = self.client_conn.recv(MAX_CHUNK_SIZE)
            if not raw_request:
                return

            request = Request(raw_request)
            self.handle_request(request, raw_request)
        except Exception as e:
            logger.error(f"Error in handling connection: {e}")
        finally:
            self.cleanup()

    def handle_request(self, request, raw_request):
        if request.protocol in (Protocol.HTTP20, Protocol.HTTP30):

            self.client_conn.send(StaticResponse.HTTP_VERSION_NOT_SUPPORTED)
            return

        if request.host in BLACKLISTED:
            self.client_conn.send(StaticResponse.BLOCK_RESPONSE)
            logger.info(
                f"{request.method:<8} {request.path} {request.protocol} BLOCKED"
            )
            return

        proxy = self.proxy_pool.get_proxy()
        self.server_conn = self.connect_via_proxy(proxy, request.host, request.port)
        logger.info(f"Using proxy {proxy} for {request.host}:{request.port}")

        if request.method != Method.CONNECT:
            self.server_conn.sendall(raw_request)

        if request.method == Method.CONNECT:
            self.client_conn.sendall(StaticResponse.CONNECTION_ESTABLISHED)

        self.handle_data_exchange()

    def connect_via_proxy(self, proxy, host, port):
        match = re.match(r"^(?:([^:]+):([^@]+)@)?([^:]+):(\d+)$", proxy)
        if not match:
            raise ValueError("Invalid proxy format")

        username, password, proxy_host, proxy_port = match.groups()
        proxy_port = int(proxy_port)

        try:
            s = socket.create_connection((proxy_host, proxy_port))
            connect_str = self.build_connect_string(host, port, username, password)
            s.sendall(connect_str.encode())

            response = s.recv(MAX_CHUNK_SIZE)
            if b"200 OK" not in response:
                raise ProxyConnectionError(
                    "Failed to establish connection through proxy"
                )

            return s
        except Exception as e:
            logger.error(f"Proxy connection error: {e}")
            raise

    @staticmethod
    def build_connect_string(host, port, username, password):
        connect_str = f"CONNECT {host}:{port} HTTP/1.1\r\nHost: {host}\r\n"
        if username and password:
            auth_str = f"{username}:{password}"
            auth_b64 = b64encode(auth_str.encode()).decode()
            connect_str += f"Proxy-Authorization: Basic {auth_b64}\r\n"
        return connect_str + "\r\n"

    def handle_data_exchange(self):
        selector = selectors.DefaultSelector()
        selector.register(self.client_conn, selectors.EVENT_READ)
        selector.register(self.server_conn, selectors.EVENT_READ)

        while True:
            events = selector.select(timeout=None)

            for key, _ in events:
                sock = key.fileobj
                try:
                    data = sock.recv(MAX_CHUNK_SIZE)
                    if not data:
                        return
                    (
                        self.server_conn
                        if sock is self.client_conn
                        else self.client_conn
                    ).sendall(data)
                except Exception as e:
                    logger.error(f"Error during data exchange: {e}")
                    return

    def cleanup(self):
        for conn in (self.client_conn, self.server_conn):
            if conn:
                try:
                    conn.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
