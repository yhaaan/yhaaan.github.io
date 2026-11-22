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
