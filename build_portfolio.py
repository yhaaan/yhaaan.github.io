"""Build a read-only portfolio. Requires only Python 3.10+ (no CMS at runtime)."""
import argparse
import json
import re
import shutil
from html import escape
from pathlib import Path, PurePosixPath
from string import Template
from tempfile import TemporaryDirectory
from urllib.parse import quote, urlsplit

BASE = Path(__file__).resolve().parent
SITE = BASE / 'site'
OUT = BASE / 'dist' / 'portfolio'


def field(record, key, required=False):
    value = record.get(key) or ''
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f'{key}: 텍스트 값을 확인하세요.')
    return escape(value.strip())


def link(value, label):
    if not value:
        return ''
    parsed = urlsplit(value)
    if parsed.scheme != 'https' or not parsed.hostname or any(c.isspace() for c in value):
        raise ValueError(f'{label}: https:// 로 시작하는 전체 주소가 필요합니다.')
    return f'<a href="{escape(value)}">{label} ↗</a>'


def build(data, out, site=SITE):
    """Render into a new/empty output directory; only copy referenced media."""
    template = Template((site / 'index.html').read_text(encoding='utf-8'))
    profile = data['profile']
    name = field(profile, 'name', True)
    brand = field(profile, 'handle') or name
    intro = field(profile, 'intro')
    groups = [('projects', '프로젝트', 'SELECTED WORK'), ('skills', '스킬', 'TOOLKIT'),
              ('experience', '이력', 'TIMELINE'), ('photos', '사진', 'GALLERY'),
              ('archive', '이전 프로필', 'FROM THE ARCHIVE')]
    skill_groups = [('많이 해봤어요', data.get('skills') or []), ('해본 적 있어요', data.get('otherSkills') or [])]
    counts = {key: len(data.get(key) or []) for key, _, _ in groups}
    counts['skills'] = sum(len(items) for _, items in skill_groups)
    visible = [g for g in groups if counts[g[0]]]

    def image(record, root, alt, css=''):
        raw = record.get('image')
        if not raw:
            return ''
        path = PurePosixPath(raw)
        if (not raw.startswith('/media/') or '..' in path.parts or '\\' in raw
                or path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif')):
            raise ValueError(f'지원하지 않는 이미지 경로: {raw}')
        rel = path.relative_to('/')
        src = (site / rel).resolve()
        if not src.is_relative_to((site / 'media').resolve()) or not src.is_file():
            raise ValueError(f'업로드 파일을 찾을 수 없습니다: {raw}')
        dest = out / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        return f'<img class="{css}" src="{root}{quote(str(rel))}" alt="{alt}" loading="lazy">'

    def write_page(path, root, title, description, body):
        home = f'{root}index.html' if root else ''
        nav = ''.join(f'<a href="{home}#{key}">{label}</a>' for key, label, _ in visible)
        page = template.substitute(root=root, name=name, brand=brand, title=title,
                                   description=description, nav=nav, content=body)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page, encoding='utf-8')

    def section(key, label, kicker, contents):
        return (f'<section class="section" id="{key}"><div class="section-head"><h2>{label}</h2>'
                f'<span class="label" lang="en">{kicker} / {counts[key]:02}</span></div>{contents}</section>')

    def project_pages():
        cards = []
        slugs = set()
        for i, p in enumerate(data['projects'], start=1):
            slug = p.get('slug') or ''
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or slug in slugs:
                raise ValueError(f'잘못되었거나 중복된 프로젝트 주소: {slug}')
            slugs.add(slug)
            title = field(p, 'title', True)
            summary = field(p, 'summary')
            category = field(p, 'category') or 'PROJECT'
            live = link(p.get('url'), '사이트 열기')
            source = link(p.get('source'), '소스 보기')
            href = f'projects/{slug}/'
            art = image(p, '', '') or f'<i></i><span>FIG. {i:02} / PROJECT FILE</span>'
            cards.append(f'<article class="project"><div aria-hidden="true" class="cover">{art}</div>'
                         f'<div><span class="serial">NO. {i:02} · {category}</span><h3><a href="{href}">{title}</a></h3>'
                         f'<p class="copy">{summary}</p><div class="links"><a href="{href}">상세 보기 →</a>{live}</div></div></article>')
            root = '../../'
            paragraphs = []
            for block in p.get('sections') or []:
                heading = field(block, 'title', True)
                caption = field(block, 'caption')
                pic = image(block, root, caption or heading)
                figure = f'<figure>{pic}<figcaption>{caption}</figcaption></figure>' if pic else ''
                paragraphs.append(f'<section><h2>{heading}</h2><p class="copy">{field(block, "text")}</p>{figure}</section>')
            detail = (f'<article class="detail"><a class="back" href="{root}index.html#projects">← 프로젝트 목록</a>'
                      f'<header><p class="label">PROJECT FILE / {category}</p><h1>{title}</h1>'
                      f'<p class="lead">{summary}</p><div class="links">{live}{source}</div>{image(p, root, title)}</header>'
                      + ''.join(paragraphs) + '</article>')
            write_page(out / href / 'index.html', root, f'{title} | {name} 포트폴리오', summary or title, detail)
        return ''.join(cards)

    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(site / 'portfolio.css', out / 'portfolio.css')
    (out / '.nojekyll').touch()
    portrait = image(profile, '', f'{name} 프로필 사진', 'portrait')
    badge = portrait or '<div class="plate" aria-hidden="true"><span>PERSONAL INDEX</span></div>'
    github = link(profile.get('github'), 'GitHub')
    contact = f'<div class="links">{github}</div>' if github else ''
    parts = [f'<header class="hero"><div><p class="label">{brand} &nbsp;/&nbsp; PERSONAL ARCHIVE</p>'
             f'<h1>{name}의<br>포트폴리오.</h1><p class="lead copy">{intro}</p>{contact}</div>{badge}</header>']
    for key, label, kicker in visible:
        rows = data.get(key) or []
        if key == 'projects':
            contents = project_pages()
        elif key == 'skills':
            contents = ''.join(f'<h3>{level}</h3><ul class="tags">'
                               + ''.join(f'<li>{escape(s)}</li>' for s in items) + '</ul>'
                               for level, items in skill_groups if items)
        elif key == 'experience':
            contents = ''.join(f'<article class="entry"><span class="serial">{field(e, "period")}</span>'
                               f'<h3>{field(e, "title", True)}</h3><p class="copy">{field(e, "text")}</p>'
                               f'{link(e.get("url"), "관련 자료")}</article>' for e in rows)
        elif key == 'photos':
            figures = []
            for photo in rows:
                caption = field(photo, 'caption', True)
                pic = image(photo, '', caption)
                if not pic:
                    raise ValueError(f'사진을 선택하세요: {caption}')
                figures.append(f'<figure>{pic}<figcaption>{caption}</figcaption></figure>')
            contents = '<div class="gallery">' + ''.join(figures) + '</div>'
        else:
            contents = ''.join(f'<details><summary>{field(e, "title", True)}</summary><p class="copy">{field(e, "text")}</p></details>' for e in rows)
        parts.append(section(key, label, kicker, contents))
    write_page(out / 'index.html', '', f'{name} | 포트폴리오', intro or f'{name} 포트폴리오', ''.join(parts))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--content', type=Path, default=BASE / 'portfolio.json')
    args = parser.parse_args()
    data = json.loads(args.content.read_text(encoding='utf-8-sig'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=OUT.parent) as temp:
        stage = Path(temp) / 'portfolio'
        build(data, stage)
        if OUT.exists():
            shutil.rmtree(OUT)
        stage.rename(OUT)
    print(f'정적 페이지 생성: {OUT}')


if __name__ == '__main__':
    main()
