import json
import os
import time
import threading
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

_analyzer = None
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def start(analyzer, port: int = 9876):
    global _analyzer
    _analyzer = analyzer

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            from urllib.parse import urlparse, parse_qs
            parsed_url   = urlparse(self.path)
            query_params = parse_qs(parsed_url.query)
            view = query_params.get('view', ['dashboard'])[0]

            if parsed_url.path == "/training-status":
                data = json.dumps(_analyzer.get_training_status()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)

            elif parsed_url.path == "/metrics":
                data = json.dumps(_analyzer.get_metrics()).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)

            elif parsed_url.path in ("/", "/index.html"):
                html_path = os.path.join(_static_dir, "panel.html" if view == "panel" else "index.html")
                if not os.path.exists(html_path):
                    html_path = os.path.join(_static_dir, "index.html")
                with open(html_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(data)

            elif parsed_url.path == "/reset":
                _analyzer.reset()
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

            elif parsed_url.path == "/start-monitoring":
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

            elif parsed_url.path == "/show-dashboard":
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

            elif parsed_url.path == "/demo-mode":
                enable = query_params.get('enable', ['1'])[0] == '1'
                if hasattr(_analyzer, "enable_demo_mode"):
                    _analyzer.enable_demo_mode(enable)
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

            elif parsed_url.path == "/inject-event":
                char = query_params.get('char', ['a'])[0]
                if hasattr(_analyzer, "ingest"):
                    event = {
                        "ts": time.time(),
                        "is_down": True,
                        "keycode": ord(char) if len(char) == 1 else 0,
                        "is_backspace": char == 'backspace',
                        "char": None if char == 'backspace' else char,
                        "app_name": "Test",
                        "modifiers": 0,
                    }
                    _analyzer.ingest(event)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "char": char}).encode())

            elif parsed_url.path == "/simulate-typing":
                text      = query_params.get('text', ['hello'])[0]
                intensity = int(query_params.get('intensity', ['1'])[0])
                if hasattr(_analyzer, "ingest"):
                    ts = time.time()
                    import random
                    for i, char in enumerate(text):
                        if intensity == 1:
                            interval = 0.05 + random.uniform(-0.01, 0.01)
                        else:
                            interval = 0.02 + random.uniform(-0.01, 0.02)
                            if random.random() < 0.15:
                                event = {
                                    "ts": ts, "is_down": True, "keycode": 8,
                                    "is_backspace": True, "char": None,
                                    "app_name": "Test", "modifiers": 0,
                                }
                                _analyzer.ingest(event)
                                ts += 0.02
                        event = {
                            "ts": ts, "is_down": True, "keycode": ord(char),
                            "is_backspace": False, "char": char,
                            "app_name": "Test", "modifiers": 0,
                        }
                        _analyzer.ingest(event)
                        ts += interval
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"status":"ok"}')

            elif parsed_url.path == "/quit":
                self.send_response(200)
                self.end_headers()
                threading.Timer(0.1, lambda: sys.exit(0)).start()

            elif parsed_url.path == "/open-accessibility":
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", port), Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server
