"""Build a static portfolio. Requires only Python 3.10+."""
import argparse
import json
import os
import re
import shutil
from html import escape
from pathlib import Path, PurePosixPath
from string import Template
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, quote, urlsplit

BASE = Path(__file__).resolve().parent
SITE = BASE / 'site'
OUT = BASE / 'dist' / 'portfolio'

LABELS = {
    'skip': '본문 바로가기', 'main': 'MAIN', 'projectNav': '프로젝트', 'archiveNav': 'Archive',
    'profileNav': '프로필', 'activityNav': '활동', 'viewProfile': '프로필 보기',
    'allActivities': '이전 활동 더 보기', 'hideProfile': '프로필 닫기',
    'projects': '프로젝트', 'awards': '수상', 'ai': 'AI 프로젝트', 'empty': '아직 등록된 항목이 없습니다.',
    'intro': '프로젝트 소개', 'activity': '활동 소개', 'github': 'GitHub', 'baekjoon': 'solved.ac', 'live': '사이트 열기',
    'source': '소스 보기', 'related': '관련 자료', 'videoLink': '영상 열기', 'prev': '이전',
    'next': '다음', 'pause': '일시 정지', 'resume': '재생', 'archive': '아카이브',
    'skills': '스킬', 'toolkit': 'TOOLKIT', 'primary': '많이 해봤어요', 'secondary': '해본 적 있어요',
    'experience': '이력', 'photos': '사진', 'history': '이전 프로필', 'top': '맨 위로 ↑', 'footer': 'Portfolio',
    'highlights': '한눈에', 'award': '수상', 'aiChallengeTag': 'AI Challenge', 'profileTitle': 'Profile',
    'roleLabel': '역할', 'devPeriodLabel': '개발 기간', 'contributionLabel': '기여도',
    'contributionDetailLabel': '상세 기여',
}
ACTIVITY_KINDS = {'게임잼', '팀 활동', '공모전', '대외활동', '부트캠프', '전시', '동아리', '학력', '해커톤', '교내대회'}
LINK_KINDS = {
    'play': ('플레이', '<svg viewBox="0 0 16 16" width="14" height="14"><path d="M5 3.2v9.6L12.6 8z" fill="currentColor"/></svg>'),
    'source': ('GitHub', '<svg viewBox="0 0 16 16" width="15" height="15"><path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'),
}
KNOWN_HOSTS = (('store.steampowered.com', 'Steam에서 보기'), ('onstove.com', '스토브에서 보기'),
               ('play.unity.com', '플레이하기'), ('github.com', 'GitHub'), ('itch.io', 'itch.io에서 보기'))
DATED = re.compile(r'(\d{4})년\s*(\d{1,2})월\s+(.+)')
AI_SPLIT = {'AI에게 맡긴 것': 'by-ai', '내가 한 것': 'by-me'}
# Tier names are not shown; they only label the groups for assistive technology.
TIERS = (('1', 'featured', '대표작'), ('2', 'notable', '주목할 작품'), ('0', 'others', '그 밖의 작품'))
AI = re.compile(r'(?<![a-z0-9])ai(?![a-z0-9])|인공\s*지능', re.I)
HONOR = re.compile(r'특별상|(?:최)?우수상|장려상|챌린저\s*상|금상|은상|동상|(?:^|[·\s])대상\s*$|\b(?:prize|award)\b|수상(?:\s|$)', re.I)
COMPETITION = re.compile(r'공모전|대회|콘테스트|게임잼|해커톤|contest|competition', re.I)
RANK = re.compile(r'\d+\s*(?:위|등)(?![가-힣])')


def text(row, key, required=False):
    value = row.get(key, '')
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f'{key}: 텍스트 값을 확인하세요.')
    return value.strip()


def percent(row, key, required=False):
    raw = row.get(key, '')
    if raw == '' and not required:
        return None
    # Capture only the significant digits, even if the input has leading zeros.
    m = re.fullmatch(r'0*(100|[0-9]{1,2})', raw) if isinstance(raw, str) else None
    if not m:
        raise ValueError(f'{key}: 기여도는 0부터 100까지의 정수로 입력하세요.')
    return int(m[1])


def project_contribution(row):
    blocks = row.get('contributionAreas', [])
    if not isinstance(blocks, list):
        raise ValueError('분야별 기여도 목록을 확인하세요.')
    areas = []
    for block in blocks:
        if not isinstance(block, dict) or block.keys() - {'title', 'value'}:
            raise ValueError('분야별 기여도 항목을 확인하세요.')
        areas.append((text(block, 'title', True), percent(block, 'value', required=True)))
    lines = [line.strip() for line in text(row, 'contributionDetail').splitlines() if line.strip()]
    return text(row, 'devPeriod'), percent(row, 'contribution'), areas, lines


