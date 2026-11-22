// Private API for the Pages frontend. Never include this module or its bindings in dist/.
import { validate, uploadPattern } from './site/owner-fields.mjs';
const origin = 'https://yhaaan.github.io', repo = '/repos/yhaaan/yhaaan.github.io';
const ttl = 1800, limit = 8 * 1024 * 1024;
class Problem extends Error { constructor(status, msg) { super(msg); this.status = status; } }
const bad = msg => { throw new Problem(400,msg); };
const conflict = () => { throw new Problem(409,'다른 변경이 먼저 저장되었습니다. 새로고침 후 최신 내용에서 다시 편집하세요.'); };
const unauthorized = () => { throw new Problem(401,'세션이 만료되었거나 로그인이 필요합니다.'); };
async function body(req) {
  if (req.headers.get('Content-Type')?.split(';')[0] !== 'application/json') bad('JSON 요청이 필요합니다.');
  if (Number(req.headers.get('Content-Length')) > limit) bad('한 번에 저장할 사진 수나 크기를 줄이세요.');
  const reader = req.body?.getReader(); if (!reader) bad('빈 요청입니다.');
  const chunks = []; let size = 0;
  for (;;) { const {value,done} = await reader.read(); if (done) break;
    size += value.length; if (size > limit) { await reader.cancel(); bad('요청이 너무 큽니다.'); } chunks.push(value); }
  try { return JSON.parse(await new Blob(chunks).text()); } catch { bad('올바르지 않은 JSON입니다.'); }
}
async function gh(token, path, method='GET', data) {
  const r = await fetch('https://api.github.com' + path, {method, redirect:'error', headers:{
    Authorization:`Bearer ${token}`, 'User-Agent':'yohan-portfolio-editor', Accept:'application/vnd.github+json',
    'Content-Type':'application/json', 'X-GitHub-Api-Version':'2022-11-28'}, body: data && JSON.stringify(data)});
  if (!r.ok) {
    if (r.status === 401) unauthorized();
    if (r.status === 409 || (method === 'PATCH' && r.status === 422)) conflict();
    throw new Problem(502,`GitHub 요청 실패 (${r.status}). 앱의 저장소 설치, 쓰기 권한과 브랜치 보호 설정을 확인하세요.`);
  }
  return r.json();
}
async function checkOwner(token,env) {
  const user = await gh(token,'/user');
  if (!/^\d+$/.test(env.OWNER_ID) || String(user.id) !== env.OWNER_ID || user.login.toLowerCase() !== 'yhaaan')
    throw new Problem(403,'이 포트폴리오 소유자가 아닙니다.');
}
async function read(token) {
  const ref = await gh(token, repo+'/git/ref/heads/main');
  const file = await gh(token, repo+'/contents/portfolio.json?ref='+ref.object.sha);
  if (!file.content || file.encoding !== 'base64') throw new Problem(422,'portfolio.json을 읽을 수 없습니다.');
  const data = JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(file.content), c=>c.charCodeAt(0))));
  return {data, version:ref.object.sha};
}
export function checkUpload(item, refs) {
  if (!uploadPattern.test(item?.path) || !refs.has(item.path) || typeof item.content !== 'string' || item.content.length > 2796204) bad('사진 경로 또는 크기가 잘못되었습니다.');
  let bytes; try { bytes = atob(item.content); } catch { bad('사진 데이터를 읽을 수 없습니다.'); }
  const ext = item.path.split('.').pop();
  const ok = ext === 'jpg' ? bytes.startsWith('\xff\xd8\xff') : ext === 'png' ? bytes.startsWith('\x89PNG\r\n\x1a\n') : bytes.startsWith('RIFF') && bytes.slice(8,12)==='WEBP';
  if (!ok || bytes.length > 2097152) bad('사진은 2MB 이하의 JPEG, PNG, WebP만 지원합니다.');
}
async function save(token, req) {
  let refs; try { refs = validate(req.data); } catch(e) { bad(e.message); }
  const old = await read(token); if (old.version !== req.version) conflict();
  const existing = validate(old.data), uploads = req.uploads ?? [];
  if (!Array.isArray(uploads) || uploads.length > 8) bad('사진 수가 너무 많습니다.');
  const fresh = new Set();
  for (const f of uploads) { checkUpload(f,refs); if (fresh.has(f.path) || existing.has(f.path)) bad('중복 사진 경로입니다.'); fresh.add(f.path); }
  for (const p of refs) if (!existing.has(p) && !fresh.has(p)) bad('선택한 사진 파일이 없습니다.');
  const base = await gh(token,repo+'/git/commits/'+old.version);
  const tree = [{path:'portfolio.json', mode:'100644', type:'blob', content:JSON.stringify(req.data,null,2)+'\n'}];
  for (const f of uploads) {
    const blob = await gh(token,repo+'/git/blobs','POST',{encoding:'base64',content:f.content});
    tree.push({path:'site'+f.path, mode:'100644', type:'blob',sha:blob.sha});
  }
  const t = await gh(token,repo+'/git/trees','POST',{base_tree:base.tree.sha, tree});
  const commit = await gh(token,repo+'/git/commits','POST',{tree:t.sha,parents:[old.version],message:'🗃️[Update] 포트폴리오 편집 내용 반영'});
  await gh(token,repo+'/git/refs/heads/main','PATCH',{sha:commit.sha,force:false});
  return {version:commit.sha};
}
export default { async fetch(req,env) {
  const headers = {'Cache-Control':'no-store', Vary:'Origin', 'Content-Type':'application/json'};
  const reply = (v,s=200) => new Response(JSON.stringify(v),{status:s,headers});
  if (req.headers.get('Origin') !== origin) return reply({error:'허용되지 않은 출처입니다.'},403);
  Object.assign(headers,{'Access-Control-Allow-Origin':origin,'Access-Control-Allow-Headers':'Authorization, Content-Type','Access-Control-Allow-Methods':'POST, OPTIONS'});
  if (req.method === 'OPTIONS') return new Response(null,{status:204,headers});
  if (req.method !== 'POST') return reply({error:'POST 요청이 필요합니다.'},405);
  try {
    const path = new URL(req.url).pathname;
    if (path === '/start') {
      const {challenge,state} = await body(req);
      if (!/^[\w-]{43}$/.test(challenge) || !/^[\w-]{43}$/.test(state)) bad('로그인을 다시 시작하세요.');
      const params = new URLSearchParams({client_id:env.GITHUB_CLIENT_ID,redirect_uri:origin+'/',state,code_challenge:challenge,code_challenge_method:'S256'});
      return reply({url:'https://github.com/login/oauth/authorize?'+params});
    }
    if (path === '/session') {
      const {code,verifier} = await body(req);
      if (!/^[\w-]{43}$/.test(verifier) || typeof code !== 'string' || !code || code.length>256) bad('로그인 정보가 올바르지 않습니다.');
      const res = await fetch('https://github.com/login/oauth/access_token',{method:'POST',headers:{Accept:'application/json','Content-Type':'application/json'},body:JSON.stringify({client_id:env.GITHUB_CLIENT_ID,client_secret:env.GITHUB_CLIENT_SECRET,code,code_verifier:verifier,redirect_uri:origin+'/'})});
      const auth = await res.json(); if (!res.ok || !auth.access_token) unauthorized();
      await checkOwner(auth.access_token,env);
      const session = crypto.randomUUID();
      await env.SESSIONS.put(session,auth.access_token,{expirationTtl:ttl});
      return reply({session});
    }
    const session = req.headers.get('Authorization')?.match(/^Bearer ([a-f0-9-]{36})$/)?.[1];
    if (!session) unauthorized();
    const token = await env.SESSIONS.get(session); if (!token) unauthorized();
    if (path === '/logout') { await env.SESSIONS.delete(session); return reply({}); }
    await checkOwner(token,env); // never trust the browser's identity or UI state
    if (path === '/read') return reply(await read(token));
    if (path === '/save') return reply(await save(token,await body(req)));
    return reply({error:'없는 경로입니다.'},404);
  } catch(e) { return reply({error:e instanceof Problem ? e.message : '편집 API 설정 또는 연결을 확인하세요.'},e instanceof Problem ? e.status : 500); }
}};
