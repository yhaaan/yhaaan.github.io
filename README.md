# yhaaan 포트폴리오

개인 포트폴리오를 위한 GitHub Pages 저장소입니다.

- 포트폴리오: https://yhaaan.github.io/
- 렌즈 노트: https://yhaaan.github.io/lens-notes/
- 렌즈 노트 소스: https://github.com/yhaaan/lens-notes

렌즈 노트의 코드, 데이터, 운영자 수정 워크플로와 기존 커밋 이력은 별도 `lens-notes` 저장소에 보존했습니다. 기존 방문자의 개인 노트는 같은 도메인과 저장 키를 사용하므로 같은 브라우저에서 이어집니다.

## 내 사이트에서 바로 편집하기

**내 PC:** `preview.cmd`를 다시 실행하세요. 위쪽 **편집 모드**에서 소개, 제목, 본문, 메뉴 문구를 클릭하면 해당 입력란이 선택된 편집창이 열립니다. **내 PC에 저장**은 로컬 `portfolio.json`과 사진을 저장하고 화면을 갱신합니다. **탐색으로 전환**하면 분류 탭과 카드가 일반 방문자처럼 동작합니다. 빈 항목 추가, 사진, 영상은 위쪽 선택 메뉴의 **항목 관리**에서 수정하세요. 자동 커밋·푸시는 없습니다. 소유자 주소는 공유하지 마세요.

메인에는 한 줄 소개와 프로젝트 카드가 표시됩니다. 탐색 모드에서 소개를 누르면 그 아래에 프로필이 펼쳐집니다. 상단의 **프로필**과 **활동**은 해당 영역을 열고 같은 메인 화면에서 이동합니다. 프로필 사진은 **프로필 → 항목 관리 → 사진**에서 추가할 수 있습니다. 수상·AI 분류는 프로젝트와 이력의 문구에서 자동 계산되며, 편집 모드에서 개수를 누르면 관련 항목을 관리할 수 있습니다.

프로젝트 상세의 **영상**에는 HTTPS MP4/WebM 직접 주소를 넣습니다. 자동 재생이 가능한 경우 음소거로 재생한 뒤 사진 슬라이드로 넘어갑니다. 대표 사진과 상세 단락 사진이 슬라이드에 포함됩니다. 호버·키보드 포커스·백그라운드에서는 자동 진행을 멈추며, 동작 줄이기 설정도 존중합니다. 미디어가 없으면 제목 표지를 보여줍니다.

**공개 사이트:** 아래 최초 설정 후 홈이나 상세 페이지의 주소 끝에 `#edit`를 붙이고 GitHub 로그인을 선택하세요. 인증 후 원래 포트폴리오 화면에 편집 버튼이 생깁니다. **저장 및 게시**는 GitHub `main`에 콘텐츠와 사진만 한 커밋으로 기록합니다. Actions 배포 성공 후 새로고침하세요. 다른 변경이 먼저 저장됐으면 덮어쓰지 않고 충돌을 알립니다. 사진은 1장 2MiB 이하의 JPEG·PNG·WebP, 한 번에 총 5MiB까지입니다. 사진 또는 프로젝트를 삭제하면 다음 배포에서 사이트에서 사라지지만 이전 커밋과 저장소 원본까지 지워지는 것은 아닙니다. 프로젝트 주소 이름을 바꾸면 이전 상세 주소도 사라집니다.

### 공개 편집 API 최초 설정 (소유자만)

GitHub Pages에는 쓰기 서버가 없으므로 Cloudflare Worker(`editor-worker.mjs`)를 별도로 배포합니다. **편집하는 장소는 Worker나 외부 CMS가 아니라 포트폴리오 페이지**입니다. 이 설정을 생략하면 공개 배포는 읽기 전용이며 로컬 편집은 그대로 가능합니다.

