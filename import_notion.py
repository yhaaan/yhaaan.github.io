"""Extract the legacy Notion PDF into a local, editable portfolio draft, never the live file."""
import argparse
import json
from pathlib import Path

from build_portfolio import BASE

PDF = BASE / '요한 Profile 181104fc6ad4806092f8e403d60d90f9.pdf'
DRAFT = BASE / 'work' / 'portfolio.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf', type=Path, nargs='?', default=PDF)
    args = parser.parse_args()
    try:
        from pypdf import PdfReader
    except ImportError:
        parser.exit(1, '먼저 python -m pip install pypdf 를 실행하세요.\n')
    if not args.pdf.is_file():
        parser.exit(1, f'PDF가 없습니다: {args.pdf}\n')
    if DRAFT.exists():
        parser.exit(1, f'기존 초안을 보호하기 위해 중단합니다. 파일을 먼저 옮겨 주세요: {DRAFT}\n')
    data = json.loads((BASE / 'portfolio.json').read_text(encoding='utf-8-sig'))
    pages = []
    skipped = []
    for n, page in enumerate(PdfReader(args.pdf).pages, 1):
        text = (page.extract_text() or '').strip()
        if text:
            pages.append({'title': f'요한 Profile · {n}쪽', 'text': text})
        else:
            skipped.append(n)
    if skipped:
        print('추출 가능한 텍스트가 없는 쪽 (이미지/OCR 확인 필요):', *skipped)
    if not pages:
        parser.exit(1, '텍스트를 읽을 수 없어 초안을 만들지 않았습니다. Notion의 Markdown 내보내기 또는 OCR 텍스트가 필요합니다.\n')
    data['archive'] = (data.get('archive') or []) + pages
    DRAFT.parent.mkdir(exist_ok=True)
    with DRAFT.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')
    print(f'{len(pages)}쪽을 로컬 초안에 담았습니다: {DRAFT}')
    print('원문·줄바꿈·연락처를 검토하세요. 원본 PDF, 사진 및 초안은 자동 게시되지 않습니다.')


if __name__ == '__main__':
    main()
