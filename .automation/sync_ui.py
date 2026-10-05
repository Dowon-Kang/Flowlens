"""One-time reviewed source update. Abort on any unexpected file hash.
No target-repository files or instructions are executed by this publisher.
"""
from pathlib import Path
import hashlib
EDITS = [
('static/app.js', '4f3023d36b6cb4735adcdd7621f3b30ab868bceca18064fc8c4310ba460b6fd8', 'ac3327f9ad074624a2a1812fabdedc1252e7d0bd6c5721e0bd9c64fb6ca52285', [
(2,3, r'''const state = { detail: 'steps', flow: null, trail: [], allSteps: false, data: null, mode: 'system', feature: null, selected: null, page: 'explorer', busy: false, zoom: 1, pan: {x:0,y:0}, layout: null, toastTimer: null };
'''),
(18,19, r'''    resetProcess(); state.data=data; state.feature=null; state.selected=null; state.mode='system'; state.zoom=1; state.pan={x:0,y:0};
'''),
(37,38, r'''    resetProcess(); state.data=data; state.feature=null; state.selected=null; state.mode='system'; state.zoom=1; state.pan={x:0,y:0};
'''),
(47,49, r'''function showFeature(id) { resetProcess();state.feature=id;state.flow=currentFeature()?.flow_ids?.[0]||null; state.mode='feature'; state.selected=null; state.page='explorer'; state.zoom=1; state.pan={x:0,y:0}; render(); }
function showSystem() { resetProcess();state.mode='system';state.feature=null;state.selected=null;state.page='explorer';state.zoom=1;state.pan={x:0,y:0};render(); }
'''),
(51,51, r'''  if(state.mode==='feature' && feature && state.detail==='steps' && currentFlow())return processGraph(currentFlow());
'''),
(58,59, r'''  $('topRepo').textContent=d.name;document.querySelector('.version').textContent='v'+d.analyzer_version;
'''),
(79,79, r'''  renderProcessTools();
  if(feature&&state.detail==='steps'){
    const flow=currentFlow();
    $('canvasTitle').textContent=flow?`${feature.label} → ${flow.kind==='function'?flow.label:'핵심 처리 단계'}`:'지원되지 않는 본문';
    $('canvasSubtitle').textContent='소스 읽기 순서 · 조건/예외 포함 · 실행 관측 아님';
    $('viewMeta').textContent=flow?`${graphData().nodes.length}개 요약 / ${flow.steps.length}개 단계`:'본문 범위 미확인';
    if(state.trail.length)$('featureContext').innerHTML+='<button class="context-chip" data-flow-back>← 상위 처리로</button>';
  }
  document.querySelector('.graph-legend').innerHTML=feature&&state.detail==='steps'?'<span><i class="legend-line dashed"></i>소스 읽기 순서 · 실행 보증 아님</span>':'<span><i class="legend-line"></i>정적 관계</span><span><i class="legend-line dashed"></i>연결 후보</span>';
'''),
(95,95, r'''  }
  if(state.detail==='steps'&&currentFlow()){
    nodes.forEach((n,i)=>{const row=Math.floor(i/2),col=row%2===0?i%2:1-i%2;positions.set(n.id,{x:40+col*372,y:76+row*148,w:320,h:108});});
    return {positions,w:780,h:Math.max(600,190+Math.ceil(nodes.length/2)*148)};
'''),
(128,128, r'''  if(node.kind==='process'){
    const chosen=state.selected?.id===node.id;
    const label=truncate(node.label,23);
    return `<g class="svg-node" data-node="${esc(node.id)}" tabindex="0" role="button" aria-label="${esc(node.label)} 근거 보기" transform="translate(${p.x},${p.y})"><title>${esc(node.description)}</title><rect class="node-box" width="${p.w}" height="${p.h}" rx="13" fill="${chosen?'#f4f0ff':'#fff'}" stroke="${chosen?'#7865d3':'#ddd9e9'}" filter="url(#node-shadow)"/><text x="17" y="25" font-size="12" fill="#776798" font-family="system-ui">${String(node.index).padStart(2,'0')} · ${node.steps.length>1?'요약 묶음':'처리 단계'}</text>${node.conditional?`<text x="${p.w-18}" y="25" text-anchor="end" font-size="10" fill="#9a753e" font-family="system-ui">조건/분기 포함</text>`:''}<text x="17" y="56" font-size="18" font-weight="600" fill="#332c45" font-family="system-ui">${esc(label)}</text><text x="17" y="80" font-size="11" fill="#787084" font-family="system-ui">${esc(node.description)} · 눌러서 근거 보기</text></g>`;
  }
'''),
(156,157, r'''  else if(Math.abs(a.y-b.y)<20){ax=b.x>a.x?a.x+a.w:a.x;ay=a.y+a.h*.54;bx=b.x>a.x?b.x:b.x+b.w;by=b.y+b.h*.54;path=`M${ax},${ay} C${ax+25},${ay+44} ${bx-25},${by+44} ${bx},${by}`;lx=(ax+bx)/2;ly=ay+33;}
'''),
(158,159, r'''  let label=({import:'import',sdk:'SDK', 'http-contract':'HTTP · 후보','http-url':'HTTP','entry-model':'요청 · 설명용','source-order':'읽기 순서','config-url':'기본 URL · 후보'})[edge.relation] || edge.relation;
'''),
(171,172, r'''function featureCards(features){return features.map(f=>`<button class="feature-card" data-feature="${esc(f.id)}"><div class="card-top">${esc(f.label)}<span>↗</span></div><code>${esc(f.endpoint_labels[0]||'API')}</code><small>${f.flow_ids?.length||0}개 처리 흐름 · ${f.node_ids.length}개 관련 파일/서비스</small></button>`).join('');}
'''),
(176,176, r'''  if(feature&&state.detail==='steps')return renderProcessPanel();
'''),
(208,209, r'''    const md=`# ${d.name}\n\n${d.summary}\n\nRevision: ${d.revision}\nAnalyzer: ${d.analyzer_version}\nMode: ${state.mode}\n\n> Static relationships are not proof of runtime execution. Processing-view edges mean source reading order, not a proven execution path. Branches and early returns may skip later steps. Other dashed edges are candidates.\n\n\`\`\`mermaid\n${diagram}\n\`\`\`\n\n## Coverage\n\n${d.coverage.analyzed} of ${d.coverage.eligible} eligible files read. ${d.coverage.omitted} omitted, ${d.coverage.failed} failed.\n\n## Limitations\n\n${d.warnings.map(w=>'- '+w).join('\n')}\n\n## Source evidence\n\n${d.evidence.map(e=>'- '+e.path.replace(/[\n\r`]/g,' ')+' : L'+e.line+'–L'+e.end_line+' ('+e.kind+', '+e.parser+')').join('\n')}\n`;
'''),
(238,238, r'''  const detail=event.target.closest('[data-detail]');if(detail){state.detail=detail.dataset.detail;state.selected=null;state.zoom=1;state.pan={x:0,y:0};render();return;}
  const callee=event.target.closest('[data-callee]');if(callee)return chooseFlow(callee.dataset.callee,true);
  const back=event.target.closest('[data-flow-back]');if(back){const id=state.trail.pop();if(id){state.flow=id;state.allSteps=false;state.selected=null;render();}return;}
  const step=event.target.closest('[data-step]');if(step){state.selected={type:'node',id:step.dataset.step};renderGraph();renderPanel();$('detailPanel').scrollTop=0;return;}
  if(event.target.closest('[data-toggle-steps]')){state.allSteps=!state.allSteps;state.selected=null;state.zoom=1;render();return;}

'''),
(267,267, r'''// Scope-based processing view. Visual groups only fold contiguous source steps.
function currentFlow(){return state.data?.flows?.find(f=>f.id===state.flow);}
function resetProcess(){state.detail='steps';state.flow=null;state.trail=[];state.allSteps=false;}
function chooseFlow(id,fromCall=false){
  if(fromCall&&state.flow)state.trail.push(state.flow);
  else if(!fromCall)state.trail=[];
  state.flow=id;state.detail='steps';state.selected=null;state.allSteps=false;state.zoom=1;state.pan={x:0,y:0};render();
}
function stepGroups(flow){
  let groups=flow.steps.map(step=>[step]);
  if(state.allSteps)return groups;
  const cost=(a,b)=>{
    const cats=new Set([...a,...b].map(s=>s.category));
    if(cats.size===1)return 0;
    if(cats.has('response'))return 50+a.length+b.length;
    if(cats.has('recommend')||cats.has('safety'))return 30+a.length+b.length;
    if(cats.has('validate')&&(cats.has('read')||cats.has('rules')||cats.has('calculate')))return 1+cats.size+a.length+b.length;
    return 10+cats.size+a.length+b.length;
  };
  while(groups.length>8){let i=0;for(let j=1;j<groups.length-1;j++)if(cost(groups[j],groups[j+1])<cost(groups[i],groups[i+1]))i=j;groups.splice(i,2,[...groups[i],...groups[i+1]]);}
  return groups;
}
function groupLabel(group){
  const kinds=new Set(group.map(s=>s.category));
  if(kinds.size===1)return group[0].label;
  const words={auth:'인증',validate:'검증',read:'조회',rules:'규칙',normalize:'정규화',calculate:'계산',recommend:'추천 계산',classify:'등급',safety:'안전 확인',adjust:'계수 조정',write:'저장',network:'외부 요청',token:'허가',response:'결과 반환',prepare:'준비',select:'설정'};
  return [...kinds].map(k=>words[k]||k).join(' · ');
}
function processGraph(flow){
  const file=state.data.nodes.find(n=>n.path===flow.path);
  const groups=stepGroups(flow);
  const nodes=groups.map((steps,i)=>({id:'view-'+steps[0].id,label:groupLabel(steps),kind:'process',role:'process',component_id:file?.component_id||'',path:flow.path,steps,
    description:`L${steps[0].line}–${steps.at(-1).end_line} · ${steps.length}개 세부 단계`,
    evidence_ids:[...new Set(steps.flatMap(s=>s.evidence_ids))],member_ids:[],tags:[],index:i+1,
    conditional:steps.some(s=>s.conditional)}));
  const edges=nodes.slice(1).map((n,i)=>({id:'reading-'+n.id,source:nodes[i].id,target:n.id,relation:'source-order',confidence:'candidate',evidence_ids:[nodes[i].evidence_ids[0],n.evidence_ids[0]],description:'소스에 적힌 순서로 읽기 위한 연결입니다. 실행·성공 경로가 아닙니다. 분기, 반복, 예외 또는 조기 반환으로 이후 단계는 실행되지 않을 수 있습니다.'}));
  return {nodes,edges};
}
function renderProcessTools(){
  const el=$('processTools'),f=currentFeature(),flow=currentFlow();
  el.classList.toggle('hidden',!f);
  if(!f)return;
  const variants=(f.flow_ids||[]).map(id=>state.data.flows.find(x=>x.id===id)).filter(Boolean);
  el.innerHTML=`<div class="process-modes"><button data-detail="steps" class="${state.detail==='steps'?'active':''}">처리 단계</button><button data-detail="files" class="${state.detail==='files'?'active':''}">파일 참고도</button></div>${variants.length?`<label class="variant-label">진입점 <select id="flowVariant" aria-label="기능 진입점">${variants.map(v=>`<option value="${esc(v.id)}" ${v.id===(state.trail[0]||state.flow)?'selected':''}>${esc(v.label)}</option>`).join('')}</select></label>`:''}${state.detail==='steps'&&flow?`<button class="button subtle compact" data-toggle-steps>${state.allSteps?'핵심만 접어 보기':`전체 ${flow.steps.length}단계 보기`}</button>`:''}`;
  $('flowVariant')?.addEventListener('change',e=>chooseFlow(e.target.value));
}
function renderProcessPanel(){
  const flow=currentFlow(),feature=currentFeature(),panel=$('detailPanel');
  if(!flow){panel.innerHTML='<h3>본문 범위 미확인</h3><p class="panel-description">처리 단계를 만들지 않았습니다. 파일 참고도에서 원본 근거를 확인하세요.</p><button data-detail="files" class="button">파일 참고도</button>';return;}
  const selected=graphData().nodes.find(n=>n.id===state.selected?.id);
  if(state.selected?.type==='edge'){
    const edge=graphData().edges.find(e=>e.id===state.selected.id);
    panel.innerHTML=`<button class="panel-back" data-action="clear">← 처리 요약</button><div class="panel-eyebrow">READING ORDER · 실행 경로 아님</div><h3>소스 순서 연결</h3><p class="panel-description">${esc(edge?.description)}</p>${evidenceHtml(edge?.evidence_ids||[])}`;return;
  }
  if(selected){
    const targets=[...new Set(selected.steps.flatMap(s=>s.calls.map(c=>c.callee_id)).filter(Boolean))].map(id=>state.data.flows.find(f=>f.id===id)).filter(Boolean);
    panel.innerHTML=`<button class="panel-back" data-action="clear">← 처리 요약</button><div class="panel-eyebrow">PROCESS EVIDENCE</div><h3>${esc(selected.label)}</h3><span class="confidence-pill candidate">규칙 기반 요약 · 실행 미검증</span><p class="panel-description">${esc(flow.label)}<br>${esc(flow.path)}<br>${esc(selected.description)}</p>${targets.length?`<div class="panel-eyebrow">호출 대상 내부 펼치기 · 정적 후보</div>${targets.map(t=>`<button class="feature-card" data-callee="${esc(t.id)}"><div class="card-top">${esc(t.label)}<span>↘</span></div><small>${esc(t.path)} · L${t.line}</small></button>`).join('')}`:''}<div class="panel-divider"></div>${selected.steps.map(s=>`<section class="step-detail"><h4>${esc(s.label)} <small>L${s.line}–${s.end_line}</small></h4>${s.conditional?'<div class="branch-note">조건·반복·콜백 또는 조기 반환이 포함될 수 있습니다.</div>':''}${evidenceHtml(s.evidence_ids)}<details class="calls-list"><summary>소스에서 찾은 호출 ${s.calls.length}개</summary>${s.calls.map(c=>`<div><code>${esc(c.name)}</code><small>${c.callee_id?'정적 연결 후보':'대상 미해결 / 외부 호출'}</small></div>`).join('')}</details></section>`).join('')}`;
  }else{
    panel.innerHTML=`<div class="panel-eyebrow">FEATURE → PROCESS → CODE</div><h3>${esc(feature.label)}</h3><p class="panel-description">현재: <strong>${esc(flow.label)}</strong><br>이 본문에서 발견한 처리를 요약했습니다. 단계 클릭 → 근거 확인 → 연결 가능한 함수 내부 순으로 탐색하세요.</p><div class="scope-box"><code>${esc(flow.path)}</code><span>L${flow.line}–${flow.end_line} · ${flow.steps.length}개 세부 단계</span></div><div class="confidence-note warn">화살표는 <strong>소스 읽기 순서</strong>입니다. 분기·오류·조기 반환으로 실제 실행 경로는 달라집니다.</div>${state.trail.length?'<button class="button" data-flow-back>← 상위 처리로 돌아가기</button>':''}<div class="panel-divider"></div><div class="panel-eyebrow">단계 바로가기</div>${graphData().nodes.map(n=>`<button class="process-shortcut" data-step="${esc(n.id)}"><b>${String(n.index).padStart(2,'0')}</b><span>${esc(n.label)}</span><small>${n.conditional?'분기 포함':'코드 근거'}</small></button>`).join('')}<div class="panel-divider"></div><ul class="warning-list">${flow.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul><button class="button subtle" data-detail="files">파일·HTTP 관계는 별도 참고도에서 →</button>`;
  }
}

'''),
]),
('static/index.html', 'fc6da147fb21d5aefc7239fc441874a95eaeb11a026a73c8b74d0516a877435b', 'd3ad893685b5d620176386fed6c5ff3b8ed9659ba9bc7c73bff801489e348349', [
(13,14, r'''    <div class="workspace-label"><span class="tiny-dot"></span> LOCAL WORKSPACE <span class="version">v0.3</span></div>
'''),
(44,44, r'''        <div id="processTools" class="process-tools hidden"></div>
'''),
(59,60, r'''  <dialog id="helpDialog"><button id="closeHelp" class="close-dialog" aria-label="안내 닫기">×</button><div class="eyebrow">HOW TO EXPLORE</div><h2>큰 그림을 먼저.<br>근거는 바로 옆에.</h2><div class="help-step"><b>01</b><div><strong>System Flow</strong><p>기술·역할에 따라 파일을 묶습니다. 화면, 상태 관리, 서비스, 백엔드, 외부 연동을 한 장에서 봅니다.</p></div></div><div class="help-step"><b>02</b><div><strong>Feature Flow</strong><p>기능을 선택하면 API별 본문의 처리 단계를 먼저 보여줍니다. 파일 참고도는 별도로 펼칠 수 있습니다. 상단에서 전체 구조 안의 위치를 확인할 수 있습니다.</p></div></div><div class="help-step"><b>03</b><div><strong>Evidence</strong><p>노드나 화살표를 선택해 근거 파일·줄·함수를 봅니다. 실선은 정적 패턴, 점선은 연결 후보이며 실제 실행을 관측한 결과는 아닙니다.</p></div></div><div class="help-note">이 MVP는 Python AST와 제한된 JS/TS/Dart 패턴을 지원합니다. 공개 GitHub URL, 로컬 폴더, ZIP 파일을 읽을 수 있으며 분석 범위를 공개합니다. 대규모 프로젝트, 동적 호출, 복잡한 라우팅은 추가 확인이 필요합니다.</div><p class="help-privacy">AI 설명을 선택하면 일부 코드 근거가 OpenAI로 전송됩니다. 비밀 값은 먼저 제거하세요. 설정되지 않은 키는 브라우저에서 요구하거나 저장하지 않습니다.</p></dialog>
'''),
]),
('static/styles.css', '3295037879a0f86e3765d2232dacf1c37bc568840e069ed42edc7c2f6c5cd8ec', '9454af42c1376c23ef32db32bfd45736198f8a9ba9c501e1e3e47f55285c4d06', [
(11,11, r'''
.process-tools{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:10px 20px;border-bottom:1px solid var(--line);background:#fff}.process-modes{display:flex;background:#f3f1fa;border-radius:7px;padding:3px}.process-modes button{border:0;background:transparent;color:#847895;border-radius:5px;font-size:11px;padding:7px 10px}.process-modes button.active{background:#fff;color:#5841ac;box-shadow:0 1px 4px #44335515}.variant-label{display:flex;align-items:center;gap:8px;font-size:10px;color:#81728f;min-width:0}.variant-label select{max-width:380px;min-width:0;border:1px solid #e2ddeb;background:#fff;border-radius:6px;color:#594c71;padding:7px;font-size:11px}.scope-box{border:1px solid #e3dced;background:#faf8ff;padding:12px;border-radius:8px;margin:12px 0;overflow-wrap:anywhere}.scope-box code{font-size:10px;display:block;line-height:1.8}.scope-box span{font-size:11px;color:#82738b;display:block;margin-top:6px}.process-shortcut{display:flex;gap:8px;align-items:center;background:#fff;border:1px solid #ebe7f3;border-radius:7px;padding:10px;width:100%;margin:7px 0;text-align:left;font-size:11px;color:#534362}.process-shortcut b{color:#9a86bc;font-size:10px}.process-shortcut span{flex:1}.process-shortcut small{font-size:9px;color:#9c8ba9}.step-detail{padding:9px 0;border-top:1px solid #eee9f4}.step-detail h4{font-size:13px;color:#544162;margin:9px 0}.step-detail h4 small{font-size:10px;color:#9a8ca6;font-weight:400}.branch-note{font-size:10px;background:#fff6e7;color:#8e7449;padding:8px;border-radius:6px;margin:8px 0}.calls-list{font-size:10px;color:#86748f;margin:12px 0}.calls-list summary{cursor:pointer;padding:8px 0}.calls-list div{padding:6px 0;overflow-wrap:anywhere}.calls-list small{display:block;color:#aa9bb3;font-size:9px}.feature-card small{overflow-wrap:anywhere}.canvas-heading{pointer-events:none}.feature-nav{max-height:36vh}.process-tools~.workspace-grid .canvas-area{min-height:600px}.process-tools~.workspace-grid .detail-panel{min-height:600px}
@media(max-width:740px){.process-tools{padding:10px;gap:7px}.variant-label{flex-basis:100%}.variant-label select{max-width:100%;width:100%}.process-tools~.workspace-grid .canvas-area{min-height:600px}.process-tools~.workspace-grid .detail-panel{min-height:0}.view-meta{max-width:100px;text-align:right}.canvas-heading>div{max-width:260px;font-size:12px}.canvas-heading>span{max-width:240px;display:block;line-height:1.7}}
'''),
]),

]
staged={}
for name,before,after,edits in EDITS:
    path=Path(name);raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()==after:continue
    assert hashlib.sha256(raw).hexdigest()==before, 'Unexpected source: '+name
    lines=raw.decode('utf-8').splitlines(keepends=True)
    for start,end,value in reversed(edits):lines[start:end]=[value]
    result=''.join(lines).encode('utf-8')
    assert hashlib.sha256(result).hexdigest()==after, 'Edited content mismatch: '+name
    staged[path]=result
for path,result in staged.items():path.write_bytes(result)
print('Applied',len(staged),'checksum-verified source changes')
