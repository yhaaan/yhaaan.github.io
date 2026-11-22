import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import './site/owner.mjs';
import worker,{checkUpload} from './editor-worker.mjs';
import {validate} from './site/owner-fields.mjs';
const origin='https://yhaaan.github.io';
const request=(path,body={},headers={})=>new Request('https://editor.example'+path,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',...headers},body:JSON.stringify(body)});
test('existing data is editable; duplicate slug and non-media path rejected',async()=>{
  const data=JSON.parse(await readFile(new URL('./portfolio.json',import.meta.url),'utf8'));validate(data);
  const bad={profile:{name:'test'},projects:[{title:'A',slug:'x'},{title:'B',slug:'x'}]};assert.throws(()=>validate(bad));
  assert.throws(()=>validate({profile:{name:'A',image:'/media/../a.png'}}));
  assert.throws(()=>checkUpload({path:'/media/../portfolio.json',content:'AA=='},new Set()));
});
test('highlights need a number or an automatic count',()=>{
  const data={profile:{name:'A'},highlights:[{auto:'projects',label:'프로젝트'},{value:'3',label:'출시'}]};
  validate(data);
  data.highlights[0].auto='stars';assert.throws(()=>validate(data));
  delete data.highlights[0].auto;assert.throws(()=>validate(data));
});
test('skill groups need a field name and items',()=>{
  const data={profile:{name:'A'},skillGroups:[{title:'AI',items:'Claude Code, Codex'}]};
  validate(data);
  data.skillGroups[0].items='';assert.throws(()=>validate(data));
  data.skillGroups[0]={title:'AI',items:'x',extra:'y'};assert.throws(()=>validate(data));
});
test('project tier is an optional enumerated choice',()=>{
  const data={profile:{name:'A'},projects:[{title:'B',slug:'b'}]};
  const p=data.projects[0];
  for(const feature of ['1','2','']){p.feature=feature;validate(data);}
  p.feature='x';assert.throws(()=>validate(data));
  delete p.feature;p.kind='web';assert.throws(()=>validate(data));
  delete p.kind;validate(data);
});
test('cross-origin and unauthenticated writes fail closed',async()=>{
  assert.equal((await worker.fetch(request('/save',{},{Origin:'https://example.com'}),{})).status,403);
  assert.equal((await worker.fetch(request('/save'),{})).status,401);
});
test('account is checked before write, stale main is not overwritten',async()=>{
  const data={profile:{name:'요한'}};
  const env={OWNER_ID:'123',SESSIONS:{get:async()=>'mock'}};
  let user={id:321,login:'not-owner'},writes=0;
  const original=globalThis.fetch;
  globalThis.fetch=async(url,opt)=>{
    if(opt.method!=='GET')writes++;
    let body=url.endsWith('/user')?user:url.endsWith('/git/ref/heads/main')?{object:{sha:'current'}}:{content:Buffer.from(JSON.stringify(data)).toString('base64'),encoding:'base64'};
    return Response.json(body);
  };
  try{
    const req=()=>request('/save',{version:'old',data},{Authorization:'Bearer 00000000-0000-0000-0000-000000000000'});
    assert.equal((await worker.fetch(req(),env)).status,403);
    user={id:123,login:'yhaaan'};assert.equal((await worker.fetch(req(),env)).status,409);assert.equal(writes,0);
  }finally{globalThis.fetch=original;}
});
