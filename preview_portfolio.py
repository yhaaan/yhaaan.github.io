"""Build and open a private, local preview of the exact site, without publishing."""
import json
import webbrowser
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from build_portfolio import BASE, build


def main():
    data = json.loads((BASE / 'portfolio.json').read_text(encoding='utf-8-sig'))
    with TemporaryDirectory(prefix='yohan-portfolio-') as temp:
        public = Path(temp) / 'public'
        build(data, public)
        handler = partial(SimpleHTTPRequestHandler, directory=str(public))
        with ThreadingHTTPServer(('127.0.0.1', 0), handler) as server:
            url = f'http://127.0.0.1:{server.server_port}/'
            print(f'포트폴리오 미리보기: {url}\n종료하려면 Ctrl+C를 누르세요.', flush=True)
            webbrowser.open_new_tab(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
