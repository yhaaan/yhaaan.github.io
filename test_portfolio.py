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
        profile = html.split('</summary>', 1)[1].split('</details>', 1)[0]
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
        disclosure, = Elements(home).attrs('details')
        self.assertEqual(disclosure['id'], 'profile')
        self.assertNotIn('open', disclosure)
        contents = home.split('<details', 1)[1].split('>', 1)[1]
        inside, after = contents.split('</details>', 1)
        summary, profile = inside.split('</summary>', 1)
        self.assertTrue(summary.startswith('<summary'))
        self.assertFalse(Elements(summary).attrs('a'))
        self.assertFalse(Elements(summary).attrs('img'))
        heading = summary.split('<h1>', 1)[1].split('</h1>', 1)[0]
        self.assertIn('data-edit-group="profile" data-edit-index="0" data-edit-field="intro">&lt;게임&gt;을 만듭니다.', heading)
        self.assertIn('data-edit-group="labels" data-edit-index="0" data-edit-field="viewProfile">프로필 보기', heading)
        self.assertNotIn('class="byline"', home)
        self.assertIn('AI Game Maker', profile)
        self.assertNotIn('class="portrait"', profile)
        self.assertIn('id="activity"', profile)
        self.assertIn('id="projects"', after)
        self.assertNotIn('data-tab=', after)
        self.assertFalse((self.out / 'profile').exists())
        for page, root in [(home, ''), (self.read('projects/new-project/index.html'), '../../')]:
            hrefs = {a.get('href') for a in Elements(page).attrs('a')}
            for target in ('index.html#projects', 'index.html#profile', 'index.html#activity'):
                self.assertIn(root + target, hrefs)

    def test_notion_fields_without_primary_skills(self):
        self.data['otherSkills'] = ['Python']
        self.data['profile']['github'] = 'https://github.com/example'
        self.data['experience'] = [{'title': '게임잼', 'url': 'https://example.org/jam'}]
        build(self.data, self.out)
        html = self.read().split('</summary>', 1)[1].split('</details>', 1)[0]
        self.assertNotIn('TOOLKIT', html)
        for text in ('Python',
                     'href="https://github.com/example"', 'href="https://example.org/jam"'):
            self.assertIn(text, html)
        self.assertNotIn('많이 해봤어요', html)

    def test_removed_project_and_empty_lists(self):
        self.data['projects'] = []
        build(self.data, self.out)
        self.assertFalse((self.out / 'projects').exists())
        home = self.read()
        self.assertIn('index.html#projects', home)
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
        activity = html.split('id="activity"', 1)[1].split('</details>', 1)[0]
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
        self.assertNotIn('ai-workflow', home)
        detail = self.read('projects/new-project/index.html')
        self.assertIn('class="prose by-ai"', detail)
        self.assertIn('class="prose by-me"', detail)
        self.assertFalse((self.out / 'ai-workflow').exists())

    def test_auto_highlights_follow_records(self):
        self.data['experience'] = [
            {'title': 'AI 게임잼', 'text': '게임잼', 'award': '특별상'},
            {'title': 'AI 공모전', 'text': '공모전'},
            {'title': 'AI 창작 프로젝트', 'text': '대외활동'},
            {'title': '콘테스트', 'text': '7위', 'award': '7위'}]
        self.data['highlights'] = [{'auto': kind, 'label': kind} for kind in ('projects', 'awards', 'ai')]
        build(self.data, self.out)
        home = self.read()
        for kind, count in [('projects', 1), ('awards', 2), ('ai', 2)]:
            self.assertIn(f'data-edit-index="{["projects", "awards", "ai"].index(kind)}" data-edit-field="auto">{count}<', home)
        self.data['highlights'] = [{'auto': 'stars', 'label': 'x'}]
        with self.assertRaisesRegex(ValueError, 'auto'):
            build(self.data, self.out / 'bad')

    def test_edit_targets_and_label_override(self):
        self.data.update(labels={'viewProfile': '<작업>', 'footer': '작업 기록'}, skills=['Unity'])
        self.data['profile']['role'] = '<클라이언트 개발자>'
        build(self.data, self.out, editor_api='/__editor')
        self.assertIn('&lt;작업&gt;', self.read())
        self.assertIn('&lt;클라이언트 개발자&gt;', self.read())
        for page, expected in [('index.html', [('labels','viewProfile'), ('labels','footer'), ('projects','title'),
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
        self.assertNotIn('class="deck"', detail)
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
        for key, value in [('feature', '3')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
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
            self.assertEqual(video['data-src'], p['video'])
            self.assertIn('muted', video)
            self.assertIn('playsinline', video)
            self.assertIn('class="title-cover"', detail)

    def test_reject_media_traversal(self):
        self.data['profile']['image'] = '/media/../outside.jpg'
        with self.assertRaisesRegex(ValueError, '이미지 경로'):
            build(self.data, self.out)

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
        self.data['projects'][0]['sections'][0]['image'] = '/media/test photo.jpg'
        build(self.data, self.out, site)
        html = self.read('projects/new-project/index.html')
        self.assertIn('../../media/test%20photo.jpg', html)
        profile = self.read().split('</summary>', 1)[1].split('</details>', 1)[0]
        images = [(img['data-edit-group'], img['src']) for img in Elements(profile).attrs('img')
                  if 'data-edit-group' in img]
        self.assertEqual(images, [('profile', 'media/test%20photo.jpg'), ('photos', 'media/test%20photo.jpg')])
        self.assertIn('첫 사진', profile.split('id="activity"', 1)[1])
        self.assertTrue((self.out / 'media/test photo.jpg').is_file())
        self.assertFalse((self.out / 'media/unused.jpg').exists())


if __name__ == '__main__':
    unittest.main()
