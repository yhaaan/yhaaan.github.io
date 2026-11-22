import {groups, sections, singleton, validate} from './owner-fields.mjs';
const S='portfolio.owner.session', L='portfolio.owner.login';
const node=(tag,text='',cls='')=>{const n=document.createElement(tag); n.textContent=text; if(cls)n.className=cls; return n;};
function button(text,fn){const b=node('button',text,'owner-btn'); b.type='button'; b.addEventListener('click',fn);return b;}
const b64url=bytes=>btoa(String.fromCharCode(...bytes)).replace(/=/g,'').replace(/\+/g,'-').replace(/\//g,'_');
const random=()=>b64url(crypto.getRandomValues(new Uint8Array(32)));
/* A drag is a preview: the captured handle stays in its original parent until
   release. Only the slot moves between grids, so cancellation needs no replay. */
function setupOrder(root, bar, status, enabled, persist) {
  const lists = Array.from(root.querySelectorAll('.works'));
  const items = list => Array.from(list.children).filter(el => el.matches('.work'));
  const snapshot = () => lists.map(items);
  let baseline = snapshot(), changes = 0, drag = null;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const effects = new Map();
  const save = button('', () => { if (!drag && changes) persist(); });
  const undo = button('되돌리기', () => {
    cancel();
    baseline.forEach((rows, i) => lists[i].append(...rows));
    refresh(); status.textContent = '원래 순서로 되돌렸습니다.';
  });
  bar.insertBefore(save, status); bar.insertBefore(undo, status);

  function refresh() {
    changes = 0;
    snapshot().forEach((rows, i) => {
      const shelf = lists[i].closest('.shelf');
      shelf.classList.toggle('is-empty', !rows.length);
      rows.forEach((row, j) => {
        if (row !== baseline[i][j]) changes++;
      });
    });
    save.hidden = undo.hidden = changes === 0;
    save.textContent = `순서 저장 (${changes})`;
  }
  function announce(row) {
    const list = row.parentElement;
    const label = list.closest('.shelf').getAttribute('aria-label');
    status.textContent = `${row.querySelector('h3').textContent} · ${label} ${items(list).indexOf(row)+1}번째`;
  }
  function flip(change) {
    if (motion.matches || !Element.prototype.animate) { change(); return; }
    // Measure grid cells (not their animated children) for stable hit testing.
    const first = new Map();
    root.querySelectorAll('.work:not(.dragging)').forEach(row => first.set(row,row.getBoundingClientRect()));
    change();
    for (const [row, a] of first) {
      const b = row.getBoundingClientRect(), x = a.left-b.left, y = a.top-b.top;
      if (!x && !y) continue;
      effects.get(row)?.cancel();
      const effect = row.querySelector('.tile').animate([{transform:`translate(${x}px,${y}px)`},{transform:'none'}],{duration:150,easing:'ease-out'});
      effects.set(row,effect);
      effect.onfinish = () => { if (effects.get(row) === effect) effects.delete(row); };
    }
  }
  function keyMove(e, row, handle) {
    const step = {ArrowUp:-1,ArrowLeft:-1,ArrowDown:1,ArrowRight:1}[e.key];
    if (!step || !enabled() || drag) return;
    e.preventDefault(); e.stopPropagation();
    let list = row.parentElement;
    const rows = items(list);
    const peer = rows[rows.indexOf(row)+step];
    let before;
    if (peer) before = step > 0 ? peer.nextElementSibling : peer;
    else {
      // Crossing into the next tier lands at its start; into the previous tier, at its end.
      list = lists[lists.indexOf(list)+step];
      if (!list) return;
      before = step > 0 ? items(list)[0] ?? null : null;
    }
    flip(() => list.insertBefore(row, before));
    refresh(); handle.focus(); announce(row);
  }

  const distance = (p, lo, hi) => Math.max(lo-p, p-hi, 0);
  function position(d) {
    d.row.style.transform = `translate(${d.x-d.startX}px,${d.y-d.startY}px)`;
    let list, best = Infinity;
    for (const grid of lists) {
      const r = grid.closest('.shelf').getBoundingClientRect();
      const score = distance(d.y,r.top,r.bottom);
      if (score < best) { best = score; list = grid; }
    }
    const slotRect = d.slot.getBoundingClientRect();
    if (d.slot.parentElement === list && !distance(d.y,slotRect.top,slotRect.bottom) && !distance(d.x,slotRect.left,slotRect.right)) return;
    // Choose the nearest grid row first, then the nearest column in that row.
    let peer = null, rect, dy = Infinity, dx = Infinity;
    for (const cell of items(list)) {
      if (cell === d.row) continue;
      const r = cell.getBoundingClientRect();
      const y = distance(d.y,r.top,r.bottom), x = Math.abs(d.x-r.left-r.width/2);
      if (y < dy || (y === dy && x < dx)) { peer = cell; rect = r; dy = y; dx = x; }
    }
    let before = peer;
    if (peer) {
      const single = getComputedStyle(list).gridTemplateColumns.split(' ').length === 1;
      const after = single ? d.y >= rect.top+rect.height/2 : d.y > rect.bottom || (d.y >= rect.top && d.x >= rect.left+rect.width/2);
      if (after) before = peer.nextElementSibling;
    }
    if (before !== d.slot && !(list === d.slot.parentElement && d.slot.nextElementSibling === before)) {
      flip(() => list.insertBefore(d.slot,before));
    }
  }
  function frame() {
    const d = drag;
    if (!d) return;
    if (d.moved) {
      const edge = Math.min(innerHeight/5,72);
      const speed = d.y < edge ? -Math.min(1,(edge-d.y)/edge) : Math.min(1,Math.max(0,(d.y-innerHeight+edge)/edge));
      if (speed) window.scrollBy({top:Math.ceil(Math.abs(speed)*16)*Math.sign(speed),behavior:'instant'});
      position(d);
    }
    d.frame = requestAnimationFrame(frame);
  }
  function begin(e, row, handle) {
    if (!enabled() || drag || !e.isPrimary || e.button !== 0) return;
    e.preventDefault(); e.stopPropagation();
    const r = row.getBoundingClientRect(), slot = node('li','','drop-slot');
    slot.setAttribute('aria-hidden','true'); slot.style.minHeight = `${r.height}px`;
    handle.focus({preventScroll:true}); handle.setPointerCapture(e.pointerId);
    row.before(slot); row.classList.add('dragging');
    Object.assign(row.style,{left:`${r.left}px`,top:`${r.top}px`,width:`${r.width}px`,height:`${r.height}px`});
    drag = {row,handle,slot,id:e.pointerId,startX:e.clientX,startY:e.clientY,x:e.clientX,y:e.clientY,moved:false};
    drag.frame = requestAnimationFrame(frame);
  }
  function track(e) {
    if (!drag || drag.id !== e.pointerId) return;
    drag.x = e.clientX; drag.y = e.clientY;
    drag.moved ||= Math.hypot(drag.x-drag.startX,drag.y-drag.startY) >= 3;
  }
  function finish(commit) {
    const d = drag;
    if (!d) return;
    cancelAnimationFrame(d.frame);
    if (commit && d.moved) position(d);
    drag = null;
    if (d.handle.hasPointerCapture(d.id)) d.handle.releasePointerCapture(d.id);
    if (commit && d.moved) d.slot.replaceWith(d.row); else d.slot.remove();
    d.row.classList.remove('dragging');
    for (const prop of ['top','left','width','height','transform']) d.row.style.removeProperty(prop);
    refresh(); d.handle.focus({preventScroll:true});
    if (commit) announce(d.row); else status.textContent = '이동을 취소했습니다.';
  }
  function cancel() { finish(false); }
  window.addEventListener('blur',cancel);
  document.addEventListener('keydown',e => {
    if (e.key === 'Escape' && drag) { e.preventDefault(); cancel(); }
  });
  for (const row of baseline.flat()) {
    const handle = node('button','↕','drag-handle'); handle.type = 'button';
    handle.setAttribute('aria-label',row.querySelector('h3').textContent+' 순서 이동');
    row.append(handle);
    handle.addEventListener('click',e => { e.preventDefault(); e.stopPropagation(); });
    handle.addEventListener('keydown',e => keyMove(e,row,handle));
    handle.addEventListener('pointerdown',e => begin(e,row,handle));
    handle.addEventListener('pointermove',track);
    handle.addEventListener('pointerup',e => { if (drag?.id === e.pointerId) { track(e); finish(true); } });
    for (const type of ['pointercancel','lostpointercapture']) handle.addEventListener(type,e => { if (drag?.id === e.pointerId) cancel(); });
  }
  refresh();
  return {
    cancel, get pending() { return changes !== 0; },
    arrange(next) {
      const projects = next.projects ?? [], bySlug = new Map(projects.map(p => [p.slug,p]));
      // A remote build can lag behind /read. Never apply an old DOM's tier or
      // relative order over a newer model; absent cards alone are harmless.
      for (const [i, rows] of baseline.entries()) {
        const visible = new Set(rows.map(row => row.dataset.slug));
        const expected = projects.filter(p => visible.has(p.slug) && (p.feature || '0') === lists[i].dataset.tier);
        if (expected.length !== rows.length || expected.some((p,j) => p.slug !== rows[j].dataset.slug)) throw Error('공개 화면과 저장된 순서가 다릅니다. 배포 후 새로고침하세요.');
      }
      const ordered = [];
      for (const list of lists) for (const row of items(list)) {
        const slug = row.dataset.slug, p = bySlug.get(slug);
        if (list.dataset.tier === '0') delete p.feature; else p.feature = list.dataset.tier;
        ordered.push(p); bySlug.delete(slug);
      }
      next.projects = ordered.concat(Array.from(bySlug.values()));
    },
    committed(projects) {
      baseline = snapshot();
      const indices = new Map(projects.map((p,i) => [p.slug,i]));
      for (const row of baseline.flat()) {
        const index = indices.get(row.dataset.slug);
        row.dataset.index = row.querySelector('.tile').dataset.index = index;
        row.querySelectorAll('[data-edit-group="projects"]').forEach(el => el.dataset.editIndex = index);
      }
      refresh();
    }
  };
}
let running=false;
export async function start(api){
  if(running)return; running=true;
  const local=api==='/__editor';
  const css=document.createElement('link'); css.rel='stylesheet';css.href=new URL('owner.css',import.meta.url);document.head.append(css);
  let session=sessionStorage.getItem(S), model, version;
  const bar=node('aside','','owner-bar');bar.setAttribute('aria-label','소유자 메뉴');
  const status=node('span','','owner-status');status.setAttribute('role','status');
  async function call(path,payload={},key=session){
    let r;try{r=await fetch(api+path,{method:'POST',credentials:'omit',cache:'no-store',headers:{'Content-Type':'application/json',...(key?{Authorization:'Bearer '+key}:{})},body:JSON.stringify(payload)});}catch{throw Error('편집 API에 연결할 수 없습니다. 연결 상태와 API 주소를 확인하세요.');}
    const obj=await r.json().catch(()=>({})); if(!r.ok){if(r.status===401){sessionStorage.removeItem(S);session=null;}throw Error(obj.error||`편집 API 오류 (${r.status})`);}return obj;
  }
  async function login(){
    if(local){status.textContent='preview.cmd 실행 창에 표시된 소유자 주소로 다시 열어 주세요.';return;}
    const verifier=random(),state=random();
    const challenge=b64url(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(verifier))));
    const {url}=await call('/start',{challenge,state},null);
    sessionStorage.setItem(L,JSON.stringify({verifier,state,path:location.pathname,time:Date.now()}));location.assign(url);
  }
  const safeLogin=()=>login().catch(e=>status.textContent=e.message);
  const clean=()=>history.replaceState(null,'',location.pathname);
  try{
    const q=new URLSearchParams(location.search);
    if(local && location.hash.startsWith('#owner=')){
      const key=location.hash.slice(7);clean();({session}=await call('/local-login',{},key));sessionStorage.setItem(S,session);
    }else if(!local && (q.has('code')||q.has('error'))){
      const pending=JSON.parse(sessionStorage.getItem(L)||'null');sessionStorage.removeItem(L);clean();
      if(!pending||pending.state!==q.get('state')||Date.now()-pending.time>600000||!q.get('code'))throw Error('로그인이 취소되었거나 만료되었습니다. 다시 로그인하세요.');
      ({session}=await call('/session',{code:q.get('code'),verifier:pending.verifier},null));sessionStorage.setItem(S,session);
      if(/^\/projects\/[a-z0-9-]+\/(?:index\.html)?$/.test(pending.path)){location.replace(pending.path);return;}
    }
    if(!session)throw Error(local?'로컬 소유자 주소가 필요합니다.':'소유자 로그인 후 이 페이지에서 편집할 수 있습니다.');
    ({data:model,version}=await call('/read'));
  }catch(e){document.body.prepend(bar);bar.append(status);status.textContent=e.message;if(!local)bar.append(button('GitHub 로그인',safeLogin));return;}
  if(location.hash==='#edit')clean();
  document.body.prepend(bar);
  const chooser=node('select');chooser.setAttribute('aria-label','편집할 항목');
  for(const [k,[label]] of Object.entries(groups)){const o=node('option',label);o.value=k;chooser.append(o);}
  const modeKey='portfolio.owner.mode';
  let editing=sessionStorage.getItem(modeKey)!=='navigate';
  const toggle=button('',()=>{editing=!editing;sessionStorage.setItem(modeKey,editing?'edit':'navigate');applyMode();});
  bar.append(node('strong',local?'로컬 편집':'소유자 편집'),toggle,chooser,button('항목 관리',()=>browse(chooser.value)),button('편집 종료',async()=>{
    try{await call('/logout');}catch(e){status.textContent=e.message;return;}sessionStorage.removeItem(S);location.replace(location.pathname);
  }),status);
  const detailSlug=location.pathname.match(/\/projects\/([^/]+)\//)?.[1];
  const dialog=node('dialog','','owner-dialog');document.body.append(dialog);dialog.setAttribute('aria-label','콘텐츠 편집');
  let dirty=false,busy=false,objectUrls=[];
  function reset(){objectUrls.forEach(URL.revokeObjectURL);objectUrls=[];dirty=false;dialog.replaceChildren();if(!dialog.open)dialog.showModal();}
  function close(){if(!busy&&(!dirty||confirm('저장하지 않은 변경을 버릴까요?'))){dialog.close();dirty=false;objectUrls.forEach(URL.revokeObjectURL);objectUrls=[];}}
  dialog.addEventListener('cancel',e=>{e.preventDefault();close();});
  const shelves=document.querySelector('.shelf')?.closest('#projects');
  const order=shelves && setupOrder(shelves,bar,status,()=>editing&&!busy&&!dialog.open,saveOrder);
  window.addEventListener('beforeunload',e=>{if(dirty||order?.pending){e.preventDefault();e.returnValue='';}});
  const selector='[data-edit-group],[data-manage]';
  function applyMode(){
    toggle.textContent=editing?'편집 모드 · 탐색으로 전환':'탐색 모드 · 편집으로 전환';
    toggle.setAttribute('aria-pressed',String(editing));
    if(!editing)order?.cancel();
    document.body.classList.toggle('owner-editing',editing);
    document.querySelectorAll(selector).forEach(el=>{if(editing)el.tabIndex=0;else el.removeAttribute('tabindex');});
  }
  applyMode();
  function activate(event){
    if(!editing||busy||dialog.open||bar.contains(event.target)||event.target.closest('.drag-handle'))return;
    if(event.type==='keydown'&&!['Enter',' '].includes(event.key))return;
    const direct=event.target.closest(selector);
    const el=direct||event.target.closest('.tile')?.querySelector('h3 [data-edit-group]')||event.target.closest('a,button,summary')?.querySelector(`${selector.split(',')[0]}:not([hidden] *),[data-manage]`);
    if(!el)return;
    event.preventDefault();event.stopImmediatePropagation();
    if(el.dataset.manage){manage(el.dataset.manage);return;}
    const {editGroup:key,editIndex:index,editField:focus}=el.dataset;
    if(!Object.hasOwn(groups,key))return;
    const i=Number(index);
    if(!singleton(key)&&(!Number.isInteger(i)||i<0||i>=(model[key]?.length??0))){browse(key);return;}
    edit(key,i,focus);
  }
  document.addEventListener('click',activate,true);
  document.addEventListener('keydown',activate,true);
  function addRow(key,i){
    const row=model[key]?.[i];if(row==null)return;
    const line=node('div','','owner-row');line.append(node('span',typeof row==='string'?row:row.title||row.caption),button('편집',()=>edit(key,i)));dialog.append(line);
  }
  function browse(key){if(singleton(key)){edit(key,0);return;}reset();
    dialog.append(node('h2',groups[key][0]),button('새 항목 추가',()=>edit(key,-1)),button('닫기',close));
    (model[key]||[]).forEach((_,i)=>addRow(key,i));
  }
  function manage(key){
    if(key==='projects'||key==='credentials'){browse(key);return;}
    reset();
    if(key==='skillLists'){browse('skillGroups');return;}
    if(key==='legacySkillLists'){
      dialog.append(node('h2','스킬 관리'),button('닫기',close));
      for(const group of ['skills','otherSkills'])dialog.append(button(groups[group][0],()=>browse(group)));
      return;
    }
  }
  function edit(key,i,focus=''){reset();const single=singleton(key);let fields=groups[key][1];
    const initial=single?model[key]:(model[key]||[])[i];const draft=structuredClone(initial??(fields?{}:''));
    // Works outside the featured tiers have no detail page: the card shows a title and
    // a one-line description and opens a single link (the existing play link, else the source).
    const compact=key==='projects'&&i>=0&&!initial?.feature;
    if(compact){
      // Each filled link becomes its own button on the card: play first, then GitHub.
      const pick=k=>fields.find(f=>f.key===k);
      fields=[pick('title'),{...pick('category'),label:'설명'},{...pick('url'),label:'플레이 링크'},{...pick('source'),label:'GitHub 링크'}];
    }
    let scalar=draft,focusTarget;const pending=new Map();const form=node('form');const err=node('p','','owner-status');err.setAttribute('role','alert');
    dialog.append(node('h2',groups[key][0]+(i<0?' 추가':' 편집')),form);form.addEventListener('input',()=>dirty=true);
    function fieldset(parent,row,defs,prefix=''){for(const f of defs){
      if(f.type==='blocks'){
        row[f.key]??=[];const blocks=row[f.key],box=node('div','','owner-block');parent.append(node('h3',f.label),box);
        const addBlock=(block,j)=>{const set=node('fieldset');set.append(node('legend','상세 단락'));fieldset(set,block,sections,`sections.${j}.`);set.append(button('단락 삭제',()=>{if(confirm('이 단락을 뺄까요?')){blocks.splice(blocks.indexOf(block),1);set.remove();dirty=true;}}));box.append(set);};
        blocks.forEach(addBlock);parent.append(button('단락 추가',()=>{const b={};blocks.push(b);addBlock(b,blocks.length-1);dirty=true;}));continue;
      }
      const label=node('label',f.label+(f.required?' *':''));parent.append(label);
      if(f.type==='image'){
        const pic=node('img');pic.alt='선택한 사진 미리보기';pic.hidden=!row[f.key];if(row[f.key])pic.src=row[f.key];
        const input=node('input');input.type='file';input.accept='image/jpeg,image/png,image/webp';label.append(input,pic);
        if(prefix+f.key===focus)focusTarget=input;
        input.onchange=()=>{const file=input.files[0];if(!file)return;
          const ext={'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[file.type];if(!ext||file.size>2097152){err.textContent='2MB 이하의 PNG, JPEG, WebP를 선택하세요.';input.value='';return;}
          const path='/media/pic-'+crypto.randomUUID()+'.'+ext;pending.set(path,file);row[f.key]=path;
          const url=URL.createObjectURL(file);objectUrls.push(url);pic.src=url;pic.hidden=false;dirty=true;err.textContent='';};
        parent.append(button('사진 빼기',()=>{delete row[f.key];pic.removeAttribute('src');pic.hidden=true;input.value='';dirty=true;}));continue;
      }
      if(f.type==='choice'){
        const input=node('select');
        for(const [value,name] of f.options){const option=node('option',name);option.value=value;input.append(option);}
        input.value=row[f.key]??'';
        if(input.value==='')delete row[f.key];
        input.onchange=()=>{if(input.value)row[f.key]=input.value;else delete row[f.key];dirty=true;};
        if(prefix+f.key===focus)focusTarget=input;
        label.append(input);continue;
      }
      const input=node(f.type==='long'?'textarea':'input');input.required=f.required;input.value=row[f.key]??'';
      if(key==='labels'){input.placeholder=f.label;if(f.key===focus&&!input.value)input.value=f.label;}
      if(f.type==='url'||f.type==='video')input.type='url';if(f.type==='slug')input.pattern='[a-z0-9]+(-[a-z0-9]+)*';
      if(prefix+f.key===focus)focusTarget=input;
      input.oninput=()=>row[f.key]=input.value;label.append(input);
    }}
    if(fields)fieldset(form,draft,fields);else{const l=node('label','스킬 이름 *');const t=node('input');t.value=scalar;t.required=true;t.oninput=()=>scalar=t.value;l.append(t);form.append(l);focusTarget=t;}
    const controls=node('div','','owner-controls');const submit=node('button',local?'내 PC에 저장':'저장 및 게시','owner-btn');submit.type='submit';controls.append(submit,button('취소',close));
    if(!single&&i>=0)controls.append(button('항목 삭제',()=>{if(confirm('이 항목을 삭제하고 저장할까요?'))persist(true);}));
    form.append(controls,err);form.onsubmit=e=>{e.preventDefault();persist(false);};
    (focusTarget||form.querySelector('input,textarea'))?.focus();
    async function persist(remove){if(busy)return;
      if(order?.pending){err.textContent='순서 변경이 대기 중입니다. 편집 창을 닫고 순서를 저장하거나 되돌린 뒤 편집하세요.';return;}
      busy=true;form.inert=true;err.textContent='저장 중…';
      try{const next=structuredClone(model);if(single)next[key]=draft;else{const rows=next[key]??=[];if(remove)rows.splice(i,1);else if(i<0)rows.push(fields?draft:scalar.trim());else rows[i]=fields?draft:scalar.trim();}
        await saveModel(next,pending,()=>{dirty=false;busy=false;close();});
      }catch(e){err.textContent=e.message;}finally{busy=false;form.inert=false;}
    }
  }
  async function saveOrder(){
    if(busy||dialog.open||!order.pending)return;
    busy=true;bar.inert=true;status.textContent='순서 저장 중…';
    try{
      const next=structuredClone(model);
      order.arrange(next);
      await saveModel(next,[],()=>order.committed(next.projects));
    }catch(e){status.textContent=e.message;}finally{busy=false;bar.inert=false;}
  }
  async function saveModel(next,pending,committed){
    const refs=validate(next),uploads=[];let total=0;
    for(const [path,file] of pending){if(!refs.has(path))continue;total+=file.size;if(total>5*1024*1024)throw Error('한 번에 올리는 사진은 총 5MB 이하로 선택하세요.');
      const content=await new Promise((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(r.result.split(',')[1]);r.onerror=()=>reject(Error('사진 읽기 실패'));r.readAsDataURL(file);});uploads.push({path,content});}
    const saved=await call('/save',{version,data:next,uploads});version=saved.version;model=next;committed();
    if(local){const target=detailSlug && !model.projects?.some(p=>p.slug===detailSlug&&p.feature)?'/':location.pathname+location.hash;location.replace(target);if(target===location.pathname+location.hash)location.reload();}
    else status.textContent='GitHub에 저장했습니다. 배포가 끝난 뒤 새로고침하면 공개 화면에 반영됩니다.';
  }
}