def youtube_id(parsed):
    """Return only an ID suitable for constructing our own thumbnail and embed URLs."""
    if parsed.port not in (None, 443):
        return ''
    host = re.sub(r'^(?:www\.|m\.)', '', parsed.hostname or '')
    if host == 'youtu.be':
        candidate = parsed.path[1:]
    elif host == 'youtube.com' and parsed.path == '/watch':
        ids = parse_qs(parsed.query, keep_blank_values=True).get('v', [])
        candidate = ids[0] if len(ids) == 1 else ''
    elif host == 'youtube.com' and parsed.path.startswith(('/shorts/', '/embed/')):
        candidate = parsed.path.split('/', 2)[2]
    else:
        return ''
    return candidate if re.fullmatch(r'[A-Za-z0-9_-]{11}', candidate) else ''


LOCAL_VIDEO = re.compile(r'/media/vid-[a-f0-9-]{36}\.(?:mp4|webm)')


def https_url(value, label, video=False):
    if value in (None, ''):
        return ''
    if video and isinstance(value, str) and value.startswith('/media/'):
        # A video file uploaded from the local editor lives next to the images.
        if not LOCAL_VIDEO.fullmatch(value):
            raise ValueError('영상: 업로드한 영상 파일 경로가 올바르지 않습니다.')
        return value
    try:
        if not isinstance(value, str) or not re.fullmatch(r'https://[^\s\\\x00-\x1f\x7f]+', value):
            raise ValueError
        parsed = urlsplit(value)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError
        _ = parsed.port  # Reject malformed ports as well as malformed hosts.
    except ValueError as exc:
        raise ValueError(f'{label}: https:// 로 시작하는 전체 주소가 필요합니다.') from exc
    if video and not parsed.path.lower().endswith(('.mp4', '.webm')) and not youtube_id(parsed):
        raise ValueError('영상: https MP4·WebM 파일 또는 YouTube 영상 주소가 필요합니다.')
    return value


def link_buttons(row, links, stretch=False):
    # Round icon buttons: a play triangle for a playable build, the GitHub mark for source code.
    out = ''
    for n, (kind, href) in enumerate(links):
        name = LINK_KINDS[kind][0]
        css = 'link-btn stretch' if stretch and n == 0 else 'link-btn'
        out += (f'<a class="{css}" data-link="{kind}" href="{escape(href)}" target="_blank" rel="noopener" '
                f'title="{name}"><span class="link-icon" aria-hidden="true">{LINK_KINDS[kind][1]}</span>'
                f'<span class="sr-only">{escape(text(row, "title"))} {name}</span></a>')
    return out


def media_position(row):
    # Where the video sits among the gallery images; absent means first.
    raw = row.get('videoAt', '')
    if raw == '':
        return 0
    if not isinstance(raw, str) or not re.fullmatch(r'[0-9]{1,3}', raw):
        raise ValueError('videoAt: 영상 위치는 0 이상의 정수여야 합니다.')
    return int(raw)


def first_image(row):
    # The project card uses the first image of the detail gallery.
    if text(row, 'image'):
        return row['image'], 'image'
    for j, block in enumerate(row.get('screens') or []):
        if isinstance(block, dict) and text(block, 'image'):
            return block['image'], f'screens.{j}.image'
    return '', 'image'


def timeline(body):
    """Split a record into (YYYY.MM, event) pairs when every line or sentence starts with a date."""
    parts = [p.strip() for p in re.split(r'\n+|(?<=[.。])\s+(?=\d{4}년)', body) if p.strip()]
    events = []
    for part in parts:
        m = DATED.fullmatch(part)
        if not m:
            return []
        events.append((f'{m[1]}.{int(m[2]):02}', m[3].rstrip('.。 ')))
    return events


def period_parts(period):
    """'2026.11' -> ('2026', '11월'); '2020~' -> ('2020', '~'); anything else keeps its text as the month cell."""
    m = re.fullmatch(r'(\d{4})(?:\.(\d{1,2}))?(.*)', period.strip())
    if not m:
        return '', period
    return m[1], (f'{int(m[2])}월' if m[2] else '') + m[3].strip()


def mapping(group, index, key):
    # All three arguments are renderer-owned identifiers, never record text.
    return f'data-edit-group="{group}" data-edit-index="{index}" data-edit-field="{key}"'


def span(group, index, key, value):
    return f'<span {mapping(group, index, key)}>{escape(value)}</span>'


def has_project_award(row):
    return bool(text(row, 'award'))


def is_ai_challenge(row):
    value = row.get('aiChallenge', '')
    if value not in ('', '1'):
        raise ValueError('aiChallenge: 지원하지 않는 값입니다.')
    return value == '1'


