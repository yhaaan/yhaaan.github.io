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
test('blocks use their own item fields and collect nested image references',()=>{
  const image='/media/scene.png';
  const p={title:'Gallery',slug:'gallery',screens:[{image},{image,caption:'첫 장면'}],sections:[{title:'기록',image:'/media/section.jpg'}]};
  const data={profile:{name:'A'},projects:[p]};
  assert.deepEqual(validate(data),new Set([image,'/media/section.jpg']));
  for(const screens of [{},[{caption:'사진 없음'}],[{image,title:'단락 아님'}],[{image:'/outside.png'}],[{image,caption:3}]]){
    assert.throws(()=>validate({...data,projects:[{...p,screens}]}));
  }
  assert.throws(()=>validate({...data,projects:[{...p,sections:[{image}]}]}));
});
test('project percentages are integer strings; each contribution area needs a title and percentage',()=>{
  const p={title:'Game',slug:'game',devPeriod:'2025.03 – 2025.07',contributionDetail:'전투 설계\nUI 개선'};
  const check=fields=>validate({profile:{name:'A'},projects:[{...p,...fields}]});
  for(const value of ['0','35','100'])check({contributionAreas:[{title:'개발',value},{title:'기획',value}]});
  check({contributionAreas:[]});
  assert.throws(()=>check({contribution:'40'}));  // The overall figure is no longer a field.
  for(const value of ['-1','101','1.5','1e1','30%',' 5',30,null]){
    assert.throws(()=>check({contributionAreas:[{title:'기획',value}]}),/기여도/);
  }
  for(const areas of [{},[null],[{value:'0'}],[{title:'기획'}],[{title:'기획',value:''}]]){
    assert.throws(()=>check({contributionAreas:areas}));
  }
});
test('production headcount is an optional positive integer string',()=>{
  const check=teamSize=>validate({profile:{name:'A'},projects:[{title:'Game',slug:'game',teamSize}]});
  for(const value of [undefined,'','1','3','999'])check(value);
  for(const value of ['0','-1','1.5','1e1','3명',' 3','03','1000',3,null]){
    assert.throws(()=>check(value),/제작 인원/);
  }
});

test('video accepts HTTPS files and supported YouTube routes only',()=>{
  const p={title:'Film',slug:'film'},data={profile:{name:'A'},projects:[p]},id='ab-CD_12345';
  for(const path of ['example.org/media.MP4?q=1','example.org/v.webm',`www.youtube.com/watch?v=${id}`,`youtu.be/${id}`,`m.youtube.com/shorts/${id}`,`youtube.com/embed/${id}`]){
    p.video='https://'+path;validate(data);
  }
  for(const url of [`http://youtu.be/${id}`,`https://youtube.com.example.org/watch?v=${id}`,`https://youtube.com/channel/${id}`,'https://youtube.com/watch?v=bad',`https://youtu.be/${id}/extra`]){
    p.video=url;assert.throws(()=>validate(data),/영상/);
  }
});
test('an uploaded video file is a referenced local upload',()=>{
  const path='/media/vid-00000000-0000-0000-0000-000000000000.webm';
  const data={profile:{name:'A'},projects:[{title:'B',slug:'b',video:path}]};
  assert.ok(validate(data).has(path));
  for(const bad of ['/media/clip.mp4','/media/vid-00000000-0000-0000-0000-000000000000.mov']){
    data.projects[0].video=bad;assert.throws(()=>validate(data));
  }
});
test('video position is a small non-negative integer string',()=>{
  const data={profile:{name:'A'},projects:[{title:'B',slug:'b',videoAt:'3'}]};
  validate(data);
  for(const bad of ['-1','1.5','x','1000']){data.projects[0].videoAt=bad;assert.throws(()=>validate(data));}
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
test('AI challenge is an optional project flag with exact string values',()=>{
  const project={title:'Jam entry',slug:'jam'};
  const data={profile:{name:'A'},projects:[project]};
  validate(data);
  for(const value of ['', '1']){project.aiChallenge=value;validate(data);}
  for(const value of ['2', ' 1', 1, null]){
    project.aiChallenge=value;
    assert.throws(()=>validate(data),/AI 대회 작품/);
  }
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
