# Constants
BACKLOG = 50
MAX_THREADS = 200
MAX_CHUNK_SIZE = 16 * 1024
DEFAULT_HTTP_PORT = 80
DEFAULT_HTTPS_PORT = 443
BLACKLISTED = []


# Enums and static responses


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


class StaticResponse:
    BLOCK_RESPONSE = b"HTTP/1.1 403 Forbidden\r\n\r\n"
    CONNECTION_ESTABLISHED = b"HTTP/1.1 200 Connection Established\r\n\r\n"
    SERVICE_UNAVAILABLE = b"HTTP/1.1 503 Service Unavailable\r\n\r\n"
    HTTP_VERSION_NOT_SUPPORTED = b"HTTP/1.1 505 HTTP Version Not Supported\r\n\r\n"
