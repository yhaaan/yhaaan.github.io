# 렌즈 노트

운영자가 공개한 창작 게임 디자인 렌즈를 누구나 번호와 키워드로 찾아볼 수 있는 읽기 전용 정적 사이트입니다. 방문자는 내용을 검색하고 읽을 수만 있으며, 렌즈 추가·수정·가져오기·백업 기능은 제공하지 않습니다.

## 공개 방식

- 모든 방문자는 저장소의 `data/lenses.json`에서 빌드된 동일한 내용을 봅니다.
- 사이트는 브라우저의 `localStorage`를 콘텐츠 저장소로 사용하지 않습니다.
- 공개 내용을 바꾸려면 이 GitHub 저장소에 쓰기 권한이 있어야 합니다.
- `main` 브랜치에 변경 사항이 반영되면 GitHub Actions가 사이트를 다시 배포합니다.

즉, 일반 방문자가 자신의 브라우저에서 사이트 내용을 바꾸거나 공용 콘텐츠를 덮어쓸 수 없습니다.

## GitHub 웹에서 렌즈 내용 올리기

로컬 개발 환경 없이 GitHub 웹사이트만으로 업데이트할 수 있습니다.

1. 공개할 JSON을 준비하고 파일 이름을 `lenses.json`으로 지정합니다.
2. 저장소에서 `data/lenses.json`을 엽니다.
3. 내용을 직접 고치려면 연필 모양 **Edit this file**을 누르고 JSON 전체를 수정합니다.
4. 파일을 통째로 바꾸려면 `data` 폴더에서 **Add file → Upload files**를 눌러 새 `lenses.json`을 올립니다.
5. **Commit changes**로 `main` 브랜치에 반영합니다.
6. 저장소의 **Actions** 탭에서 `Deploy to GitHub Pages` 작업이 성공했는지 확인합니다.

배포에 실패하면 기존 사이트는 그대로 유지됩니다. 잘못 올렸다면 해당 커밋을 **Revert**하거나 `data/lenses.json`의 **History**에서 이전 버전을 복원할 수 있습니다.

## JSON 형식

기존 사이트의 **백업 내보내기**로 만든 JSON 형식과 호환됩니다. 최상위 구조는 다음과 같습니다.

```json
{
  "appId": "art-of-game-design-lens-notes",
  "schemaVersion": 1,
  "edition": 2,
  "language": "ko",
  "exportedAt": null,
  "lenses": [
    {
      "number": 1,
      "title": "렌즈 제목",
      "content": "공개할 내용",
      "keywords": ["선택", "피드백"],
      "notes": "공개할 보충 메모",
      "favorite": false,
      "updatedAt": null
    }
  ]
}
```

`lenses`에는 1번부터 113번까지 정확히 113개의 항목이 있어야 하며 번호가 중복되면 안 됩니다. `favorite` 값은 호환성을 위해 파일에 남아 있지만 공개 사이트에서는 사용하지 않습니다. `notes`를 포함해 JSON에 넣은 모든 텍스트는 공개 저장소와 사이트에서 누구나 볼 수 있으므로 공개할 내용만 넣으세요.

## 검색과 열람

- `42` 또는 `#42`로 정확한 번호 검색
- 제목·내용·키워드·보충 메모 검색
- 전체·공개됨·준비 중 필터
- 공개된 렌즈의 읽기 전용 상세 화면
- 데스크톱과 모바일 반응형 화면

## 로컬 검증(선택 사항)

Node.js 22 이상에서 다음 명령으로 빌드와 자동 검증을 실행할 수 있습니다.

```bash
npm ci
npm test
npm run lint
```

정적 결과물은 `dist/client`에 생성됩니다.

## GitHub Pages 설정

저장소의 **Settings → Pages → Build and deployment**에서 Source를 **GitHub Actions**로 선택합니다. 포함된 `.github/workflows/deploy-pages.yml`은 `main` 브랜치가 변경될 때 `dist/client`을 배포합니다.

사용자 사이트(`계정명.github.io`)와 프로젝트 사이트(`계정명.github.io/저장소명`)를 모두 지원하도록 자산 경로가 자동 설정됩니다.
