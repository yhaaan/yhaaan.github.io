"""Build and open a private, local preview of the exact site, without publishing."""
import json
import webbrowser
import secrets
from http.server import ThreadingHTTPServer
from local_owner import handler_for
from pathlib import Path
from tempfile import TemporaryDirectory

from build_portfolio import BASE, build


def main():
    data = json.loads((BASE / 'portfolio.json').read_text(encoding='utf-8-sig'))
    with TemporaryDirectory(prefix='yohan-portfolio-') as temp:
        public = Path(temp) / 'public'
        build(data, public, editor_api='/__editor')
        bootstrap = secrets.token_urlsafe(32)
        handler = handler_for(temp, [public], bootstrap)
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            url = f'http://127.0.0.1:{server.server_port}/'
            owner = url+'#owner='+bootstrap
            print(f'방문자 미리보기: {url}\n소유자 주소 (공유 금지): {owner}\n종료: Ctrl+C', flush=True)
            webbrowser.open_new_tab(owner)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
