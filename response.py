class ResponseParsingError(Exception):
    """Raised when there's an error parsing a response."""

    pass


class Response:
    def __init__(self, raw):
        self.raw = raw
        self.headers = {}
        self.status_line = ""
        self.protocol = ""
        self.status = ""
        self.status_str = ""
        self.parse_response(raw)

    def parse_response(self, raw):
        try:
            lines = raw.split(b"\r\n")
            self.parse_status_line(lines[0].decode())
            self.parse_headers(lines[1:])
        except Exception as e:
            raise ResponseParsingError(f"Failed to parse response: {e}")

    def parse_status_line(self, status_line):
        parts = status_line.split()
        if len(parts) < 3:
            raise ValueError("Invalid status line format")
        self.protocol = parts[0]
        self.status = parts[1]
        self.status_str = " ".join(parts[2:])

    def parse_headers(self, header_lines):
        for line in header_lines:
            if line.strip():
                key, value = line.decode().split(":", 1)
                self.headers[key.strip().lower()] = value.strip()
