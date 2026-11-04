import hmac
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

STATE = Path('/state')
RECEIVER = Path('/run/readsb/aircraft.json')
CSRF = secrets.token_urlsafe(32)


def save_key(key, state=STATE):
    if not re.fullmatch(r'[A-Za-z0-9]{8,128}', key):
        raise ValueError('Invalid sharing key')
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    content = '\n'.join([
        'receiver="beast-tcp"', 'host="receiver:30005"',
        f'fr24key="{key}"', 'bs="no"', 'raw="no"',
        'mlat="no"', 'mlat-without-gps="no"', 'logmode="0"', ''
    ])
    descriptor, temporary = tempfile.mkstemp(dir=state, prefix='.config-')
    try:
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, state / 'fr24feed.ini')
    finally:
        Path(temporary).unlink(missing_ok=True)


def snapshot(state=STATE, receiver=RECEIVER):
    result = {'configured': (state / 'fr24feed.ini').is_file(),
              'receiver': False, 'aircraft': 0, 'messages': 0,
              'feed': 'waiting', 'monitorFresh': False}
    try:
        data = json.loads(receiver.read_text())
        result['receiver'] = 0 <= time.time() - float(data['now']) < 20
        if result['receiver']:
            result['aircraft'] = len(data.get('aircraft', []))
            result['messages'] = int(data.get('messages', 0))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        monitor = state / 'monitor.json'
        result['monitorFresh'] = 0 <= time.time() - monitor.stat().st_mtime < 60
        if result['monitorFresh']:
            raw = monitor.read_text()
            match = re.search(r'fr24feed_mon_fr24_feed_status[\s"=:]+([A-Za-z]+)', raw)
            if match:
                status = match[1].lower()
                result['feed'] = status if status in ('connected', 'disconnected') else 'waiting'
    except OSError:
        pass
    return result


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def send(self, status, body, content_type):
        encoded = body.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(encoded)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-" + CSRF + "'; connect-src 'self'; form-action 'self'; frame-ancestors 'self'")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path == '/health':
            self.send(200, 'ok', 'text/plain')
        elif self.path == '/api/status':
            self.send(200, json.dumps(snapshot()), 'application/json')
        elif self.path == '/':
            page = Path(__file__).with_name('index.html').read_text().replace('__CSRF__', CSRF)
            self.send(200, page, 'text/html; charset=utf-8')
        else:
            self.send(404, 'Not found', 'text/plain')

    def do_POST(self):
        if self.path != '/configure':
            self.send(404, 'Not found', 'text/plain')
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('Invalid size')
            form = parse_qs(self.rfile.read(size).decode())
            if not hmac.compare_digest(form.get('csrf', [''])[0], CSRF):
                self.send(403, 'Reload the page and try again.', 'text/plain')
                return
            save_key(form.get('key', [''])[0])
        except (ValueError, UnicodeError):
            self.send(400, 'Invalid sharing key.', 'text/plain')
            return
        except OSError:
            self.send(503, 'Configuration could not be saved.', 'text/plain')
            return
        self.send_response(303)
        self.send_header('Location', '/')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()


if __name__ == '__main__':
    ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
