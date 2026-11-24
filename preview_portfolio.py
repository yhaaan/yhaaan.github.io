"""Build and open a private, local preview of the exact site, without publishing.

The preview keeps itself current: when portfolio.json, build_portfolio.py or anything under
site/ changes on disk, the next page request rebuilds the site, so a browser refresh is enough.
"""
import importlib
import json
import threading
import webbrowser
import secrets
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

import build_portfolio
import local_owner
from build_portfolio import BASE
from local_owner import handler_for


class Rebuilder:
    """Rebuild into a fresh folder when watched sources change; serve the old build if it fails."""

    def __init__(self, temp, public, base=BASE):
        self.temp, self.public, self.base = temp, public, base
        self.lock = threading.Lock()
        self.stamp = self.fingerprint()

    def fingerprint(self):
        files = [self.base / 'portfolio.json', self.base / 'build_portfolio.py',
                 *(self.base / 'site').rglob('*')]
        return tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in sorted(files) if p.is_file())

    def refresh(self):
        with self.lock:
            stamp = self.fingerprint()
            if stamp == self.stamp:
                return False
            self.stamp = stamp  # Even a failed build is not retried until the files change again.
            try:
                # Reload the builder so code edits apply too, and let owner saves use the same code.
                module = importlib.reload(build_portfolio)
                local_owner.build = module.build
                data = json.loads((self.base / 'portfolio.json').read_text(encoding='utf-8-sig'))
                stage = Path(mkdtemp(dir=self.temp))
                module.build(data, stage, self.base / 'site', editor_api='/__editor')
            except Exception as error:  # Keep serving the last good build and say why.
                print(f'[미리보기] 다시 만들기 실패, 이전 화면 유지: {error}', flush=True)
                return False
            self.public[0] = stage
            print('[미리보기] 변경 반영됨 · 새로고침하면 보입니다.', flush=True)
            return True


def live_handler(temp, public, bootstrap, *, base=BASE):
    rebuilder = Rebuilder(temp, public, base)
    owner = handler_for(temp, public, bootstrap, base=base)

    class Handler(owner):
        def __init__(self, *args, **kwargs):
            rebuilder.refresh()  # Before the base class picks the folder to serve for this request.
            super().__init__(*args, **kwargs)

    Handler.rebuilder = rebuilder
    return Handler


def main():
    data = json.loads((BASE / 'portfolio.json').read_text(encoding='utf-8-sig'))
    with TemporaryDirectory(prefix='yohan-portfolio-') as temp:
        public = [Path(temp) / 'public']
        build_portfolio.build(data, public[0], editor_api='/__editor')
        bootstrap = secrets.token_urlsafe(32)
        handler = live_handler(temp, public, bootstrap)
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            url = f'http://127.0.0.1:{server.server_port}/'
            owner = url+'#owner='+bootstrap
            print(f'방문자 미리보기: {url}\n소유자 주소 (공유 금지): {owner}\n'
                  '파일이 바뀌면 브라우저 새로고침만 하면 됩니다.\n종료: Ctrl+C', flush=True)
            webbrowser.open_new_tab(owner)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
