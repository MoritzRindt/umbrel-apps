import importlib.util
from http.client import HTTPConnection
import json
from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest
from urllib.parse import urlencode

spec = importlib.util.spec_from_file_location('server', Path(__file__).parent / 'app/server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


class ConfigurationTests(unittest.TestCase):
    def test_config_is_private_and_cannot_inject_options(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server.save_key('testKEY123456', root)
            config = root / 'fr24feed.ini'
            self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o600)
            self.assertIn('host="receiver:30005"', config.read_text())
            before = config.read_bytes()
            for invalid in ('', 'abc', 'abc12345\nraw="yes"', 'abc12345"', '../../other'):
                with self.assertRaises(ValueError):
                    server.save_key(invalid, root)
                self.assertEqual(config.read_bytes(), before)

    def test_status_never_exposes_key_and_rejects_stale_receiver(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server.save_key('testKEY123456', root)
            receiver = root / 'aircraft.json'
            receiver.write_text(json.dumps({'now': time.time(), 'aircraft': [{}, {}], 'messages': 123}))
            status = server.snapshot(root, receiver)
            self.assertTrue(status['receiver'])
            self.assertEqual(status['aircraft'], 2)
            self.assertNotIn('testKEY123456', json.dumps(status))
            receiver.write_text(json.dumps({'now': 1, 'aircraft': [{}]}))
            self.assertFalse(server.snapshot(root, receiver)['receiver'])

    def test_missing_or_invalid_monitor_does_not_report_connected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receiver = root / 'absent'
            self.assertEqual(server.snapshot(root, receiver)['feed'], 'waiting')
            (root / 'monitor.json').write_text('fr24feed_mon_fr24_feed_status="connected"')
            self.assertEqual(server.snapshot(root, receiver)['feed'], 'connected')

    def test_http_rejects_cross_site_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            original = server.save_key
            server.save_key = lambda key: original(key, Path(directory))
            httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
            thread = threading.Thread(target=httpd.serve_forever, daemon=True)
            thread.start()
            try:
                connection = HTTPConnection('127.0.0.1', httpd.server_port, timeout=3)
                connection.request('POST', '/configure', urlencode({'key': 'testKEY123456', 'csrf': 'wrong'}))
                response = connection.getresponse()
                self.assertEqual(response.status, 403)
                response.read()
                self.assertFalse((Path(directory) / 'fr24feed.ini').exists())
                connection.request('POST', '/configure', urlencode({'key': 'testKEY123456', 'csrf': server.CSRF}))
                response = connection.getresponse()
                self.assertEqual(response.status, 303)
                response.read()
                self.assertTrue((Path(directory) / 'fr24feed.ini').exists())
                connection.close()
            finally:
                httpd.shutdown()
                httpd.server_close()
                thread.join()
                server.save_key = original


if __name__ == '__main__':
    unittest.main()
