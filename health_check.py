import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests
import time
import logging

logger = logging.getLogger()

# Health check HTTP server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/favicon.ico":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Favicon OK")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def start_health_check_server():
    server = HTTPServer(("0.0.0.0", 80), HealthCheckHandler)
    logger.info("Health check server started on port 80")
    threading.Thread(target=server.serve_forever, daemon=True).start()

def self_ping():
    while True:
        try:
            requests.get("http://0.0.0.0")
            logger.info("Self-ping successful.")
        except Exception as e:
            logger.error(f"Self-ping failed: {e}")
        time.sleep(240)  # Ping every 4 minutes