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
from urllib.parse import quote, urlsplit

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
    'highlights': '한눈에', 'award': '수상',
    'roleLabel': '역할',
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


def https_url(value, label, video=False):
    if value in (None, ''):
        return ''
    try:
        if not isinstance(value, str) or not re.fullmatch(r'https://[^\s\\\x00-\x1f\x7f]+', value):
            raise ValueError
        parsed = urlsplit(value)
        if not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise ValueError
        _ = parsed.port  # Reject malformed ports as well as malformed hosts.
    except ValueError as exc:
        raise ValueError(f'{label}: https:// 로 시작하는 전체 주소가 필요합니다.') from exc
    if video and not parsed.path.lower().endswith(('.mp4', '.webm')):
        raise ValueError('영상: https MP4 또는 WebM 주소가 필요합니다.')
    return value


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

    def image(self, row, root, alt, group, index, key='image', css=''):
        raw = row.get('image')
        if not raw:
            return ''
        if (not isinstance(raw, str) or not raw.startswith('/media/') or '\\' in raw
                or any(ord(c) < 32 for c in raw) or any(p in ('', '.', '..') for p in raw[1:].split('/'))):
            raise ValueError(f'지원하지 않는 이미지 경로: {raw}')
        rel = PurePosixPath(raw[1:])
        if rel.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'):
            raise ValueError(f'지원하지 않는 이미지 경로: {raw}')
        src = (self.site / rel).resolve()
        if not src.is_relative_to((self.site / 'media').resolve()) or not src.is_file():
            raise ValueError(f'업로드 파일을 찾을 수 없습니다: {raw}')
        dest = self.out / rel
        if not dest.exists():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
        return (f'<img class="{css}" {mapping(group, index, key)} src="{root}{quote(str(rel))}" '
                f'alt="{escape(alt)}" loading="lazy" decoding="async">')

    def page(self, path, root, title, description, body, current='projectNav'):
        home = root + 'index.html'
        active = ' aria-current="location"'
        links = [('projectNav', home + '#projects')]
        links += [('profileNav', home + '#profile'), ('activityNav', home + '#activity')]
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
        slides = []
        main = self.image(row, root, title, group, i)
        if main:
            slides.append(main)
        for j, block in enumerate(row.get('sections') or []):
            prefix = f'sections.{j}.'
            caption = text(block, 'caption')
            pic = self.image(block, root, caption or text(block, 'title'), group, i, prefix + 'image')
            if pic:
                cap = f'<figcaption>{span(group, i, prefix + "caption", caption)}</figcaption>' if caption else ''
                slides.append(pic + cap)
        url = https_url(row.get('video'), '영상', video=True)
        if not slides:
            if not url:
                return ''  # No uploaded media: the page goes straight from the title to the text.
            slides.append('<div class="title-cover" aria-hidden="true"></div>')
        frames = ''.join(f'<figure class="slide">{s}</figure>' for s in slides)
        movie = f'<video muted playsinline preload="none" hidden data-src="{escape(url)}"></video>' if url else ''
        controls = ''
        if url or len(slides) > 1:
            controls = (f'<div class="deck-controls" hidden><button type="button" data-prev>{self.label("prev")}</button>'
                        f'<button type="button" data-pause><span data-stop>{self.label("pause")}</span>'
                        f'<span data-start hidden>{self.label("resume")}</span></button>'
                        f'<button type="button" data-next>{self.label("next")}</button></div>')
        return f'<div class="deck"><div class="stage">{frames}{movie}</div>{controls}</div>'

    def detail(self, row, group, i, href):
        """Title, media when uploaded, then a lede with its links beside a compact fact list."""
        project = group == 'projects'
        title = text(row, 'title', True)
        desc_key, meta_key = ('summary', 'category') if project else ('text', 'period')
        desc, meta = text(row, desc_key), text(row, meta_key)
        e = lambda k: span(group, i, k, text(row, k))
        root = '../../'
        actions = [self.action(row.get('url'), 'live' if project else 'related', True),
                   self.action(row.get('source'), 'source'), self.action(row.get('video'), 'videoLink')]
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
        return f'<a class="{css}" href="{escape(url)}" target="_blank" rel="noopener">{label}</a>'

    def work(self, row, i, tier):
        slug = text(row, 'slug')  # Validated in catalog before use in attributes.
        e = lambda k: span('projects', i, k, text(row, k))
        def hint(key, message):
            return f'<span class="owner-hint" {mapping("projects", i, key)}>{message}</span>'

        # Editor-enabled builds also carry the alternate card details. Shelf-scoped
        # styles present the correct variant immediately when a work changes lists.
        large = tier == '1' or self.api
        rich = tier != '0' or self.api
        pic = self.image(row, '', '', 'projects', i) if large else ''
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
        if rich:
            # Cards stay short: the role is read on the detail page.
            for k in ('outcome', 'award'):
                if text(row, k):
                    info.append(f'<strong class="{k}">{e(k)}</strong>')
        # Featured works open their detail page; the rest open their playable build
        # or source directly, and stay unlinked until the owner adds either one.
        attrs = f'class="tile tone-{i % 4}" data-record="projects" data-index="{i}"'
        buttons = ''
        if tier == '0':
            # Other works have no detail page. The play link and the GitHub link each get their own
            # button; the first one present also covers the whole block so the row stays clickable.
            links = [(kind, https_url(row.get(key), LINK_KINDS[kind][0] + ' 링크'))
                     for kind, key in (('play', 'url'), ('source', 'source'))]
            links = [(kind, href) for kind, href in links if href]
            for n, (kind, href) in enumerate(links):
                name = LINK_KINDS[kind][0]
                css = 'link-btn stretch' if n == 0 else 'link-btn'
                buttons += (f'<a class="{css}" data-link="{kind}" href="{escape(href)}" target="_blank" rel="noopener" '
                            f'title="{name}"><span class="link-icon" aria-hidden="true">{LINK_KINDS[kind][1]}</span>'
                            f'<span class="sr-only">{escape(text(row, "title"))} {name}</span></a>')
            tag = 'div'
            if links:
                attrs += ' data-linked'
                buttons = f'<span class="link-buttons">{buttons}</span>'
        else:
            tag, attrs = 'a', attrs + f' href="projects/{slug}/"'
        return (f'<li class="work" data-slug="{slug}" data-index="{i}"><{tag} {attrs}>'
                f'<div class="work-cover">{pic}<h3>{e("title")}</h3></div>'
                f'<div class="work-info">{"".join(info)}</div>{buttons}</{tag}></li>')

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
            if row.get('feature'):
                self.detail(row, 'projects', i, f'projects/{slug}/')
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
        # Counts follow the records, so adding a project or an award updates the summary.
        experience = self.data.get('experience') or []
        if kind == 'projects':
            return len(self.data.get('projects') or [])
        if kind == 'awards':
            return sum(1 for row in experience if text(row, 'award'))
        if kind == 'ai':
            # An AI-themed jam, hackathon or contest; other AI activities are not competitions.
            events = (text(row, 'title') + '\n' + text(row, 'text') for row in experience)
            return sum(1 for evidence in events if AI.search(evidence) and COMPETITION.search(evidence))
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
            cells.append(f'<li><b>{value}</b><span>{label}</span></li>')
        if not cells:
            return ''
        return (f'<section class="highlights" aria-labelledby="highlights-title">'
                f'<h2 id="highlights-title">{self.label("highlights")}</h2><ul>{"".join(cells)}</ul></section>')

    def profile_credentials(self):
        """Education and completed programs, listed under the role as period + name + status."""
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
            visible = render(rows[:5])
            if len(rows) > 5:
                visible += ('<details class="earlier-activities"><summary>'
                            f'<span>{self.label("allActivities")} '
                            f'<small class="activity-count">+{len(rows) - 5}</small></span></summary>'
                            '<div class="disclosure-body">' + render(rows[5:]) + '</div></details>')
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

    def profile_content(self):
        root = ''
        role = text(self.profile, 'role') or 'AI Game Maker'
        pic = self.image(self.profile, root, self.name, 'profile', 0, css='portrait')
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
        identity = (f'<aside class="identity">{pic}<h2>{span("profile", 0, "name", self.name)}</h2>'
                    f'<p class="role">{span("profile", 0, "role", role)}</p>'
                    + self.profile_credentials() + self.profile_skills() + (f'<ul class="profile-links">{links}</ul>' if links else '') + '</aside>')
        return f'<article class="profile-detail">{identity}{self.profile_activity(root)}</article>'

    def render(self):
        intro = text(self.profile, 'intro') or self.name
        hero = ('<details class="profile-disclosure" id="profile"><summary class="intro"><h1><span class="intro-link">'
                f'{span("profile", 0, "intro", intro)}<small>'
                f'<span class="when-closed">{self.label("viewProfile")}</span>'
                f'<span class="when-open">{self.label("hideProfile")}</span></small></span></h1></summary>'
                '<div class="disclosure-body">' + self.profile_content() + '</div></details>')
        self.page('index.html', '', f'{self.name} | 포트폴리오', intro, hero + self.highlights() + self.catalog())


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
