// These definitions drive both the forms and the production write validator.
const field = (key, label, type = 'text', required = false) => ({key, label, type, required});
const choice = (key, label, options) => ({...field(key, label, 'choice'), options});
const title = field('title', '제목', 'text', true);
const image = field('image', '사진', 'image');
const labels = {
  roleLabel:'역할',
  allActivities:'이전 활동 더 보기', hideProfile:'프로필 닫기',
  skip:'본문 바로가기', main:'MAIN', projectNav:'프로젝트', archiveNav:'Archive', profileNav:'프로필', activityNav:'활동', viewProfile:'프로필 보기', projects:'프로젝트', awards:'수상', ai:'AI 프로젝트',
  empty:'아직 등록된 항목이 없습니다.', intro:'프로젝트 소개', activity:'활동 소개', github:'GitHub', baekjoon:'solved.ac', live:'사이트 열기',
  source:'소스 보기', related:'관련 자료', videoLink:'영상 열기', prev:'이전', next:'다음', pause:'일시 정지', resume:'재생',
  archive:'아카이브', skills:'스킬', toolkit:'TOOLKIT', primary:'많이 해봤어요', secondary:'해본 적 있어요', experience:'이력',
  photos:'사진', history:'이전 프로필', top:'맨 위로 ↑', footer:'Portfolio',
  highlights:'한눈에', award:'수상'
};
export const singleton = key => key === 'profile' || key === 'labels';
export const sections = [title, field('text', '본문', 'long'), image, field('caption', '사진 설명')];
export const groups = {
  profile: ['프로필', [field('name', '이름', 'text', true), field('handle', '활동명'), field('role', '직무 (기본: AI Game Maker)'), field('intro', '소개', 'long'), field('github', 'GitHub', 'url'), field('baekjoon', 'solved.ac 프로필 주소', 'url'), field('baekjoonTier', 'solved.ac 티어 (예: Gold IV)'), image]],
  labels: ['화면 문구', Object.entries(labels).map(([k,v]) => field(k,v))],
  projects: ['프로젝트', [title, field('slug', '상세 주소 (예: my-game)', 'slug', true), choice('feature', '작품 단계', [['','그 밖의 작품'],['1','대표작'],['2','주목할 작품']]), field('category', '분류'), field('role', '내 역할'), field('outcome', '대표 성과 한 줄'), field('award', '수상 (있을 때만)'), field('summary', '소개', 'long'), image, field('video', '영상 (https MP4 / WebM)', 'video'), field('url', '실행 / 사이트 링크', 'url'), field('source', '소스 링크', 'url'), field('sections', '상세 본문 단락', 'blocks')]],
  profileLinks: ['프로필 링크', [title, field('url', '주소', 'url', true)]],
  credentials: ['학력·교육', [field('title', '이름 (예: 세종대학교 컴퓨터공학과)', 'text', true), field('period', '기간 (예: 2020~)'), field('text', '상태 (예: 재학, 수료)')]],
  skillGroups: ['스킬 분야', [field('title', '분야 (예: 엔진)', 'text', true), field('items', '항목 (쉼표로 구분)', 'text', true)]],
  skills: ['(이전) 많이 사용한 스킬', null], otherSkills: ['(이전) 경험한 스킬', null],
  experience: ['이력', [title, field('period', '기간'), field('text', '설명', 'long'), field('award', '수상 (있을 때만)'), field('url', '관련 링크', 'url')]],
  highlights: ['한눈에 지표', [choice('auto', '숫자 계산', [['','직접 입력'],['projects','프로젝트 수'],['awards','수상·입상 수 (이력의 수상 칸)'],['ai','AI 게임잼·해커톤·공모전 참가 수']]), field('value', '숫자 (직접 입력일 때)'), field('label', '설명', 'text', true)]],
  photos: ['사진첩', [field('caption', '사진 설명', 'text', true), field('image', '사진', 'image', true)]],
  archive: ['이전 프로필', [title, field('text', '내용', 'long')]]
};
export const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
export const uploadPattern = /^\/media\/pic-[a-f0-9-]{36}\.(jpg|png|webp)$/;
export function validate(data) {
  const refs = new Set(), slugs = new Set();
  const fail = msg => { throw new Error(msg); };
  const list = v => Array.isArray(v) && v.length <= 1000;
  function record(row, fields) {
    if (!row || typeof row !== 'object' || Array.isArray(row)) fail('항목 형식이 올바르지 않습니다.');
    if (Object.keys(row).some(k => !fields.some(f => f.key === k))) fail('지원하지 않는 필드가 있습니다.');
    for (const f of fields) {
      const v = row[f.key];
      if (f.type === 'blocks') {
        if (v != null) { if (!list(v)) fail('본문 단락 수를 확인하세요.'); v.forEach(b => record(b, sections)); }
        continue;
      }
      if (f.type === 'choice' && Object.hasOwn(row, f.key) && !f.options.some(([value]) => v === value)) fail(`${f.label} 값을 확인하세요.`);
      if (v == null || v === '') { if (f.required) fail(`${f.label} 입력이 필요합니다.`); continue; }
      if (typeof v !== 'string' || !v.trim() || v.length > 65000) fail(`${f.label} 값을 확인하세요.`);
      if (f.type === 'slug') {
        if (!slugPattern.test(v) || v.length > 100 || slugs.has(v)) fail('프로젝트 주소는 고유한 영문 소문자·숫자·하이픈이어야 합니다.');
        slugs.add(v);
      }
      if (f.type === 'url' || f.type === 'video') {
        let url;
        try {
          if (!/^https:\/\/[^\s\\\x00-\x1f\x7f]+$/.test(v)) throw Error();
          url = new URL(v);
          if (!url.hostname || url.username || url.password || v.slice(8).startsWith('/')) throw Error();
        } catch { fail(`${f.label}: https 주소가 필요합니다.`); }
        if (f.type === 'video' && !/\.(mp4|webm)$/i.test(url.pathname)) fail('영상은 MP4 또는 WebM 주소여야 합니다.');
      }
      if (f.type === 'image') {
        if (!/^\/media\/(?:[^/\\\x00-\x1f]+\/)*[^/\\\x00-\x1f]+\.(png|jpeg|jpg|gif|webp|avif)$/i.test(v) || v.split('/').some(p => p === '.' || p === '..')) fail('사진 경로가 올바르지 않습니다.');
        refs.add(v);
      }
    }
  }
  if (!data || Object.keys(data).some(k => !Object.hasOwn(groups,k))) fail('포트폴리오 형식을 확인하세요.');
  for (const [key, [,fields]] of Object.entries(groups)) {
    if (singleton(key)) {
      if (key === 'profile' || Object.hasOwn(data,key)) record(data[key],fields);
      continue;
    }
    const rows = data[key] ?? [];
    if (!list(rows)) fail('항목 수를 확인하세요.');
    for (const row of rows) {
      if (fields) record(row,fields);
      else if (typeof row !== 'string' || !row.trim() || row.length > 200) fail('스킬 이름을 확인하세요.');
    }
  }
  for (const row of data.highlights ?? []) if (!row.auto && !row.value) fail('한눈에 지표: 숫자를 입력하거나 자동 계산을 고르세요.');
  if (new TextEncoder().encode(JSON.stringify(data,null,2)).length > 800000) fail('전체 텍스트가 너무 큽니다.');
  return refs;
}
