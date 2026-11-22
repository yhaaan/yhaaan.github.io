# yhaaan 포트폴리오

개인 포트폴리오를 위한 GitHub Pages 저장소입니다.

- 포트폴리오: https://yhaaan.github.io/
- 렌즈 노트: https://yhaaan.github.io/lens-notes/
- 렌즈 노트 소스: https://github.com/yhaaan/lens-notes

렌즈 노트의 코드, 데이터, 운영자 수정 워크플로와 기존 커밋 이력은 별도 `lens-notes` 저장소에 보존했습니다. 기존 방문자의 개인 노트는 같은 도메인과 저장 키를 사용하므로 같은 브라우저에서 이어집니다.

## 소유자용 웹 편집기 (최초 1회 연결)

1. 이 변경 사항을 `main`에 반영하고 저장소 **Settings → Pages → Source**를 **GitHub Actions**로 설정합니다.
2. [Pages CMS](https://app.pagescms.org/)에 저장소 소유자 GitHub 계정으로 로그인합니다. Pages CMS GitHub App 설치 시 **Only select repositories**로 `yhaaan.github.io`만 선택합니다.
3. 이 저장소의 `main`을 열면 `.pages.yml` 설정으로 **내 포트폴리오** 폼이 나타납니다. 이 편집기 주소를 본인 브라우저에 즐겨찾기 해 두세요. 공개 페이지에는 편집기로 가는 링크나 로그인 코드가 없습니다.
4. **소유자만 편집하려면** GitHub 저장소의 쓰기 권한을 본인에게만 두고 Pages CMS에도 다른 편집자를 초대하지 마세요. 권한은 비밀 URL이나 브라우저 저장소가 아니라 GitHub/Pages CMS에서 검사합니다. 쓰기가 가능한 협업자, 앱, 팀이 있으면 권한을 먼저 점검하세요. 공개 저장소의 소스와 공개된 콘텐츠 자체는 비밀이 아닙니다.

## 평소 사용법

- **내 포트폴리오**에서 스킬·이력·사진·프로젝트 목록에 항목을 추가하거나 수정·삭제하고 저장합니다. 목록 순서대로 보이며, 빈 목록은 방문자 메뉴와 페이지에서 사라집니다.
- 프로젝트는 **주소 이름**(예: `lens-notes`)으로 `/projects/lens-notes/` 상세 페이지가 만들어집니다. **상세 본문 단락**마다 소제목·글·사진을 자유롭게 구성할 수 있습니다. 프로젝트를 삭제하면 다음 배포에서 카드와 상세 페이지가 함께 제거됩니다.
- 이미지 필드에서 파일을 업로드하거나 기존 파일을 선택합니다. JPG/JPEG, PNG, WebP, GIF, AVIF를 지원합니다. 사진을 교체하거나 삭제할 때에는 먼저 콘텐츠의 참조를 바꾸고 저장한 뒤, 필요하면 미디어 보관함에서 남은 원본을 삭제하세요. 업로드한 파일은 저장소에 기록되므로 비공개 사진은 올리지 마세요.
- 저장 → `portfolio.json`과 업로드 파일이 저장소에 기록 → Actions가 검증·빌드·배포합니다. **Actions → Deploy portfolio to GitHub Pages**에서 성공한 뒤 공개 주소를 새로고침하세요. 중복 주소나 누락된 이미지로 빌드가 실패하면 기존 배포가 유지됩니다. 오류를 고쳐 다시 저장하세요. 브랜치 보호 규칙이 있다면 CMS의 `main` 저장을 허용하는지도 확인해야 합니다.

## 예전 Notion PDF로 초기 데이터 채우기 (선택, 로컬 1회)

초기 콘텐츠는 Notion의 Markdown·CSV 내보내기에서 옮겼습니다. 프로필 소개, 두 그룹의 스킬 9개, 활동 23건과 학력·수상, 프로젝트 14개를 `portfolio.json`에 담았고 기존 렌즈 노트도 유지합니다. 원본 폴더나 PDF가 없어도 빌드와 CMS 편집이 가능합니다. 생년월일·이메일·증명사진은 기본 공개 콘텐츠에 포함하지 않았습니다. 사진을 쓰려면 CMS의 **프로필 → 프로필 사진**에서 원하는 파일을 업로드하세요.

일반적인 사용에는 PDF 가져오기가 필요하지 않습니다. 별도로 예전 PDF의 추출 가능한 텍스트를 페이지 단위의 편집 가능한 **이전 프로필** 항목으로 옮길 수 있습니다. 서식·사진은 자동 변환하지 않으며, 이미지뿐인 페이지에는 OCR 또는 Notion 텍스트 내보내기가 필요합니다.

루트에 기존 `요한 Profile 181104fc6ad4806092f8e403d60d90f9.pdf`를 둔 상태에서 다음을 실행하세요 (Python 3.10+).

```powershell
python -m pip install pypdf
python import_notion.py
python build_portfolio.py --content work/portfolio.json
python -m http.server 8000 --bind 127.0.0.1 --directory dist/portfolio
```

`http://127.0.0.1:8000/`에서 초안을 확인하세요. `work/portfolio.json`은 현재 콘텐츠를 복사한 뒤 원문을 덧붙인 로컬 초안입니다. 기존 초안은 덮어쓰지 않습니다. PDF 내 줄바꿈·연락처 등 공개 여부를 검토하고, 필요하면 편집한 다음 **다른 CMS 수정을 하기 전** `Copy-Item work/portfolio.json portfolio.json`으로 적용합니다. 중간에 다른 수정이 있었다면 `archive` 항목만 합치세요. 다음 배포부터 웹 편집기에서도 수정할 수 있습니다. 원본 PDF와 `work/`는 Git에서 제외하며, 빌드는 PDF를 복사하지 않습니다.

## 로컬 미리보기 및 검증

Windows에서는 프로젝트 폴더의 **`preview.cmd`를 더블클릭**하세요 (Python 3.10 이상 필요). macOS·Linux에서는 `python3 preview_portfolio.py`로 실행합니다. 공개 페이지와 같은 방식으로 임시 폴더에 빌드하고, 내 컴퓨터에서만 열리는 빈 포트로 서버를 시작합니다. 브라우저가 자동으로 열리지 않으면 실행 창에 표시된 주소를 복사하세요. 창에서 `Ctrl+C`를 누르면 종료됩니다. 내용을 바꾼 뒤에는 다시 실행하세요.

실행 창에 `[Python not found]`가 나오면 `py -3`와 `python` 어느 쪽으로도 Python 3.10 이상을 실행하지 못한 상태입니다. 이미 설치했다면 `py -0p` 또는 `python --version`으로 경로·버전을 확인하고, 설치하지 않았다면 [Windows용 Python](https://www.python.org/downloads/windows/)을 설치한 뒤 실행 창을 새로 여세요. `[Python OK]` 다음에 `[Preview error]`가 나온 경우 Python 재설치부터 하지 말고, `[Preview error]` **바로 위의 오류**를 확인하세요.

아래는 테스트와 배포용 결과물까지 직접 확인하는 방법입니다.

```powershell
python -m unittest test_portfolio
python build_portfolio.py
python -m http.server 8000 --bind 127.0.0.1 --directory dist/portfolio
```

일반 빌드는 외부 패키지를 쓰지 않습니다. `site/index.html`은 공통 템플릿, `site/portfolio.css`는 스타일, `site/media/`는 CMS 업로드 경로입니다. 배포 대상은 매번 새로 생성하는 `dist/portfolio/`의 HTML·CSS 및 참조된 이미지뿐입니다. 직접 HTML 결과물을 편집하지 마세요.
