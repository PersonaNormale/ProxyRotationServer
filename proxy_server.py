import sys
import socket
from concurrent.futures import ThreadPoolExecutor
import argparse

from constants import MAX_THREADS, BACKLOG
from logger_config import logger
from connection_handler import ConnectionHandler
from proxy_pool import ProxyPool

# Server


class Server:
    def __init__(self, host, port, proxy_pool):
        self.host = host
        self.port = port
        self.proxy_pool = proxy_pool
        self.server_socket = self.create_server_socket()
        self.executor = ThreadPoolExecutor(max_workers=MAX_THREADS)

    def create_server_socket(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((self.host, self.port))
        server_socket.listen(BACKLOG)
        return server_socket

    def start(self):
        logger.info(f"Starting server on {self.host}:{self.port}")
        try:
            while True:
                client_conn, _ = self.server_socket.accept()
                handler = ConnectionHandler(client_conn, self.proxy_pool)
                self.executor.submit(handler.run)
        except Exception as e:
            logger.error(f"Error in server: {e}")
        finally:
            self.stop()

    def stop(self):
        self.executor.shutdown(wait=True)
        self.server_socket.close()


def main():
    args = parse_arguments()
    global logger

    try:
        proxy_pool = ProxyPool(args.proxy_file)
        server = Server(host=args.host, port=args.port, proxy_pool=proxy_pool)
        server.start()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)


def parse_arguments():
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
    return parser.parse_args()


if __name__ == '__main__':
    main()
