"""Loopback-only owner API. Serves generated files, never the repository itself."""
import base64
import hashlib
import json
import re
import secrets
import threading
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from tempfile import NamedTemporaryFile, mkdtemp

from build_portfolio import BASE, build


def revision(raw):
    return hashlib.sha256(raw).hexdigest()


def handler_for(temp, public, bootstrap, *, base=BASE):
    sessions = set()
    lock = threading.Lock()
    source = base / 'portfolio.json'
    site = base / 'site'

    class Handler(SimpleHTTPRequestHandler):
        extensions_map = {**SimpleHTTPRequestHandler.extensions_map, '.mjs': 'text/javascript', '.js': 'text/javascript'}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(public[0]), **kwargs)

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            super().end_headers()

        def reply(self, status, obj):
            raw = json.dumps(obj, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            host = f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host') != host or self.headers.get('Origin') != 'http://' + host:
                return self.reply(403, {'error': '로컬 편집 창에서만 저장할 수 있습니다.'})
            auth = self.headers.get('Authorization', '')
            if self.headers.get_content_type() != 'application/json':
                return self.reply(415, {'error': 'JSON 요청이 필요합니다.'})
            with lock:
                if self.path == '/__editor/local-login' and secrets.compare_digest(auth.encode(), ('Bearer '+bootstrap).encode()):
                    session = secrets.token_urlsafe(32)
                    sessions.add('Bearer '+session)
                    return self.reply(200, {'session': session})
                if auth not in sessions:
                    return self.reply(401, {'error': '실행 창의 소유자 주소로 다시 열어 주세요.'})
                if self.path == '/__editor/logout':
                    sessions.discard(auth)
                    return self.reply(200, {})
                raw = source.read_bytes()
                if self.path == '/__editor/read':
                    return self.reply(200, {'data': json.loads(raw), 'version': revision(raw)})
                if self.path != '/__editor/save':
                    return self.reply(404, {'error': '없는 경로입니다.'})
                created = []
                tmpfile = None
                try:
                    n = int(self.headers.get('Content-Length', 0))
                    if not 0 < n <= 8*1024*1024:
                        raise ValueError('한 번에 저장할 사진 크기를 줄이세요.')
                    req = json.loads(self.rfile.read(n))
                    if req['version'] != revision(raw):
                        return self.reply(409, {'error': '원본이 변경되었습니다. 최신 내용에서 다시 편집하세요.'})
                    data = req['data']
                    encoded = (json.dumps(data, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
                    if len(encoded)>800000:
                        raise ValueError('텍스트가 너무 큽니다.')
                    for item in req.get('uploads', []):
                        path = item['path']
                        if not re.fullmatch(r'/media/pic-[a-f0-9-]{36}\.(png|jpg|webp)', path):
                            raise ValueError('잘못된 사진 경로입니다.')
                        img = base64.b64decode(item['content'], validate=True)
                        valid = {'.png': img.startswith(b'\x89PNG\r\n\x1a\n'), '.jpg': img.startswith(b'\xff\xd8\xff'), '.webp': img[:4]==b'RIFF' and img[8:12]==b'WEBP'}
                        dest = site / path.lstrip('/')
                        if not valid[dest.suffix] or len(img)>2097152 or dest.parent.resolve() != site / 'media':
                            raise ValueError('2MB 이하의 JPEG, PNG, WebP 사진을 선택하세요.')
                        dest.parent.mkdir(exist_ok=True)
                        with dest.open('xb') as f:
                            created.append(dest)
                            f.write(img)
                    stage = Path(mkdtemp(dir=temp))
                    build(data, stage, site, editor_api='/__editor')
                    if any(not (stage / 'media' / p.name).is_file() for p in created):
                        raise ValueError('사용하지 않는 업로드 파일이 있습니다.')
                    with NamedTemporaryFile(dir=base, delete=False) as f:
                        tmpfile = Path(f.name)
                        f.write(encoded)
                    if source.read_bytes() != raw:
                        return self.reply(409, {'error': '다른 수정이 감지되었습니다.'})
                    tmpfile.replace(source)
                    created.clear()
                    public[0] = stage
                    return self.reply(200, {'version':revision(encoded)})
                except (ValueError, KeyError, TypeError, AttributeError, OSError) as e:
                    return self.reply(400, {'error': '저장 실패: '+str(e)})
                finally:
                    for path in created:
                        path.unlink(missing_ok=True)
                    if tmpfile:
                        tmpfile.unlink(missing_ok=True)
    return Handler
