import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from build_portfolio import BASE, SITE, build


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        tmp = TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.out = Path(tmp.name) / 'public'
        self.data = {'profile': {'name': '요한'}, 'projects': [
            {'title': '새 프로젝트', 'slug': 'new-project', 'sections': [{'title': '기록', 'text': '상세 내용'}]}
        ]}

    def test_actual_content_builds(self):
        data = json.loads((BASE / 'portfolio.json').read_text(encoding='utf-8'))
        build(data, self.out)
        for p in data.get('projects') or []:
            self.assertTrue((self.out / 'projects' / p['slug'] / 'index.html').exists())
        self.assertFalse((self.out / 'portfolio.json').exists())
        self.assertFalse((self.out / '.pages.yml').exists())

    def test_detail_and_text_fields(self):
        self.data.update(skills=['HTML'], experience=[{'title': '경력'}],
                         archive=[{'title': '예전 소개', 'text': '<script>example</script>'}])
        build(self.data, self.out)
        html = (self.out / 'index.html').read_text(encoding='utf-8')
        for text in ('projects/new-project/', 'HTML', '경력', '&lt;script&gt;', '예전 소개'):
            self.assertIn(text, html)
        self.assertNotIn('<script', html)
        self.assertNotIn('id="photos"', html)
        detail = (self.out / 'projects/new-project/index.html').read_text(encoding='utf-8')
        self.assertIn('상세 내용', detail)
        self.assertIn('../../index.html#projects', detail)

    def test_notion_fields_without_primary_skills(self):
        self.data['otherSkills'] = ['Python']
        self.data['profile']['github'] = 'https://github.com/example'
        self.data['experience'] = [{'title': '게임잼', 'url': 'https://example.org/jam'}]
        build(self.data, self.out)
        html = (self.out / 'index.html').read_text(encoding='utf-8')
        for text in ('해본 적 있어요', 'Python', 'TOOLKIT / 01',
                     'href="https://github.com/example"', 'href="https://example.org/jam"'):
            self.assertIn(text, html)
        self.assertNotIn('많이 해봤어요', html)

    def test_removed_project_and_empty_lists(self):
        self.data['projects'] = []
        build(self.data, self.out)
        self.assertFalse((self.out / 'projects').exists())
        self.assertNotIn('#projects', (self.out / 'index.html').read_text(encoding='utf-8'))

    def test_reject_duplicate_slug(self):
        self.data['projects'] *= 2
        with self.assertRaisesRegex(ValueError, '중복'):
            build(self.data, self.out)

    def test_reject_unsafe_link(self):
        self.data['projects'][0]['url'] = 'javascript:example()'
        with self.assertRaisesRegex(ValueError, 'https'):
            build(self.data, self.out)

    def test_reject_media_traversal(self):
        self.data['profile']['image'] = '/media/../outside.jpg'
        with self.assertRaisesRegex(ValueError, '이미지 경로'):
            build(self.data, self.out)

    def test_photo_upload_paths(self):
        site = self.out.parent / 'input'
        media = site / 'media'
        media.mkdir(parents=True)
        for name in ['index.html', 'portfolio.css']:
            (site / name).write_bytes((SITE / name).read_bytes())
        (media / 'test photo.jpg').write_bytes(b'test data')
        (media / 'unused.jpg').write_bytes(b'unreferenced')
        self.data['photos'] = [{'caption': '첫 사진', 'image': '/media/test photo.jpg'}]
        self.data['projects'][0]['sections'][0]['image'] = '/media/test photo.jpg'
        build(self.data, self.out, site)
        html = (self.out / 'projects/new-project/index.html').read_text(encoding='utf-8')
        self.assertIn('../../media/test%20photo.jpg', html)
        self.assertTrue((self.out / 'media/test photo.jpg').is_file())
        self.assertFalse((self.out / 'media/unused.jpg').exists())


if __name__ == '__main__':
    unittest.main()
