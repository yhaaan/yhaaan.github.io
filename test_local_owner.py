import json
import shutil
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from build_portfolio import SITE, build
from local_owner import handler_for


class LocalEditTests(unittest.TestCase):
    def test_private_save_round_trip(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            shutil.copytree(SITE, base / 'site')
            data = {'profile': {'name': 'Before'}}
            source = base / 'portfolio.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            public = [base / 'public']
            build(data, public[0], base / 'site', editor_api='/__editor')
            self.assertTrue((public[0] / 'owner.mjs').is_file())
            handler = handler_for(tmp, public, 'local-test', base=base)
            with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                def post(path, key='', obj=None, origin=None):
                    c = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                    try:
                        c.request('POST', '/__editor/'+path, json.dumps(obj or {}), {
                            'Origin': origin or f'http://127.0.0.1:{server.server_port}',
                            'Content-Type': 'application/json', 'Authorization': 'Bearer '+key})
                        r = c.getresponse()
                        return r.status, json.loads(r.read())
                    finally:
                        c.close()
                try:
                    self.assertEqual(post('save')[0], 401)
                    self.assertEqual(post('local-login','local-test',origin='https://example.org')[0], 403)
                    key = post('local-login','local-test')[1]['session']
                    state = post('read',key)[1]
                    state['data']['profile']['name'] = 'After'
                    self.assertEqual(post('save',key,state)[0], 200)
                    self.assertEqual(json.loads(source.read_bytes())['profile']['name'], 'After')
                    self.assertIn('After', (public[0]/'index.html').read_text(encoding='utf-8'))
                    self.assertEqual(post('save',key,state)[0], 409)
                    self.assertEqual(post('logout',key)[0], 200)
                    self.assertEqual(post('read',key)[0], 401)
                finally:
                    server.shutdown()
                    thread.join()



class RangeTests(unittest.TestCase):
    def test_video_byte_ranges_allow_seeking(self):
        with TemporaryDirectory() as tmp:
            public = Path(tmp) / 'public'
            (public / 'media').mkdir(parents=True)
            (public / 'media' / 'clip.mp4').write_bytes(bytes(range(100)))
            handler = handler_for(tmp, [public], 'k', base=Path(tmp))
            with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    def get(rng=None):
                        c = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
                        c.request('GET', '/media/clip.mp4', headers={'Range': rng} if rng else {})
                        r = c.getresponse()
                        return r.status, r.getheader('Content-Range'), r.read(), r.getheader('Accept-Ranges')
                    status, rng, body, accept = get()
                    self.assertEqual((status, len(body), accept), (200, 100, 'bytes'))
                    self.assertEqual(get('bytes=10-19')[:3], (206, 'bytes 10-19/100', bytes(range(10, 20))))
                    self.assertEqual(get('bytes=95-')[:3], (206, 'bytes 95-99/100', bytes(range(95, 100))))
                    self.assertEqual(get('bytes=-3')[:3], (206, 'bytes 97-99/100', bytes(range(97, 100))))
                    self.assertEqual(get('bytes=200-300')[:2], (416, 'bytes */100'))
                finally:
                    server.shutdown()
                    thread.join()

class LivePreviewTests(unittest.TestCase):
    def test_refresh_rebuilds_after_source_change_and_keeps_last_good_build(self):
        import os
        from preview_portfolio import live_handler
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            shutil.copytree(SITE, base / 'site')
            source = base / 'portfolio.json'
            source.write_text(json.dumps({'profile': {'name': 'Before'}}), encoding='utf-8')
            public = [base / 'public']
            build(json.loads(source.read_text(encoding='utf-8')), public[0], base / 'site', editor_api='/__editor')
            rebuilder = live_handler(tmp, public, 'k', base=base).rebuilder
            self.assertFalse(rebuilder.refresh())
            first = public[0]
            source.write_text(json.dumps({'profile': {'name': 'After'}}), encoding='utf-8')
            os.utime(source, ns=(1, 2))  # A distinct stamp even on coarse file clocks.
            self.assertTrue(rebuilder.refresh())
            self.assertNotEqual(public[0], first)
            self.assertIn('After', (public[0] / 'index.html').read_text(encoding='utf-8'))
            good = public[0]
            source.write_text('{broken', encoding='utf-8')
            self.assertFalse(rebuilder.refresh())
            self.assertEqual(public[0], good)