1. GitHub 계정 Settings → Developer settings → GitHub Apps에서 개인용 앱을 만드세요. Homepage 및 **Callback URL**은 `https://yhaaan.github.io/`, 웹훅은 끄고 Repository permissions는 **Contents: Read and write**와 기본 Metadata만 허용하세요. 설치 가능 계정은 본인만, Install App에서는 `yhaaan.github.io` 저장소만 선택합니다. OAuth용 **Client ID**와 Client secret을 사용합니다(App ID나 private key 아님). 값은 채팅에 붙이지 마세요.
2. Cloudflare Workers KV에 세션용 namespace 하나를 만듭니다. `wrangler.editor.example.toml`을 `wrangler.editor.toml`로 복사해 `SESSIONS`의 namespace ID, GitHub App의 공개 Client ID, [본인 계정 정보](https://api.github.com/users/yhaaan)의 숫자 `id`를 채우세요. 현재 Worker의 출처·저장소는 `yhaaan.github.io`로 고정되어 있습니다.
3. Node.js와 Wrangler CLI가 가능한 환경에서 `npx wrangler login`, `npx wrangler deploy --config wrangler.editor.toml`을 실행한 후 `npx wrangler secret put GITHUB_CLIENT_SECRET --config wrangler.editor.toml`의 비공개 입력창에 OAuth secret을 등록합니다. 비밀값은 Pages 설정, HTML 또는 Git에 넣지 마세요.
4. GitHub 저장소 **Settings → Secrets and variables → Actions → Variables**에 `PORTFOLIO_EDITOR_API`를 추가합니다. 값은 위 Worker의 **공개 https 출처**(예: `https://yohan-portfolio-editor.example.workers.dev`, 경로 없음)입니다. Pages Source는 GitHub Actions로 설정하고 `main`에 이 코드를 반영한 뒤 **Deploy portfolio to GitHub Pages**를 실행하세요. 변수를 나중에 넣었다면 워크플로를 다시 실행해야 합니다.
5. `https://yhaaan.github.io/#edit`에서 로그인하고 소유자 표시줄을 확인하세요. 일반 시크릿 창에서 기본 주소에는 편집 버튼이 없어야 합니다. 저장이 거부되면 App 설치 범위·Contents 권한·브랜치 보호와 **Actions** 결과를 확인하세요. 예전 Pages CMS 앱을 설치했다면 GitHub Settings → Applications에서 해당 앱의 기존 쓰기 권한도 직접 해제하세요.

Worker가 OAuth 코드와 PKCE 검증값을 교환하고 GitHub 사용자 숫자 ID와 로그인명을 검사합니다. GitHub 토큰은 브라우저에 넘기지 않고 만료되는 서버 KV 세션에만 보관합니다. 브라우저에는 이 API 전용 세션 ID만 탭 저장소에 두며, 읽기·저장 요청마다 서버가 GitHub 신원을 다시 검사합니다. `#edit` 자체는 권한이 아닙니다. 세션은 30분 후 만료되며 **편집 종료**로 종료할 수 있습니다. 같은 도메인에 배포하는 다른 앱의 자바스크립트도 신뢰할 수 있어야 합니다.

## 예전 Notion PDF로 초기 데이터 채우기 (선택, 로컬 1회)

초기 콘텐츠는 Notion의 Markdown·CSV 내보내기에서 옮겼습니다. 프로필 소개, 두 그룹의 스킬 9개, 활동 23건과 학력·수상, 프로젝트 14개를 `portfolio.json`에 담았고 기존 렌즈 노트도 유지합니다. 원본 폴더나 PDF가 없어도 빌드와 사이트 내 편집이 가능합니다. 생년월일·이메일·증명사진은 기본 공개 콘텐츠에 포함하지 않았습니다. 사진을 쓰려면 홈의 **프로필 편집 → 사진**에서 파일을 선택해 저장하세요.

일반적인 사용에는 PDF 가져오기가 필요하지 않습니다. 별도로 예전 PDF의 추출 가능한 텍스트를 페이지 단위의 편집 가능한 **이전 프로필** 항목으로 옮길 수 있습니다. 서식·사진은 자동 변환하지 않으며, 이미지뿐인 페이지에는 OCR 또는 Notion 텍스트 내보내기가 필요합니다.

루트에 기존 `요한 Profile 181104fc6ad4806092f8e403d60d90f9.pdf`를 둔 상태에서 다음을 실행하세요 (Python 3.10+).

```powershell
python -m pip install pypdf
python import_notion.py
python build_portfolio.py --content work/portfolio.json
python -m http.server 8000 --bind 127.0.0.1 --directory dist/portfolio
```

`http://127.0.0.1:8000/`에서 초안을 확인하세요. `work/portfolio.json`은 현재 콘텐츠를 복사한 뒤 원문을 덧붙인 로컬 초안입니다. 기존 초안은 덮어쓰지 않습니다. PDF 내 줄바꿈·연락처 등 공개 여부를 검토하고, 필요하면 편집한 다음 **다른 콘텐츠 수정을 하기 전** `Copy-Item work/portfolio.json portfolio.json`으로 적용합니다. 중간에 다른 수정이 있었다면 `archive` 항목만 합치세요. 다음 배포부터 웹 편집기에서도 수정할 수 있습니다. 원본 PDF와 `work/`는 Git에서 제외하며, 빌드는 PDF를 복사하지 않습니다.

## 로컬 미리보기 및 검증

Windows에서는 프로젝트 폴더의 **`preview.cmd`를 더블클릭**하세요 (Python 3.10 이상 필요). macOS·Linux에서는 `python3 preview_portfolio.py`로 실행합니다. 공개 페이지와 같은 방식으로 임시 폴더에 빌드하고, 내 컴퓨터에서만 열리는 빈 포트로 서버를 시작합니다. 브라우저가 자동으로 열리지 않으면 실행 창에 표시된 주소를 복사하세요. 창에서 `Ctrl+C`를 누르면 종료됩니다. 내용을 바꾼 뒤에는 다시 실행하세요.

실행 창에 `[Python not found]`가 나오면 `py -3`와 `python` 어느 쪽으로도 Python 3.10 이상을 실행하지 못한 상태입니다. 이미 설치했다면 `py -0p` 또는 `python --version`으로 경로·버전을 확인하고, 설치하지 않았다면 [Windows용 Python](https://www.python.org/downloads/windows/)을 설치한 뒤 실행 창을 새로 여세요. `[Python OK]` 다음에 `[Preview error]`가 나온 경우 Python 재설치부터 하지 말고, `[Preview error]` **바로 위의 오류**를 확인하세요.

아래는 테스트와 배포용 결과물까지 직접 확인하는 방법입니다.

```powershell
python -m unittest test_portfolio test_local_owner
node --test test_editor.mjs
python build_portfolio.py
python -m http.server 8000 --bind 127.0.0.1 --directory dist/portfolio
```

일반 빌드는 외부 패키지를 쓰지 않습니다. `site/index.html`은 공통 템플릿, `site/portfolio.css`는 스타일, `site/media/`는 사진 경로입니다. 배포 대상은 `dist/portfolio/`의 HTML·CSS·참조된 이미지와, 공개 편집 API를 설정했을 때만 포함되는 편집기 자산입니다. 서버 코드와 GitHub 자격 증명은 배포 대상에 포함하지 않습니다. 직접 HTML 결과물을 편집하지 마세요.
