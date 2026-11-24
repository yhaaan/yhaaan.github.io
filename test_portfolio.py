import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
from tempfile import TemporaryDirectory

from build_portfolio import BASE, SITE, build


class Elements(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def attrs(self, tag):
        return [attrs for t, attrs in self.tags if t == tag]


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / 'public'
        self.data = {'profile': {'name': '요한'}, 'projects': [
            {'title': '새 프로젝트', 'slug': 'new-project', 'feature': '2', 'sections': [{'title': '기록', 'text': '상세 내용'}]}
        ]}

    def read(self, path='index.html'):
        return (self.out / path).read_text(encoding='utf-8')

    def test_actual_content_builds(self):
        data = json.loads((BASE / 'portfolio.json').read_text(encoding='utf-8'))
        build(data, self.out)
        for p in data.get('projects') or []:
            self.assertEqual((self.out / 'projects' / p['slug'] / 'index.html').exists(), bool(p.get('feature')))
        self.assertFalse((self.out / 'portfolio.json').exists())
        self.assertFalse((self.out / '.pages.yml').exists())
        self.assertFalse((self.out / 'owner.mjs').exists())
        self.assertEqual((self.out / 'portfolio.js').read_bytes(), (SITE / 'portfolio.js').read_bytes())

    def test_detail_and_text_fields(self):
        self.data.update(skills=['HTML'], experience=[{'title': '경력'}],
                         archive=[{'title': '예전 소개', 'text': '<script>example</script>'}])
        build(self.data, self.out)
        html = self.read()
        profile = html.split('id="profile"', 1)[1].split('</main>', 1)[0]
        self.assertIn('projects/new-project/', html)
        for text in ('id="skills"', 'id="experience"', '경력', '>HTML<'):
            self.assertIn(text, profile)
        for file in self.out.rglob('*.html'):
            page = file.read_text(encoding='utf-8')
            for legacy in ('id="archive"', '#archive"', '예전 소개', 'example</script>', 'example&lt;/script&gt;'):
                self.assertNotIn(legacy, page, str(file))
        self.assertEqual([s.get('src') for s in Elements(html).attrs('script')], ['portfolio.js'])
        self.assertNotIn('id="photos"', profile)
        detail = self.read('projects/new-project/index.html')
        self.assertIn('상세 내용', detail)
        self.assertIn('../../index.html#projects', detail)

    def test_home_intro_and_profile_routes(self):
        self.data['profile']['intro'] = '<게임>을 만듭니다.'
        build(self.data, self.out)
        home = self.read()
        hero = home.split('<header class="intro">', 1)[1].split('</header>', 1)[0]
        heading = hero.split('<h1>', 1)[1].split('</h1>', 1)[0]
        self.assertIn('data-edit-group="profile" data-edit-index="0" data-edit-field="intro">&lt;게임&gt;을 만듭니다.', heading)
        identity = hero.split('href="#profile">', 1)[1].split('</a>', 1)[0]
        self.assertIn('data-edit-field="name">요한', identity)
        self.assertIn('data-edit-field="role">AI Game Maker', identity)
        self.assertFalse(Elements(identity).attrs('img'))
        profile = home.split('id="profile"', 1)[1].split('</main>', 1)[0]
        self.assertIn('id="activity"', profile)
        self.assertNotIn('data-edit-group="profile"', profile)
        self.assertIn('href="#projects">↑ 작품으로</a>', profile)
        self.assertNotIn('data-tab=', home)
        self.assertFalse((self.out / 'profile').exists())
        for page, base in [(home, ''), (self.read('projects/new-project/index.html'), '../../index.html')]:
            nav = page.split('<nav ', 1)[1].split('</nav>', 1)[0]
            self.assertEqual([a['href'] for a in Elements(nav).attrs('a')],
                             [base + target for target in ('#projects', '#profile', '#activity')])

    def test_profile_is_open_after_projects(self):
        self.data['experience'] = [{'title': f'활동 {i}'} for i in range(6)]
        build(self.data, self.out)
        home = self.read()
        els = Elements(home)
        self.assertFalse(any('profile-disclosure' in d.get('class', '').split() for d in els.attrs('details')))
        identity, = [a for a in els.attrs('a') if 'identity-link' in a.get('class', '').split()]
        self.assertEqual(identity['href'], '#profile')
        ids = [a['id'] for _, a in els.tags if 'id' in a]
        self.assertLess(ids.index('projects'), ids.index('profile'))
        self.assertNotIn('earlier-activities', home)  # Every activity is listed openly.
        self.assertIn('id="activity-6"', home.split('id="profile"', 1)[1])

    def test_notion_fields_without_primary_skills(self):
        self.data['otherSkills'] = ['Python']
        self.data['profile']['github'] = 'https://github.com/example'
        self.data['experience'] = [{'title': '게임잼', 'url': 'https://example.org/jam'}]
        build(self.data, self.out)
        home = self.read()
        hero = home.split('<header class="intro">', 1)[1].split('</header>', 1)[0]
        identity, links = hero.split('</a>', 1)
        self.assertNotIn('https://github.com/example', identity)
        self.assertIn('href="https://github.com/example"', links)
        profile = home.split('id="profile"', 1)[1].split('</main>', 1)[0]
        self.assertIn('href="https://github.com/example"', profile)  # The section repeats the links.
        self.assertNotIn('TOOLKIT', profile)
        self.assertIn('Python', profile)
        self.assertIn('href="https://example.org/jam"', profile)
        self.assertNotIn('많이 해봤어요', profile)

    def test_removed_project_and_empty_lists(self):
        self.data['projects'] = []
        build(self.data, self.out)
        self.assertFalse((self.out / 'projects').exists())
        home = self.read()
        self.assertIn('href="#projects"', home.split('</nav>', 1)[0])
        self.assertNotIn('data-manage="projects"', home)
        self.assertEqual(home.count(' is-empty"'), 3)

    def test_categories_follow_evidence_and_share_details(self):
        self.data['projects'][0].update(source='https://example.org/game', sections=[{'title': '공모전', 'text': '10위'}])
        self.data['experience'] = [
            {'title': '공모전', 'text': '10위', 'url': 'https://example.org/game'},
            {'title': 'AI Game Jam', 'text': 'Special Prize', 'url': 'https://example.org/jam'},
            {'title': 'Trail Game Jam', 'text': '참가'},
        ]
        build(self.data, self.out)
        html = self.read()
        self.assertNotIn('data-panel=', html)
        links = [a['href'] for a in Elements(html).attrs('a') if 'data-record' in a]
        self.assertEqual(links, ['projects/new-project/'])
        self.assertNotIn('entry-tags', html)  # Text tags gave way to the marked result.
        self.assertFalse((self.out / 'activities').exists())
        activity = html.split('id="activity"', 1)[1].split('</main>', 1)[0]
        self.assertIn('id="activity-2"', activity)
        self.assertIn('href="https://example.org/jam"', activity)
        for row in self.data['experience']:
            self.assertIn(row['title'], activity)

    def test_baekjoon_tier_link(self):
        self.data['profile'].update(baekjoon='https://solved.ac/someone', baekjoonTier='Gold IV')
        build(self.data, self.out)
        html = self.read()
        self.assertIn('href="https://solved.ac/someone" target="_blank" rel="noopener"', html)
        self.assertIn('data-edit-field="baekjoonTier">Gold IV</span>', html)
        self.data['profile']['baekjoon'] = 'http://solved.ac/someone'
        with self.assertRaises(ValueError):
            build(self.data, self.out.parent / 'again')

    def test_profile_links_follow_github(self):
        self.data['profile']['github'] = 'https://github.com/someone'
        self.data['profileLinks'] = [{'title': '노트', 'url': 'https://example.org/notes/'}]
        build(self.data, self.out)
        links = self.read().split('class="profile-links">', 1)[1].split('</ul>', 1)[0]
        self.assertEqual([a['href'] for a in Elements(links).attrs('a')],
                         ['https://github.com/someone', 'https://example.org/notes/'])
        self.assertIn('data-edit-group="profileLinks" data-edit-index="0" data-edit-field="title">노트', links)

    def test_ai_challenge_band_on_cards(self):
        self.data['projects'] = [{'title': 'AI 작품', 'slug': 'a', 'feature': '1', 'aiChallenge': '1', 'challenge': '잼'},
                                 {'title': '그 밖', 'slug': 'b', 'aiChallenge': '1'},
                                 {'title': '일반', 'slug': 'c'}]
        build(self.data, self.out)
        html = self.read()
        self.assertNotIn('ai-badge', html)
        self.assertEqual(html.count('class="ai-tag"'), 2)
        self.assertEqual(html.count('data-edit-field="aiChallengeTag">AI Challenge</span>'), 2)
        self.assertNotIn('class="award"', html)  # Entering an event without a prize is not an award.
        self.data['projects'][0]['award'] = '상'
        build(self.data, self.out.parent / 'awarded')
        first = (self.out.parent / 'awarded' / 'index.html').read_text(encoding='utf-8').split('data-slug="a"', 1)[1]
        self.assertIn('data-edit-field="challenge">잼</span> · <span data-edit-group="projects" '
                      'data-edit-index="0" data-edit-field="award">상</span></strong>', first.split('</li>', 1)[0])

    def test_profile_section_title_photo_and_links(self):
        self.data['profile']['github'] = 'https://github.com/someone'
        build(self.data, self.out)
        section = self.read().split('id="profile"', 1)[1]
        self.assertIn('data-edit-field="profileTitle">Profile</span>', section)
        self.assertIn('class="profile-links"', section)
        self.assertIn('href="https://github.com/someone"', section)

    def test_skill_groups_replace_legacy_lists(self):
        self.data.update(skills=['Old'], skillGroups=[{'title': 'AI', 'items': 'Claude Code, Codex ,Gemini'},
                                                      {'title': '엔진', 'items': 'Unity'}])
        build(self.data, self.out)
        html = self.read()
        self.assertNotIn('Old', html)
        self.assertIn('data-manage="skillLists"', html)
        ai = html.split('data-edit-field="title">AI</span>', 1)[1].split('</dl>', 1)[0].split('</div>', 1)[0]
        self.assertEqual([a.get('data-edit-field') for a in Elements(ai).attrs('li')], ['items'] * 3)
        for item in ('>Claude Code<', '>Codex<', '>Gemini<', '>Unity<'):
            self.assertIn(item, html)

    def test_credentials_sit_above_skills(self):
        self.data.update(credentials=[{'period': '2025', 'title': '게임랩', 'text': '수료'}, {'title': '대학교'}],
                         skillGroups=[{'title': 'AI', 'items': 'Codex'}])
        build(self.data, self.out)
        html = self.read()
        self.assertLess(html.index('data-manage="credentials"'), html.index('data-manage="skillLists"'))
        self.assertIn('data-edit-group="credentials" data-edit-index="0" data-edit-field="text">수료', html)
        self.assertNotIn('data-edit-index="1" data-edit-field="period"', html)

    def test_activity_years_kinds_and_results(self):
        self.data['experience'] = [
            {'period': '2026.11', 'title': '잼', 'text': '게임잼 · Prize', 'award': 'Prize', 'url': 'https://example.org/j'},
            {'period': '2026.06', 'title': '전시', 'text': '팀 활동 · 부스 선정'},
            {'period': '2020~', 'title': '학교', 'text': '학력'},
        ]
        build(self.data, self.out)
        html = self.read()
        self.assertEqual(html.count('class="year"'), 2)
        self.assertIn('<h3 class="year">2026</h3>', html)
        self.assertIn('<h3 class="year">2020</h3>', html)
        first = html.split('id="activity-1"', 1)[1].split('</article>', 1)[0]
        self.assertIn('class="entry-row" href="https://example.org/j" target="_blank"', first)
        self.assertIn('class="result"', first)
        self.assertIn('>11월<', first)
        self.assertNotIn('게임잼', first)
        second = html.split('id="activity-2"', 1)[1].split('</article>', 1)[0]
        self.assertIn('>부스 선정</small>', second)
        self.assertIn('<div class="entry-row">', second)
        self.assertIn('>~<', html.split('id="activity-3"', 1)[1])

    def test_award_highlights_and_ai_sections(self):
        self.data['projects'][0].update(feature='2', award='게임잼 특별상', sections=[
            {'title': 'AI에게 맡긴 것', 'text': '코드 초안'}, {'title': '내가 한 것', 'text': '문제 정의'}])
        self.data['highlights'] = [{'value': '3', 'label': 'Steam 출시'}]
        build(self.data, self.out)
        home = self.read()
        self.assertEqual(home.count('class="work"'), 1)
        self.assertIn('class="award"><span data-edit-group="projects" data-edit-index="0" data-edit-field="award">', home)
        self.assertIn('data-edit-group="highlights" data-edit-index="0" data-edit-field="value">3', home)
        self.assertNotIn('data-filter=', home)  # A manual value is not a filter button.
        self.assertNotIn('ai-workflow', home)
        detail = self.read('projects/new-project/index.html')
        self.assertIn('class="prose by-ai"', detail)
        self.assertIn('class="prose by-me"', detail)
        self.assertFalse((self.out / 'ai-workflow').exists())

    def test_auto_highlights_follow_records(self):
        self.data['experience'] = [{'title': 'AI 게임잼', 'award': '특별상'}]
        self.data['projects'][0]['award'] = '장려상'
        self.data['projects'].extend([
            {'title': '대표작', 'slug': 'featured', 'feature': '1', 'aiChallenge': '1'},
            {'title': '수상작', 'slug': 'both', 'award': '특별상', 'aiChallenge': '1'},
            {'title': '출품작', 'slug': 'entry', 'aiChallenge': '1'},
            {'title': 'AI 게임잼 수상 기록', 'slug': 'unmarked', 'award': ' ', 'aiChallenge': ''}])
        expected = [('projects', 'All work', 5), ('awards', 'Prize winners', 2), ('ai', 'Challenge entries', 3)]
        self.data['highlights'] = [{'auto': kind, 'label': label} for kind, label, _ in expected]
        build(self.data, self.out)
        home = self.read()
        els = Elements(home)
        heading, = [h for h in els.attrs('h2') if h.get('id') == 'highlights-title']
        self.assertIn('sr-only', heading['class'].split())
        buttons = [b for b in els.attrs('button') if 'data-filter' in b]
        self.assertEqual([b['data-filter'] for b in buttons], [kind for kind, _, _ in expected])
        for i, (kind, label, count) in enumerate(expected):
            button = buttons[i]
            self.assertIn('stat', button['class'].split())
            self.assertEqual((button['type'], button['aria-pressed'], button['aria-controls']), ('button', 'false', 'projects'))
            cell = home.split(f'data-filter="{kind}"', 1)[1].split('</button>', 1)[0]
            target = f'<span data-edit-group="highlights" data-edit-index="{i}"'
            self.assertIn(f'<b>{target} data-edit-field="auto">{count}</span></b>', cell)
            self.assertIn(f'<span>{target} data-edit-field="label">{label}</span></span>', cell)
        self.assertEqual({a['data-slug']: (a.get('data-award'), a.get('data-ai'))
                          for a in els.attrs('li') if a.get('class') == 'work'}, {
            'new-project': ('1', None), 'featured': (None, '1'), 'both': ('1', '1'),
            'entry': (None, '1'), 'unmarked': (None, None)})
        self.data['highlights'] = [{'auto': 'stars', 'label': 'x'}]
        with self.assertRaisesRegex(ValueError, 'auto'):
            build(self.data, self.out / 'bad')

    def test_edit_targets_and_label_override(self):
        self.data.update(labels={'viewProfile': '옛 열기', 'hideProfile': '옛 닫기', 'footer': '<작업 기록>'}, skills=['Unity'])
        self.data['profile']['role'] = '<클라이언트 개발자>'
        build(self.data, self.out, editor_api='/__editor')
        self.assertIn('&lt;작업 기록&gt;', self.read())
        for unused in ('옛 열기', '옛 닫기'):
            self.assertNotIn(unused, self.read())
        self.assertIn('&lt;클라이언트 개발자&gt;', self.read())
        for page, expected in [('index.html', [('profile','intro'), ('labels','footer'), ('projects','title'),
                                               ('profile','name'), ('profile','role'), ('skills','value')]),
                               ('projects/new-project/index.html', [('projects','sections.0.text'), ('labels','projectNav')])]:
            attrs = Elements(self.read(page)).attrs('span')
            targets = {(a.get('data-edit-group'), a.get('data-edit-field')) for a in attrs if a.get('data-edit-index') == '0'}
            self.assertTrue(set(expected) <= targets)
        self.assertTrue((self.out / 'owner-init.js').exists())
        for invalid in ([], {'unrecognized': 'x'}):
            self.data['labels'] = invalid
            with self.assertRaises(ValueError):
                build(self.data, self.out)

    def test_detail_timeline_links_and_no_placeholder_cover(self):
        self.data['projects'][0].update(
            url='https://store.steampowered.com/app/1/', source='https://github.com/a/b', outcome='리뷰 10개',
            sections=[{'title': '팀 구성', 'text': '2인 개발'},
                      {'title': '출시', 'text': '2024년 5월 전시\n2026년 3월 Steam 출시. 2026년 6월 콘솔 출시'}])
        build(self.data, self.out)
        detail = self.read('projects/new-project/index.html')
        self.assertNotIn('title-cover', detail)
        self.assertNotIn('class="media-gallery"', detail)
        self.assertIn('data-edit-group="projects" data-edit-index="0" data-edit-field="screens">이미지·영상 추가</button>', detail)
        self.assertEqual([a['class'] for a in Elements(detail).attrs('a') if 'action' in a.get('class', '')],
                         ['action primary', 'action'])
        self.assertIn('Steam에서 보기', detail)
        self.assertIn('>GitHub<', detail)
        for when, what in [('2024.05', '전시'), ('2026.03', 'Steam 출시'), ('2026.06', '콘솔 출시')]:
            self.assertIn(f'<dt>{when}</dt><dd data-edit-group="projects" data-edit-index="0" '
                          f'data-edit-field="sections.1.text">{what}</dd>', detail)
        self.assertIn('2인 개발', detail)
        self.assertNotIn('리뷰 10개', detail)  # A dated record already carries the results.
        self.assertIn('class="owner-hint"', detail)

    def test_project_contribution(self):
        period = '2025.03 – 2025.07 (5개월)'
        self.data['projects'][0].update(video='https://example.org/v.webm', devPeriod=period, contribution='40',
                                        contributionAreas=[{'title': '기획', 'value': '100'}, {'title': 'UI', 'value': '35'}],
                                        contributionDetail=' 전투 설계\n  \n<UI> 개선 ')
        self.data['labels'] = {'contributionLabel': '내 기여도'}
        build(self.data, self.out)
        html = self.read('projects/new-project/index.html')
        before, rest = html.split('<section class="contribution">', 1)
        block, after = rest.split('</section>', 1)
        self.assertIn('class="media-gallery"', before)
        self.assertIn('class="overview"', after)
        self.assertNotIn('contribution-placeholder', html)
        self.assertNotIn('data-edit-field="contribution"', block)  # Only the per-part bars are shown.
        for field, value in [('devPeriod', period), ('contributionAreas.0.title', '기획'),
                             ('contributionAreas.0.value', '100%'), ('contributionAreas.1.title', 'UI'),
                             ('contributionAreas.1.value', '35%')]:
            self.assertIn(f'data-edit-group="projects" data-edit-index="0" data-edit-field="{field}">{value}<', block)
        for key, label in [('devPeriodLabel', '개발 기간'), ('contributionLabel', '내 기여도'), ('contributionDetailLabel', '상세 기여')]:
            self.assertIn(f'data-edit-group="labels" data-edit-index="0" data-edit-field="{key}">{label}<', block)
        divs = Elements(block).attrs('div')
        meters = [a for a in divs if a.get('role') == 'meter']
        self.assertEqual([(a['aria-valuenow'], a['aria-label']) for a in meters],
                         [('100', '기획 내 기여도'), ('35', 'UI 내 기여도')])
        self.assertTrue(all((a['aria-valuemin'], a['aria-valuemax']) == ('0', '100') for a in meters))
        self.assertEqual([a['style'] for a in divs if 'style' in a], ['width:100%', 'width:35%'])
        items = block.split('<ul class="contribution-list">', 1)[1].split('</ul>', 1)[0]
        self.assertEqual(len(Elements(items).attrs('li')), 2)
        for line in ('전투 설계', '&lt;UI&gt; 개선'):
            self.assertIn(f'<li data-edit-group="projects" data-edit-index="0" data-edit-field="contributionDetail">{line}</li>', items)

    def test_empty_project_contribution(self):
        build(self.data, self.out)
        html = self.read('projects/new-project/index.html')
        self.assertNotIn('<section class="contribution"', html)
        self.assertIn('class="contribution-placeholder" data-edit-group="projects" data-edit-index="0" '
                      'data-edit-field="devPeriod">개발 기간·기여도 입력</button>', html)

    def test_invalid_project_contribution(self):
        p = self.data['projects'][0]
        del p['feature']  # Validation also applies to projects not currently showing a detail page.
        for bad in ('-1', '101', '1.5', '1e1', '30%', 30, None):
            for key, value in [('contribution', bad), ('contributionAreas', [{'title': '기획', 'value': bad}])]:
                with self.subTest(key=key, bad=bad), self.assertRaisesRegex(ValueError, '기여도'):
                    p[key] = value
                    build(self.data, self.out)
                del p[key]
        for areas in ({}, [None], [{'title': '기획'}], [{'value': '0'}]):
            with self.subTest(areas=areas), self.assertRaises(ValueError):
                p['contributionAreas'] = areas
                build(self.data, self.out)

    def test_other_works_link_out_without_detail_pages(self):
        self.data['projects'] = [
            {'title': '플레이', 'slug': 'play', 'url': 'https://example.org/play', 'source': 'https://github.com/a/play'},
            {'title': '소스', 'slug': 'code', 'source': 'https://github.com/a/code'},
            {'title': '링크 없음', 'slug': 'none'},
        ]
        build(self.data, self.out)
        html = self.read()
        tiles = [(t, a) for t, a in Elements(html).tags if a.get('data-record') == 'projects']
        self.assertEqual([t for t, a in tiles], ['div', 'div', 'div'])  # Buttons inside, never nested links.
        self.assertEqual(['data-linked' in a for t, a in tiles], [True, True, False])
        buttons = [a for a in Elements(html).attrs('a') if 'link-btn' in a.get('class', '')]
        self.assertEqual([(a['class'], a['data-link'], a['href']) for a in buttons], [
            ('link-btn stretch', 'play', 'https://example.org/play'),
            ('link-btn', 'source', 'https://github.com/a/play'),
            ('link-btn stretch', 'source', 'https://github.com/a/code')])
        self.assertTrue(all(a.get('rel') == 'noopener' and a.get('target') == '_blank' for a in buttons))
        self.assertFalse((self.out / 'projects').exists())
        self.data['projects'][0]['url'] = 'http://example.org/play'
        with self.assertRaises(ValueError):
            build(self.data, Path(self.out.parent) / 'again')

    def test_project_tiers_and_hints(self):
        rows = self.data['projects']
        del rows[0]['feature']
        rows.extend([{'title': '나', 'slug': 'b', 'feature': '2'},
                     {'title': '다', 'slug': 'c', 'feature': '1'},
                     {'title': '라', 'slug': 'd', 'feature': '1', 'role': '기획', 'outcome': '출시'}])
        build(self.data, self.out)
        home = self.read()
        els = Elements(home)
        for tag in ('section', 'ol'):
            self.assertEqual([a['data-tier'] for a in els.attrs(tag) if 'data-tier' in a], ['1', '2', '0'])
        works = [a for a in els.attrs('li') if a.get('class') == 'work']
        self.assertEqual([(a['data-slug'], a['data-index']) for a in works],
                         [('c', '2'), ('d', '3'), ('b', '1'), ('new-project', '0')])
        self.assertNotIn('data-kind', home)
        self.assertNotIn('class="sequence"', home)
        self.assertNotIn('역할 입력 필요', home)  # Cards leave the role to the detail page.
        self.assertNotIn('work-role', home)
        detail = self.read('projects/d/index.html')
        for key in ('role', 'outcome', 'roleLabel'):
            self.assertIn(f'data-edit-field="{key}"', detail)

    def test_invalid_project_choices(self):
        for key, value in [('feature', '3'), ('aiChallenge', '2'), ('aiChallenge', ' 1'), ('aiChallenge', 1), ('aiChallenge', None)]:
            with self.subTest(key=key, value=value), self.assertRaisesRegex(ValueError, key):
                self.data['projects'][0][key] = value
                build(self.data, self.out)
            del self.data['projects'][0][key]

    def test_reject_duplicate_slug(self):
        self.data['projects'] *= 2
        with self.assertRaisesRegex(ValueError, '중복'):
            build(self.data, self.out)

    def test_reject_unsafe_link(self):
        self.data['projects'][0]['url'] = 'javascript:example()'
        with self.assertRaisesRegex(ValueError, 'https'):
            build(self.data, self.out)

    def test_video_validation_and_fallback(self):
        p = self.data['projects'][0]
        for url in ('http://example.org/x.mp4', 'https://example.org/v?name=x.mp4', '/media/x.webm', 'https://example.org/a\\b.mp4'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                p['video'] = url
                build(self.data, self.out)
        for ext in ('MP4', 'webm'):
            p['video'] = f'https://example.org/v.{ext}?s=1&t=2'
            build(self.data, self.out)
            detail = self.read('projects/new-project/index.html')
            video, = Elements(detail).attrs('video')
            self.assertEqual(video['src'], p['video'])
            self.assertEqual(video['preload'], 'metadata')
            for flag in ('controls', 'playsinline'):
                self.assertIn(flag, video)
            for flag in ('autoplay', 'muted', 'hidden'):
                self.assertNotIn(flag, video)
            self.assertNotIn('class="media-thumb"', detail)
            self.assertNotIn('title-cover', detail)

    def test_youtube_facade(self):
        ident = 'ab-CD_12345'
        p = self.data['projects'][0]
        for path in (f'youtube.com/watch?t=4&v={ident}', f'youtu.be/{ident}',
                     f'm.youtube.com/shorts/{ident}', f'www.youtube.com/embed/{ident}'):
            with self.subTest(path=path):
                p['video'] = 'https://' + path
                build(self.data, self.out)
                els = Elements(self.read('projects/new-project/index.html'))
                self.assertFalse(els.attrs('iframe') or els.attrs('video'))
                facade, = [a for a in els.attrs('a') if 'data-youtube' in a]
                self.assertEqual(facade['data-youtube'], ident)
                self.assertEqual(facade['href'], f'https://www.youtube.com/watch?v={ident}')
                self.assertEqual((facade['target'], facade['rel']), ('_blank', 'noopener'))
                thumb, = els.attrs('img')
                self.assertEqual((thumb['loading'], thumb['src']), ('lazy', f'https://i.ytimg.com/vi/{ident}/hqdefault.jpg'))
        for path in (f'youtube.com.example.org/watch?v={ident}', f'youtube.com/channel/{ident}',
                     'youtu.be/not-an-id', f'youtube.com/watch?v={ident}&v={ident}'):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError, 'YouTube'):
                p['video'] = 'https://' + path
                build(self.data, self.out)

    def test_screen_requires_image(self):
        for screens in ({}, [{'caption': '설명만'}]):
            with self.subTest(screens=screens), self.assertRaisesRegex(ValueError, '스크린샷'):
                self.data['projects'][0]['screens'] = screens
                build(self.data, self.out)

    def test_reject_media_traversal(self):
        self.data['profile']['image'] = '/media/../outside.jpg'
        with self.assertRaisesRegex(ValueError, '이미지 경로'):
            build(self.data, self.out)

    def test_uploaded_video_file_plays_in_gallery(self):
        site = self.out.parent / 'input'
        (site / 'media').mkdir(parents=True)
        for name in ['index.html', 'portfolio.css', 'portfolio.js']:
            (site / name).write_bytes((SITE / name).read_bytes())
        name = 'vid-00000000-0000-0000-0000-000000000000.mp4'
        (site / 'media' / name).write_bytes(b'\0\0\0\x18ftypmp42')
        self.data['projects'][0]['video'] = '/media/' + name
        build(self.data, self.out, site)
        detail = self.read('projects/new-project/index.html')
        self.assertIn(f'<video controls playsinline preload="metadata" src="../../media/{name}"', detail)
        self.assertTrue((self.out / 'media' / name).is_file())
        for bad in ('/media/clip.mp4', '/media/vid-00000000-0000-0000-0000-000000000000.mov'):
            self.data['projects'][0]['video'] = bad
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, '영상'):
                build(self.data, self.out.parent / 'again', site)

    def test_media_order_and_card_cover_follow_the_gallery(self):
        site = self.out.parent / 'input'
        (site / 'media').mkdir(parents=True)
        for name in ['index.html', 'portfolio.css', 'portfolio.js']:
            (site / name).write_bytes((SITE / name).read_bytes())
        for name in ('a.png', 'b.png', 'c.png'):
            (site / 'media' / name).write_bytes(b'x')
        p = self.data['projects'][0]
        p.update(feature='1', video='https://example.org/clip.mp4', videoAt='2',
                 screens=[{'image': '/media/a.png'}, {'image': '/media/b.png'}, {'image': '/media/c.png'}])
        build(self.data, self.out, site)
        detail = self.read('projects/new-project/index.html')
        keys = [a['data-media'] for a in Elements(detail).attrs('button') if 'data-media' in a]
        self.assertEqual(keys, ['screens.0', 'screens.1', 'video', 'screens.2'])
        card = self.read().split('data-slug="new-project"', 1)[1].split('</li>', 1)[0]
        self.assertIn('data-edit-field="screens.0.image" src="media/a.png"', card)
        p['videoAt'] = '9'
        build(self.data, self.out.parent / 'end', site)
        detail = (self.out.parent / 'end' / 'projects/new-project/index.html').read_text(encoding='utf-8')
        self.assertEqual([a['data-media'] for a in Elements(detail).attrs('button') if 'data-media' in a][-1], 'video')
        p['videoAt'] = 'x'
        with self.assertRaisesRegex(ValueError, 'videoAt'):
            build(self.data, self.out.parent / 'bad', site)

    def test_photo_upload_paths(self):
        site = self.out.parent / 'input'
        media = site / 'media'
        media.mkdir(parents=True)
        for name in ['index.html', 'portfolio.css', 'portfolio.js']:
            (site / name).write_bytes((SITE / name).read_bytes())
        (media / 'test photo.jpg').write_bytes(b'test data')
        (media / 'unused.jpg').write_bytes(b'unreferenced')
        self.data['profile']['image'] = '/media/test photo.jpg'
        self.data['photos'] = [{'caption': '첫 사진', 'image': '/media/test photo.jpg'}]
        p = self.data['projects'][0]
        p['sections'][0].update(image='/media/test photo.jpg', caption='기록 사진')
        p.update(video='https://example.org/trailer.webm', image='/media/test photo.jpg', screens=[
            {'image': '/media/test photo.jpg', 'caption': '<시작>'}, {'image': '/media/test photo.jpg'}])
        build(self.data, self.out, site)
        html = self.read('projects/new-project/index.html')
        self.assertIn('../../media/test%20photo.jpg', html)
        els = Elements(html)
        frames = [a for a in els.attrs('div') if a.get('class') == 'media-frame']
        self.assertEqual([a['data-edit-field'] for a in frames],
                         ['video', 'image', 'screens.0.image', 'screens.1.image', 'sections.0.image'])
        thumbs = [b for b in els.attrs('button') if b.get('class') == 'media-thumb']
        self.assertEqual(len(thumbs), len(frames))
        self.assertEqual([b.get('aria-current') for b in thumbs], ['true', None, None, None, None])
        self.assertIn('data-edit-field="screens.0.caption">&lt;시작&gt;', html)
        self.assertIn('data-edit-field="sections.0.caption">기록 사진', html)
        home = self.read()
        identity = home.split('<a class="identity-link" href="#profile">', 1)[1].split('</a>', 1)[0]
        profile = home.split('id="profile"', 1)[1].split('</main>', 1)[0]
        # The hero shows the portrait; the profile section shows it large, then the photo album.
        expected = [(identity, ['profile']), (profile, ['profile', 'photos'])]
        for fragment, groups in expected:
            imgs = Elements(fragment).attrs('img')
            self.assertEqual([(i['data-edit-group'], i['data-edit-index'], i['data-edit-field'], i['src']) for i in imgs],
                             [(g, '0', 'image', 'media/test%20photo.jpg') for g in groups])
        self.assertIn('첫 사진', profile.split('id="activity"', 1)[1])
        self.assertTrue((self.out / 'media/test photo.jpg').is_file())
        self.assertFalse((self.out / 'media/unused.jpg').exists())


if __name__ == '__main__':
    unittest.main()
