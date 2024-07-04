import re
from constants import DEFAULT_HTTP_PORT, DEFAULT_HTTPS_PORT, Protocol
# Request and Response classes


class RequestParsingError():
    """Raised when there's an error parsing a request."""


class Request:
    def __init__(self, raw):
        self.raw = raw
        self.headers = {}
        self.method = ""
        self.path = ""
        self.protocol = ""
        self.host = ""
        self.port = DEFAULT_HTTP_PORT
        self.parse_request(raw)

    def parse_request(self, raw):
        try:
            lines = raw.split(b"\r\n")
            self.parse_request_line(lines[0].decode())
            self.parse_headers(lines[1:])
            self.parse_host_port()
        except ValueError as e:
            raise RequestParsingError(f"Failed to parse request: {e}")

    def parse_request_line(self, request_line):
        parts = request_line.split()
        if len(parts) != 3:
            raise ValueError("Invalid request line format")
        self.method, self.path, self.protocol = parts

    def parse_headers(self, header_lines):
        for line in header_lines:
            if line.strip():
                key, value = line.decode().split(":", 1)
                self.headers[key.strip().lower()] = value.strip()

    def parse_host_port(self):
        host_header = self.headers.get('host', '')
        match = re.match(r"^(.*?)(?::(\d+))?$", host_header)
        if match:
            self.host = match.group(1)
            self.port = int(match.group(2)) if match.group(
                2) else DEFAULT_HTTP_PORT
        else:
            raise ValueError(f"Invalid host header: {host_header}")

        if self.protocol in (Protocol.HTTP20, Protocol.HTTP30):
            self.port = DEFAULT_HTTPS_PORT

        if ":" in self.path:
            self.path = "/" + "/".join(self.path.split(":")[1:])