def content_flags(row):
    fragments = [text(row, k) for k in ('title', 'category', 'summary', 'text')]
    for section in row.get('sections') or []:
        fragments.extend(text(section, k) for k in ('title', 'text', 'caption'))
    evidence = '\n'.join(fragments).strip()
    award = (text(row, 'award') or HONOR.search(evidence)
             or (COMPETITION.search(evidence) and RANK.search(evidence)))
    return bool(award), bool(AI.search(evidence))


class Portfolio:
    def __init__(self, data, out, site, editor_api):
        self.data, self.out, self.site, self.api = data, out, site, editor_api
        overrides = data.get('labels', {})
        if not isinstance(overrides, dict) or overrides.keys() - LABELS.keys():
            raise ValueError('지원하지 않는 화면 문구입니다.')
        self.labels = {k: text(overrides, k) or v for k, v in LABELS.items()}
        self.template = Template((site / 'index.html').read_text(encoding='utf-8'))
        self.profile = data['profile']
        self.name = text(self.profile, 'name', True)

    def label(self, key):
        return span('labels', 0, key, self.labels[key])

    def link(self, url, key):
        url = https_url(url, key)
        return f'<a href="{escape(url)}">{self.label(key)}</a>' if url else ''

    def image_src(self, row, root):
        return self.media_file(row.get('image'), root, ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'))

    def media_file(self, raw, root, suffixes):
        """Copy one uploaded file from site/media into the output and return its page-relative URL."""
        if not raw:
            return ''
        if (not isinstance(raw, str) or not raw.startswith('/media/') or '\\' in raw
                or any(ord(c) < 32 for c in raw) or any(p in ('', '.', '..') for p in raw[1:].split('/'))):
            raise ValueError(f'지원하지 않는 이미지 경로: {raw}')
        rel = PurePosixPath(raw[1:])
        if rel.suffix.lower() not in suffixes:
            raise ValueError(f'지원하지 않는 이미지 경로: {raw}')
        src = (self.site / rel).resolve()
        if not src.is_relative_to((self.site / 'media').resolve()) or not src.is_file():
            raise ValueError(f'업로드 파일을 찾을 수 없습니다: {raw}')
        dest = self.out / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        return root + quote(str(rel))

    def image(self, row, root, alt, group, index, key='image', css=''):
        src = self.image_src(row, root)
        if not src:
            return ''
        return (f'<img class="{css}" {mapping(group, index, key)} src="{src}" '
                f'alt="{escape(alt)}" loading="lazy" decoding="async">')

    def page(self, path, root, title, description, body, current='projectNav'):
        home = root + 'index.html'
        active = ' aria-current="location"'
        nav_home = home if root else ''
        links = [('projectNav', nav_home + '#projects'), ('profileNav', nav_home + '#profile'),
                 ('activityNav', nav_home + '#activity')]
        nav = ''.join(f'<a href="{href}"{active if key == current else ""}>{self.label(key)}</a>'
                      for key, href in links)
        brand_key = 'handle' if text(self.profile, 'handle') else 'name'
        loader = (f'<script defer src="{root}owner-init.js" data-api="{escape(self.api)}"></script>' if self.api else '')
        result = self.template.substitute(
            title=escape(title), description=escape(description), root=root, owner_loader=loader,
            theme='detail-page' if root else 'index-page', home=home, nav=nav, skip=self.label('skip'),
            brand=span('profile', 0, brand_key, text(self.profile, brand_key)), content=body,
            name=span('profile', 0, 'name', self.name), footer=self.label('footer'), top=self.label('top'))
        file = self.out / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(result, encoding='utf-8')

    def media(self, row, group, i, root):
        title = text(row, 'title', True)
        slides, thumbs = [], []
        play = '<span class="media-play" aria-hidden="true">▶</span>'

        def add(content, preview, label, key, caption=''):
            slides.append(f'<figure class="media-slide"><div class="media-frame" {mapping(group, i, key)}>'
                          f'{content}</div>{caption}</figure>')
            n = len(slides)
            current = ' aria-current="true"' if n == 1 else ''
            thumbs.append(f'<button type="button" class="media-thumb" data-media="{key.removesuffix(".image")}" '
                          f'aria-label="{n}. {escape(label)}"{current}>{preview}</button>')

        def picture(block, prefix, fallback, caption=''):
            src = self.image_src(block, root)
            if src:
                alt = caption or fallback
                cap = f'<figcaption>{span(group, i, prefix + "caption", caption)}</figcaption>' if caption else ''
                add(f'<img src="{src}" alt="{escape(alt)}" loading="lazy" decoding="async">',
                    f'<img src="{src}" alt="" loading="lazy">', alt, prefix + 'image', cap)

        url = row.get('video')  # Validated before rendering the project.
        video_item = None
        if url:
            ident = youtube_id(urlsplit(url))
            label = title + ' 영상'
            if ident:
                preview = f'<img src="https://i.ytimg.com/vi/{ident}/hqdefault.jpg" alt="" loading="lazy">' + play
                movie = (f'<a class="media-facade" data-youtube="{ident}" data-title="{escape(title)}" '
                         f'aria-label="{escape(label)} 재생" href="https://www.youtube.com/watch?v={ident}" '
                         f'target="_blank" rel="noopener">{preview}</a>')
            else:
                preview = play
                if url.startswith('/media/'):
                    url = self.media_file(url, root, ('.mp4', '.webm'))
                movie = (f'<video controls playsinline preload="metadata" src="{escape(url)}" '
                         f'aria-label="{escape(label)}"></video>')
            video_item = (movie, preview, label, 'video')
        video_at = media_position(row)
        if video_item and video_at == 0:
            add(*video_item)
        picture(row, '', title)
        for j, block in enumerate(row.get('screens', [])):
            if video_item and len(slides) == video_at:
                add(*video_item)
                video_item = None
            picture(block, f'screens.{j}.', f'{title} 스크린샷 {j + 1}', text(block, 'caption'))
        if video_item and video_at:
            add(*video_item)  # A position past the last image puts the video at the end.
        for j, block in enumerate(row.get('sections') or []):
            picture(block, f'sections.{j}.', text(block, 'title'), text(block, 'caption'))
        if not slides:
            return (f'<button type="button" class="media-placeholder" {mapping(group, i, "screens")}>'
                    '이미지·영상 추가</button>')
        arrows = strip = ''
        if len(slides) > 1:
            buttons = ''.join(f'<button type="button" data-{key} '
                              f'aria-label="{escape(self.labels[key])}">{arrow}</button>'
                              for key, arrow in [('prev', '❮'), ('next', '❯')])
            arrows = f'<div class="media-arrows" hidden>{buttons}</div>'
            strip = (f'<div class="media-nav" hidden><p class="media-count" role="status">1 / {len(slides)}</p>'
                     f'<div class="media-thumbs">{"".join(thumbs)}</div></div>')
        return (f'<section class="media-gallery" aria-label="{escape(title)} 미디어"><div class="media-stage">'
                f'{"".join(slides)}{arrows}</div>{strip}</section>')

    def contribution_block(self, i, period, overall, areas, lines):
        if not period and not areas and not lines:
            return (f'<button type="button" class="contribution-placeholder" {mapping("projects", i, "devPeriod")}>'
                    '개발 기간·기여도 입력</button>')

        def meter(key, value, label):
            return (f'<div class="contribution-track" role="meter" aria-valuemin="0" aria-valuemax="100" '
                    f'aria-valuenow="{value}" aria-label="{escape(label)}" {mapping("projects", i, key)}>'
                    f'<div style="width:{value}%"></div></div>')

        cells = []
        if period:
            cells.append(f'<div><h2>{self.label("devPeriodLabel")}</h2><p class="contribution-period">'
                         f'{span("projects", i, "devPeriod", period)}</p></div>')
        # No single overall figure: the contribution reads as one bar per part (개발, 기획).
        if areas:
            rows = []
            for j, (title, value) in enumerate(areas):
                prefix = f'contributionAreas.{j}.'
                name = span('projects', i, prefix + 'title', title)
                number = span('projects', i, prefix + 'value', f'{value}%')
                bar = meter(prefix + 'value', value, title + ' ' + self.labels['contributionLabel'])
                rows.append(f'<li>{name}{bar}{number}</li>')
            heading = f'<h2>{self.label("contributionLabel")}</h2>'
            cells.append(f'<div class="contribution-areas">{heading}<ul>{"".join(rows)}</ul></div>')
        grid = f'<div class="contribution-grid">{"".join(cells)}</div>' if cells else ''
        detail = ''
        if lines:
            items = ''.join(f'<li {mapping("projects", i, "contributionDetail")}>{escape(line)}</li>' for line in lines)
            detail = (f'<div class="contribution-detail"><h2>{self.label("contributionDetailLabel")}</h2>'
                      f'<ul class="contribution-list">{items}</ul></div>')
        return f'<section class="contribution">{grid}{detail}</section>'

    def detail(self, row, group, i, href, contribution=None):
        """Title and media, project contribution, then the lede, links and fact list."""
        project = group == 'projects'
        title = text(row, 'title', True)
        desc_key, meta_key = ('summary', 'category') if project else ('text', 'period')
        desc, meta = text(row, desc_key), text(row, meta_key)
        e = lambda k: span(group, i, k, text(row, k))
        root = '../../'
        actions = [self.action(row.get('url'), 'live' if project else 'related', True),
                   self.action(row.get('source'), 'source')]  # The video plays in the gallery above.
        facts, prose, dated = [], [], False
        if project:
            role = text(row, 'role')
            facts.append(f'<div><dt>{self.label("roleLabel")}</dt><dd>{e("role")}</dd></div>' if role else
                         f'<div class="owner-hint"><dt>{self.label("roleLabel")}</dt>'
                         f'<dd {mapping(group, i, "role")}>역할 입력 필요</dd></div>')
        for j, block in enumerate(row.get('sections') or []):
            prefix = f'sections.{j}.'
            heading, body = text(block, 'title', True), text(block, 'text')
            h = span(group, i, prefix + 'title', heading)
            b = span(group, i, prefix + 'text', body)
            events = timeline(body)
            if events and not block.get('image') and not block.get('caption'):
                # Dated records read as a timeline; the date already says what the heading did.
                dated = True
                facts.extend(f'<div class="event"><dt>{when}</dt><dd {mapping(group, i, prefix + "text")}>'
                             f'{escape(what)}</dd></div>' for when, what in events)
            elif (heading not in AI_SPLIT and not block.get('image') and not block.get('caption')
                  and '\n' not in body and len(body) <= 80):
                facts.append(f'<div><dt>{h}</dt><dd>{b}</dd></div>')
            else:
                cap = ''
                if block.get('caption') and not block.get('image'):
                    cap = f'<p>{span(group, i, prefix + "caption", text(block, "caption"))}</p>'
                css = ' ' + AI_SPLIT[heading] if heading in AI_SPLIT else ''
                prose.append(f'<section class="prose{css}"><h2>{h}</h2><p>{b}</p>{cap}</section>')
        if not dated:
            # Without a dated record the one-line outcome or award is the only proof of results.
            for key in ('outcome', 'award') if project else ('award',):
                if text(row, key):
                    facts.append(f'<div class="result"><dd>{e(key)}</dd></div>')
        subtitle = f'<p class="subtitle">{e(meta_key)}</p>' if meta else ''
        lede = f'<p class="lede">{e(desc_key)}</p>' if desc else ''
        links = ''.join(actions)
        links = f'<div class="actions">{links}</div>' if links else ''
        info = f'<dl class="facts">{"".join(facts)}</dl>' if facts else ''
        detail = (f'<article class="detail"><header><h1>{e("title")}</h1>{subtitle}</header>'
                  + self.media(row, group, i, root)
                  + (self.contribution_block(i, *contribution) if contribution is not None else '')
                  + (f'<div class="overview"><div>{lede}{links}</div>{info}</div>' if lede or links or info else '')
                  + ''.join(prose) + '</article>')
        self.page(href + 'index.html', root, f'{title} | {self.name}', desc or title, detail)

    def action(self, url, key, primary=False):
        """A link button named after where it goes when the host is well known."""
        url = https_url(url, key)
        if not url:
            return ''
        host = (urlsplit(url).hostname or '').lower()
        name = next((n for h, n in KNOWN_HOSTS if host == h or host.endswith('.' + h)), '')
        label = escape(name) if name else self.label(key)
        css = 'action primary' if primary else 'action'
        kind = {'live': 'play', 'source': 'source'}.get(key)
        icon = f'<span class="action-icon" aria-hidden="true">{LINK_KINDS[kind][1]}</span>' if kind else ''
        data = f' data-link="{kind}"' if kind else ''
        return f'<a class="{css}"{data} href="{escape(url)}" target="_blank" rel="noopener">{icon}{label}</a>'

    def work(self, row, i, tier):
        slug = text(row, 'slug')  # Validated in catalog before use in attributes.
        e = lambda k: span('projects', i, k, text(row, k))
        def hint(key, message):
            return f'<span class="owner-hint" {mapping("projects", i, key)}>{message}</span>'

        # Editor-enabled builds also carry the alternate card details. Shelf-scoped
        # styles present the correct variant immediately when a work changes lists.
        large = tier == '1' or self.api
        rich = tier != '0' or self.api
        cover, cover_key = first_image(row)
        pic = self.image({'image': cover}, '', '', 'projects', i, cover_key) if large and cover else ''
        info = []
        if text(row, 'category'):
            info.append(f'<small class="work-category">{e("category")}</small>')
        if large:
            if text(row, 'summary'):
                info.append(f'<p class="work-summary">{e("summary")}</p>')
            elif not any(text(row, k) for k in ('category', 'outcome', 'award')):
                info.append('<div class="work-summary">' + hint('summary', '소개·성과 입력 예정') + '</div>')
            for j, block in enumerate(row.get('sections') or []):
                if text(block, 'title') in ('팀 구성', '개발 인원', '개발 인원과 역할'):
                    if text(block, 'text'):
                        team = span('projects', i, f'sections.{j}.text', text(block, 'text'))
                        info.append(f'<p class="work-team">{team}</p>')
                    break
        if rich and text(row, 'outcome'):
            # Cards stay short: the role is read on the detail page.
            info.append(f'<strong class="outcome">{e("outcome")}</strong>')
        # The green line is for awards only; an AI challenge work names its event before the prize.
        if rich and text(row, 'award'):
            event = f'{e("challenge")} · ' if is_ai_challenge(row) and text(row, 'challenge') else ''
            info.append(f'<strong class="award">{event}{e("award")}</strong>')
        # Featured works open their detail page; the rest open their playable build
        # or source directly, and stay unlinked until the owner adds either one.
        attrs = f'class="tile tone-{i % 4}" data-record="projects" data-index="{i}"'
        # The play link and the GitHub link each get their own round button on every card.
        links = [(kind, https_url(row.get(key), LINK_KINDS[kind][0] + ' 링크'))
                 for kind, key in (('play', 'url'), ('source', 'source'))]
        links = [(kind, href) for kind, href in links if href]
        buttons = card_links = ''
        if tier == '0':
            # Other works have no detail page: the first link also covers the whole block.
            tag = 'div'
            if links:
                attrs += ' data-linked'
                buttons = f'<span class="link-buttons">{link_buttons(row, links, stretch=True)}</span>'
        else:
            # Featured cards open the detail page; their link buttons sit beside the card link,
            # in the footer's right corner, because links cannot nest.
            tag, attrs = 'a', attrs + f' href="projects/{slug}/"'
            if links:
                card_links = f'<span class="link-buttons card-links">{link_buttons(row, links)}</span>'
        # Works made for an AI jam, hackathon or contest carry an "AI Challenge" band in the
        # cover's top-right corner; the event's name sits with the award below.
        badge = ''
        if is_ai_challenge(row):
            badge = f'<span class="ai-tag">{self.label("aiChallengeTag")}</span>'
        flags = ' data-award="1"' if has_project_award(row) else ''
        if is_ai_challenge(row):
            flags += ' data-ai="1"'
        return (f'<li class="work" data-slug="{slug}" data-index="{i}"{flags}><{tag} {attrs}>'
                f'<div class="work-cover">{pic}{badge}<h3>{e("title")}</h3></div>'
                f'<div class="work-info">{"".join(info)}</div>{buttons}</{tag}>{card_links}</li>')

    def catalog(self):
        slugs = set()
        buckets = {tier: [] for tier, *_ in TIERS}
        for i, row in enumerate(self.data.get('projects') or []):
            slug = text(row, 'slug')
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or slug in slugs:
                raise ValueError(f'잘못되었거나 중복된 프로젝트 주소: {slug}')
            slugs.add(slug)
            if row.get('feature', '') not in ('', '1', '2'):
                raise ValueError('feature: 지원하지 않는 값입니다.')
            https_url(row.get('video'), '영상', video=True)
            screens = row.get('screens', [])
            if not isinstance(screens, list):
                raise ValueError('스크린샷 목록을 확인하세요.')
            for screen in screens:
                if not isinstance(screen, dict) or not text(screen, 'image'):
                    raise ValueError('스크린샷 이미지를 선택하세요.')
                text(screen, 'caption')
            contribution = project_contribution(row)  # Validate even projects without a detail page.
            if row.get('feature'):
                self.detail(row, 'projects', i, f'projects/{slug}/', contribution)
            buckets[row.get('feature') or '0'].append((i, row))

        shelves = []
        for tier, key, name in TIERS:
            rows = buckets[tier]
            count = len(rows)
            cards = ''.join(self.work(row, i, tier) for i, row in rows)
            css = '' if count else ' is-empty'
            shelves.append(f'<section class="shelf shelf-{key}{css}" data-tier="{tier}" aria-label="{name}">'
                           f'<ol class="works" data-tier="{tier}">{cards}</ol></section>')
        return '<div id="projects">' + ''.join(shelves) + '</div>'

    def auto_count(self, kind):
        projects = self.data.get('projects') or []
        if kind == 'projects':
            return len(projects)
        if kind == 'awards':
            return sum(has_project_award(row) for row in projects)
        if kind == 'ai':
            return sum(is_ai_challenge(row) for row in projects)
        raise ValueError('auto: 지원하지 않는 값입니다.')

    def highlights(self):
        cells = []
        for i, row in enumerate(self.data.get('highlights') or []):
            kind = text(row, 'auto')
            if kind:
                value = span('highlights', i, 'auto', str(self.auto_count(kind)))
            else:
                value = span('highlights', i, 'value', text(row, 'value', True))
            label = span('highlights', i, 'label', text(row, 'label', True))
            content = f'<b>{value}</b><span>{label}</span>'
            if kind:
                cells.append(f'<li><button type="button" class="stat" data-filter="{kind}" aria-pressed="false" '
                             f'aria-controls="projects">{content}</button></li>')
            else:
                cells.append(f'<li class="stat">{content}</li>')
        if not cells:
            return ''
        return (f'<section class="highlights" aria-labelledby="highlights-title">'
                f'<h2 id="highlights-title" class="sr-only">{self.label("highlights")}</h2><ul>{"".join(cells)}</ul>'
                '<p id="works-filter-status" class="sr-only" aria-live="polite" aria-atomic="true"></p></section>')

    def profile_credentials(self):
        """Education and completed programs, listed above skills as period + name + status."""
        rows = []
        for i, row in enumerate(self.data.get('credentials') or []):
            period = text(row, 'period')
            note = text(row, 'text')
            rows.append(f'<div class="credential"><dt>{span("credentials", i, "period", period) if period else ""}</dt>'
                        f'<dd><b>{span("credentials", i, "title", text(row, "title", True))}</b>'
                        + (f' <small>{span("credentials", i, "text", note)}</small>' if note else '') + '</dd></div>')
        return f'<dl class="credentials" data-manage="credentials">{"".join(rows)}</dl>' if rows else ''

    def profile_skills(self):
        """Skills grouped by field (엔진, AI, 언어…); older two-level lists still render as two lines."""
        rows = []
        for i, group in enumerate(self.data.get('skillGroups') or []):
            title = text(group, 'title', True)
            items = [s.strip() for s in text(group, 'items', True).split(',') if s.strip()]
            pills = ''.join(f'<li {mapping("skillGroups", i, "items")}>{escape(s)}</li>' for s in items)
            rows.append(f'<div class="skill-group"><dt>{span("skillGroups", i, "title", title)}</dt>'
                        f'<dd><ul class="skill-line">{pills}</ul></dd></div>')
        if rows:
            return f'<dl id="skills" class="skills" data-manage="skillLists">{"".join(rows)}</dl>'
        lines = []
        for group, css in [('skills', 'strong'), ('otherSkills', 'familiar')]:
            items = self.data.get(group) or []
            if items:
                pills = ''.join(f'<li>{span(group, i, "value", s)}</li>' for i, s in enumerate(items))
                lines.append(f'<ul class="skill-line {css}" aria-label="{escape(self.labels["primary" if css == "strong" else "secondary"])}">{pills}</ul>')
        return f'<div id="skills" class="skills" data-manage="legacySkillLists">{"".join(lines)}</div>' if lines else ''

    def activity_row(self, row, i):
        """One activity: month, title with its detail, and the result marked when it was awarded."""
        title = span('experience', i, 'title', text(row, 'title', True))
        award = text(row, 'award')
        # The first word of each record is its kind (게임잼, 팀 활동…); the year list already says enough.
        rest = [seg for seg in text(row, 'text').split(' · ') if seg and seg not in ACTIVITY_KINDS and seg != award]
        detail = (f'<small {mapping("experience", i, "text")}>{escape(" · ".join(rest))}</small>' if rest else '')
        result = f'<em class="result">{span("experience", i, "award", award)}</em>' if award else ''
        month = period_parts(text(row, 'period'))[1]
        body = (f'<span class="month">{span("experience", i, "period", month)}</span>'
                f'<span class="what"><b>{title}</b>{detail}</span>{result}')
        url = https_url(row.get('url'), '관련 링크')
        inner = (f'<a class="entry-row" href="{escape(url)}" target="_blank" rel="noopener">{body}</a>' if url
                 else f'<div class="entry-row">{body}</div>')
        css = 'entry awarded' if award else 'entry'
        return f'<article class="{css}" id="activity-{i + 1}">{inner}</article>'

    def profile_activity(self, root):
        rows = [(i, row) for i, row in enumerate(self.data.get('experience') or [])]
        chunks = []
        if rows:
            year = None
            def render(part):
                nonlocal year
                out = []
                for i, row in part:
                    y = period_parts(text(row, 'period'))[0]
                    if y and y != year:
                        out.append(f'<h3 class="year">{escape(y)}</h3>')
                    year = y or year
                    out.append(self.activity_row(row, i))
                return ''.join(out)
            visible = render(rows)  # The profile sits below the works, so the whole history stays open.
            chunks.append(f'<section id="experience" aria-label="{escape(self.labels["experience"])}">{visible}</section>')
        photos = []
        for i, row in enumerate(self.data.get('photos') or []):
            cap = text(row, 'caption', True)
            pic = self.image(row, root, cap, 'photos', i)
            if not pic:
                raise ValueError(f'사진을 선택하세요: {cap}')
            photos.append(f'<figure>{pic}<figcaption>{span("photos", i, "caption", cap)}</figcaption></figure>')
        if photos:
            chunks.append(f'<section id="photos" aria-label="{escape(self.labels["photos"])}">{"".join(photos)}</section>')
        content = ''.join(chunks) or f'<p>{self.label("empty")}</p>'
        return f'<section id="activity" aria-label="{escape(self.labels["activityNav"])}">{content}</section>'

    def profile_link_row(self):
        links = [self.link(self.profile.get('github'), 'github')]
        boj = https_url(self.profile.get('baekjoon'), '백준 프로필')
        if boj:
            # Only the tier is shown; it is entered by hand because solved.ac blocks automated reads.
            tier = text(self.profile, 'baekjoonTier')
            rank = f' <b class="tier">{span("profile", 0, "baekjoonTier", tier)}</b>' if tier else ''
            links.append(f'<a href="{escape(boj)}" target="_blank" rel="noopener">{self.label("baekjoon")}{rank}</a>')
        for i, row in enumerate(self.data.get('profileLinks') or []):
            # Side work that is not a game (e.g. a personal web tool) sits with the profile links.
            url = https_url(row.get('url'), '프로필 링크')
            links.append(f'<a href="{escape(url)}" target="_blank" rel="noopener">'
                         f'{span("profileLinks", i, "title", text(row, "title", True))}</a>')
        links = ''.join(f'<li>{a}</li>' for a in links if a)
        return f'<ul class="profile-links">{links}</ul>' if links else ''

    def profile_identity(self):
        role = text(self.profile, 'role') or 'AI Game Maker'
        pic = self.image(self.profile, '', '', 'profile', 0, css='portrait')
        link_row = self.profile_link_row()
        return (f'<div class="identity"><a class="identity-link" href="#profile">{pic}'
                f'<div><h2>{span("profile", 0, "name", self.name)}'
                '<span class="identity-arrow" aria-hidden="true">↓</span></h2>'
                f'<p class="role">{span("profile", 0, "role", role)}</p></div></a>{link_row}</div>')

    def profile_content(self):
        # The section restates who this is: a large photo and the same links as the hero.
        pic = self.image(self.profile, '', self.name, 'profile', 0, css='portrait-large')
        sidebar = pic + self.profile_link_row() + self.profile_credentials() + self.profile_skills()
        if sidebar:
            sidebar = f'<div class="profile-sidebar">{sidebar}</div>'
        return (f'<section id="profile" aria-labelledby="profile-title">'
                f'<h2 id="profile-title" class="section-title">{self.label("profileTitle")}</h2>'
                f'<div class="profile-detail">{sidebar}{self.profile_activity("")}</div>'
                '<a class="back-projects" href="#projects">↑ 작품으로</a></section>')

    def render(self):
        intro = text(self.profile, 'intro') or self.name
        hero = (f'<header class="intro"><h1>{span("profile", 0, "intro", intro)}</h1>'
                f'{self.profile_identity()}</header>')
        self.page('index.html', '', f'{self.name} | 포트폴리오', intro,
                  hero + self.highlights() + self.catalog() + self.profile_content())


def build(data, out, site=SITE, editor_api=''):
    """Render into a new/empty output directory; only copy referenced media."""
    out.mkdir(parents=True, exist_ok=True)
    assets = ['portfolio.css', 'portfolio.js']
    if editor_api:
        if editor_api != '/__editor' and not re.fullmatch(r'https://[a-zA-Z0-9.-]+(?::[0-9]+)?', editor_api):
            raise ValueError('편집 API는 https 출처 주소여야 합니다.')
        assets.extend(('owner-init.js', 'owner.mjs', 'owner-fields.mjs', 'owner.css'))
    for asset in assets:
        shutil.copyfile(site / asset, out / asset)
    (out / '.nojekyll').touch()
    Portfolio(data, out, site, editor_api).render()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--content', type=Path, default=BASE / 'portfolio.json')
    args = parser.parse_args()
    data = json.loads(args.content.read_text(encoding='utf-8-sig'))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=OUT.parent) as temp:
        stage = Path(temp) / 'portfolio'
        build(data, stage, editor_api=os.environ.get('PORTFOLIO_EDITOR_API', '').strip().rstrip('/'))
        if OUT.exists():
            shutil.rmtree(OUT)
        stage.rename(OUT)
    print(f'정적 페이지 생성: {OUT}')


if __name__ == '__main__':
    main()
