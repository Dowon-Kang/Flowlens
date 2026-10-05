const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = { data: null, mode: 'system', feature: null, selected: null, page: 'explorer', busy: false, zoom: 1, pan: {x:0,y:0}, layout: null, toastTimer: null };
const roleLabels = {user:'ENTRY POINT',app:'PRESENTATION',state:'STATE & CONTROL',transport:'NETWORK LAYER',backend:'APPLICATION',modules:'MODULES',infrastructure:'INFRASTRUCTURE'};
const roleIcons = {user:'U',app:'UI',state:'ST',transport:'IO',backend:'API',modules:'M',infrastructure:'EXT'};
const order = {user:0,app:1,state:2,transport:3,backend:4,modules:5,infrastructure:6};
const truncate = (s, n=35) => String(s).length > n ? String(s).slice(0,n-1)+'…' : String(s);
const toast = (text) => { clearTimeout(state.toastTimer); $('toast').textContent=text; $('toast').classList.remove('hidden'); state.toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),3500); };
function notice(text='', error=false) { $('notice').textContent=text; $('notice').classList.toggle('hidden',!text); $('notice').classList.toggle('error',error); }
function setBusy(busy) { state.busy=busy; document.body.classList.toggle('busy',busy); $('loading').classList.toggle('hidden',!busy); document.querySelectorAll('[data-demo],#analyzeButton,#folderButton,#zipButton').forEach(b=>b.disabled=busy); }

async function analyze(payload) {
  if(state.busy) return;
  setBusy(true); notice();
  try {
    const response=await fetch('/api/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...payload,explain:$('explainToggle').checked}),signal:AbortSignal.timeout(150000)});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || `분석 실패 (HTTP ${response.status})`);
    state.data=data; state.feature=null; state.selected=null; state.mode='system'; state.zoom=1; state.pan={x:0,y:0};
    document.querySelectorAll('[data-demo]').forEach(b=>b.classList.toggle('selected',payload.source==='demo' && b.dataset.demo===(payload.demo || 'mobile')));
    state.page='explorer'; render();
    if(data.coverage.partial) notice(`부분 분석: 지원 후보 ${data.coverage.eligible}개 중 ${data.coverage.analyzed}개 파일을 읽었습니다. 생략 ${data.coverage.omitted}개, 실패 ${data.coverage.failed}개. 분석 과정에서 전체 범위를 확인하세요.`);
    else if(payload.source==='files' && payload.clientSkipped) notice(`브라우저에서 ${payload.clientSkipped}개 파일을 보안·크기·지원 형식 기준으로 제외했습니다. 서버 통계는 전달된 파일만 포함합니다.`);
  } catch(error) {
    notice(error.name==='TimeoutError' ? '분석 요청이 시간 제한을 초과했습니다. 더 작은 폴더로 시도해 주세요.' : error.message,true);
  } finally { setBusy(false); }
}


async function analyzeZip(file) {
  if(state.busy) return;
  setBusy(true); notice();
  try {
    const params=new URLSearchParams({filename:file.name,explain:String($('explainToggle').checked)});
    const response=await fetch('/api/analyze-zip?'+params.toString(),{method:'POST',headers:{'Content-Type':file.type||'application/zip'},body:file,signal:AbortSignal.timeout(150000)});
    const data=await response.json();
    if(!response.ok) throw new Error(data.error || `ZIP 분석 실패 (HTTP ${response.status})`);
    state.data=data; state.feature=null; state.selected=null; state.mode='system'; state.zoom=1; state.pan={x:0,y:0};
    document.querySelectorAll('[data-demo]').forEach(b=>b.classList.remove('selected'));
    state.page='explorer'; render();
    if(data.coverage.partial) notice(`부분 분석: ZIP 내부 ${data.coverage.discovered}개 파일 중 지원 후보 ${data.coverage.eligible}개, 실제 분석 ${data.coverage.analyzed}개입니다.`);
  } catch(error) {
    notice(error.name==='TimeoutError' ? 'ZIP 분석 요청이 시간 제한을 초과했습니다.' : error.message,true);
  } finally { setBusy(false); }
}

function currentFeature() { return state.data?.features.find(f=>f.id===state.feature); }
function showFeature(id) { state.feature=id; state.mode='feature'; state.selected=null; state.page='explorer'; state.zoom=1; state.pan={x:0,y:0}; render(); }
function showSystem() { state.mode='system';state.feature=null;state.selected=null;state.page='explorer';state.zoom=1;state.pan={x:0,y:0};render(); }
function graphData() {
  const d=state.data; const feature=currentFeature();
  if(state.mode==='feature' && feature) return {nodes:d.nodes.filter(n=>feature.node_ids.includes(n.id)),edges:d.edges.filter(e=>feature.edge_ids.includes(e.id))};
  return {nodes:d.system_nodes,edges:d.system_edges};
}

function render() {
  if(!state.data) return;
  const d=state.data, feature=currentFeature();
  $('topRepo').textContent=d.name;
  $('repoName').textContent=d.name;
  $('revision').textContent='#'+d.revision.slice(0,8);
  $('revision').title=d.revision;
  $('sourceBadge').textContent=({demo:'합성 예제',github:'GitHub · public',files:'Local files',zip:'ZIP archive'})[d.source] || d.source;
  $('featureCount').textContent=d.features.length;
  $('sidebarFeatures').innerHTML=d.features.map(f=>`<button class="feature-link ${f.id===state.feature?'active':''}" data-feature="${esc(f.id)}"><span></span>${esc(f.label)}</button>`).join('') || '<p class="demo-note">인식된 API 기능이 없습니다.</p>';
  $('systemTab').classList.toggle('active',state.mode==='system');
  $('featureTab').classList.toggle('active',state.mode==='feature');
  $('viewMeta').textContent=feature ? `${feature.node_ids.length}개 관련 노드` : `${d.system_nodes.filter(n=>n.kind!=='virtual').length}개 핵심 영역`;
  $('canvasTitle').textContent=feature ? `${feature.label} · 기능별 흐름` : '프로젝트 전체 실행 경로';
  $('canvasSubtitle').textContent=feature ? '파일 의존성 · HTTP 연결 후보 / 호출 순서 미검증' : '기술 계층으로 압축 · 노드를 눌러 근거 확인';
  $('featureContext').classList.toggle('hidden',!feature);
  if(feature) $('featureContext').innerHTML=`<button class="context-back" data-action="system">← 전체 구조</button><span>이 기능의 상위 소속</span>${d.system_nodes.filter(n=>feature.component_ids.includes(n.id)).map(n=>`<button class="context-chip" data-system-node="${esc(n.id)}">${esc(n.label)}</button>`).join('')}`;
  $('explorerView').classList.toggle('hidden',state.page!=='explorer');
  $('pipelineView').classList.toggle('hidden',state.page!=='pipeline');
  $('exploreNav').classList.toggle('active',state.page==='explorer');
  $('pipelineNav').classList.toggle('active',state.page==='pipeline');
  $('validationStatus').textContent='구조·근거 일관성 검사 통과 · 런타임 미검증';
  $('coverageStatus').textContent=`${d.coverage.analyzed} files  /  ${d.evidence.length} evidence  /  ${d.coverage.partial?'부분 분석':'수집 범위 분석'}`;
  $('modePill').innerHTML=`<i></i> ${d.explanation?'AI-ASSISTED EXPLANATION':'STATIC ANALYSIS'}`;
  renderGraph(); renderPanel(); renderPipeline();
}

function calculateLayout(nodes, edges) {
  const positions=new Map();
  if(state.mode==='system') {
    const main=nodes.filter(n=>n.role!=='infrastructure');
    const infrastructure=nodes.filter(n=>n.role==='infrastructure');
    let y=90;
    for(const n of main) {
      const h=n.kind==='virtual'?66:n.tags.length?140:108;
      positions.set(n.id,{x:102,y,w:258,h}); y+=h+43;
    }
    const sideStart=Math.max(240, y-110-infrastructure.length*160);
    infrastructure.forEach((n,i)=>positions.set(n.id,{x:520,y:sideStart+i*180,w:258,h:108}));
    return {positions,w:885,h:Math.max(y+35,sideStart+infrastructure.length*180+90,600)};
  }
  // File-level layout. Layering is visual organization, not a claimed call sequence.
  const rank=new Map(nodes.map(n=>[n.id,({app:0,state:1,transport:2,backend:3,modules:3,infrastructure:6})[n.role]??3]));
  const byId=new Map(nodes.map(n=>[n.id,n]));
  const backend=nodes.filter(n=>['backend','modules'].includes(n.role));
  const internal=edges.filter(e=>['backend','modules'].includes(byId.get(e.source)?.role) && ['backend','modules'].includes(byId.get(e.target)?.role));
  const indegree=new Map(backend.map(n=>[n.id,internal.filter(e=>e.target===n.id).length]));
  const queue=backend.filter(n=>indegree.get(n.id)===0).map(n=>n.id);
  const processed=new Set();
  while(queue.length) {
    const id=queue.shift(); if(processed.has(id)) continue;processed.add(id);
    for(const e of internal.filter(e=>e.source===id)) {
      rank.set(e.target,Math.min(5,Math.max(rank.get(e.target),rank.get(id)+1)));
      indegree.set(e.target,indegree.get(e.target)-1); if(indegree.get(e.target)===0) queue.push(e.target);
    }
  }
  const groups=new Map();
  for(const n of nodes) {const r=rank.get(n.id);if(!groups.has(r))groups.set(r,[]);groups.get(r).push(n);}
  const rows=[...groups.entries()].sort((a,b)=>a[0]-b[0]);
  const maxCols=Math.max(...rows.map(([,row])=>Math.min(4,row.length)),1);
  const w=Math.max(780,maxCols*252+130);let y=95;
  for(const [,row] of rows) {
    const sorted=row.sort((a,b)=>a.label.localeCompare(b.label));
    for(let start=0;start<sorted.length;start+=4) {
      const slice=sorted.slice(start,start+4), rowWidth=slice.length*230+(slice.length-1)*24;
      slice.forEach((n,i)=>positions.set(n.id,{x:(w-rowWidth)/2+i*254,y,w:230,h:92}));
      y+=139;
    }
  }
  return {positions,w,h:Math.max(y+55,600)};
}

function nodeSvg(node, p) {
  const chosen=state.selected?.type==='node' && state.selected.id===node.id;
  const infra=node.role==='infrastructure', virtual=node.kind==='virtual';
  const border=chosen?'#8a79df':infra?'#d7e5df':'#e0ddec';
  const bg=chosen?'#faf7ff':infra?'#fbfdfb':'#ffffff';
  const iconBg=infra?'#edf5f1':'#f0ebfa';const iconColor=infra?'#91ad9d':'#9b8abc';
  const shadow=chosen?'filter="url(#selected-shadow)"':'filter="url(#node-shadow)"';
  const role=roleLabels[node.role] || node.role;
  const label=truncate(node.label,state.mode==='feature'?23:30);
  const description=state.mode==='feature' ? (state.data.system_nodes.find(n=>n.id===node.component_id)?.label || node.description) : node.description;
  if(virtual) return `<g class="svg-node" data-node="${esc(node.id)}" tabindex="0" role="button" aria-label="${esc(node.label)}" transform="translate(${p.x},${p.y})"><rect class="node-box" width="${p.w}" height="${p.h}" rx="13" fill="#f5f3fa" stroke="${border}" stroke-dasharray="4 4"/><circle cx="31" cy="33" r="14" fill="#e8e2f1"/><text x="31" y="37" text-anchor="middle" font-size="12" fill="#9a8aac" font-family="system-ui">U</text><text x="58" y="30" font-size="15" fill="#81718f" font-family="system-ui" font-weight="550">${esc(label)}</text><text x="58" y="46" font-size="10" fill="#8a7c96" font-family="system-ui">설명용 진입점 · 실행 관측 아님</text></g>`;
  const badge=roleIcons[node.role]||'SRC';
  const titleSize=state.mode==='feature'?17:18;
  let tags='';
  if(node.tags.length && state.mode==='system') {
    let tx=16,ty=103;
    for(const tag of node.tags.slice(0,6)) {const text=truncate(tag,15);const tw=Math.max(34,text.length*5.6+12);if(tx+tw>p.w-12){tx=16;ty+=22;}if(ty>p.h-8)break;tags+=`<rect x="${tx}" y="${ty-12}" width="${tw}" height="18" rx="4" fill="#f6f3fb"/><text x="${tx+6}" y="${ty}" font-size="8" fill="#756587" font-family="system-ui">${esc(text)}</text>`;tx+=tw+5;}
  }
  return `<g class="svg-node" data-node="${esc(node.id)}" tabindex="0" role="button" aria-label="${esc(node.label)} 근거 보기" transform="translate(${p.x},${p.y})"><title>${esc(node.path || node.description)}</title><rect class="node-box" width="${p.w}" height="${p.h}" rx="13" fill="${bg}" stroke="${border}" stroke-width="${chosen?1.8:1}" ${shadow}/><rect x="15" y="13" width="28" height="20" rx="5" fill="${iconBg}"/><text x="29" y="27" text-anchor="middle" font-size="8" font-weight="600" fill="${iconColor}" font-family="system-ui">${badge}</text><text x="52" y="27" font-size="10" letter-spacing=".6" fill="#786b8b" font-family="system-ui">${role}</text><circle cx="${p.w-20}" cy="23" r="3" fill="${infra?'#a6c1b3':'#b9add2'}"/><text x="16" y="57" font-size="${titleSize}" font-weight="550" letter-spacing="-.3" fill="#42384e" font-family="system-ui,Segoe UI,sans-serif">${esc(label)}</text><text x="16" y="77" font-size="10" fill="#797085" font-family="system-ui">${esc(truncate(description,35))}</text>${tags}</g>`;
}

function edgeSvg(edge, layout) {
  const a=layout.positions.get(edge.source),b=layout.positions.get(edge.target);if(!a||!b)return '';
  const selected=state.selected?.type==='edge'&&state.selected.id===edge.id;
  const candidate=edge.confidence==='candidate';
  const color=selected?'#8c70d4':candidate?'#c4b18b':'#b5aec6';
  let ax,ay,bx,by,path,lx,ly;
  const side=state.mode==='system'&&b.x>a.x+100;
  if(side){ax=a.x+a.w;ay=a.y+a.h/2;bx=b.x;by=b.y+b.h/2;const mx=(ax+bx)/2;path=`M${ax},${ay} C${mx},${ay} ${mx},${by} ${bx},${by}`;lx=mx;ly=(ay+by)/2;}
  else if(Math.abs(a.y-b.y)<20){ax=a.x+a.w;ay=a.y+a.h*.54;bx=b.x;by=b.y+b.h*.54;path=`M${ax},${ay} C${ax+25},${ay+44} ${bx-25},${by+44} ${bx},${by}`;lx=(ax+bx)/2;ly=ay+33;}
  else{ax=a.x+a.w/2;ay=a.y+a.h;bx=b.x+b.w/2;by=b.y;const my=(ay+by)/2;path=`M${ax},${ay} C${ax},${my} ${bx},${my} ${bx},${by}`;lx=(ax+bx)/2;ly=my;}
  let label=({import:'import',sdk:'SDK', 'http-contract':'HTTP · 후보','http-url':'HTTP','entry-model':'요청 · 설명용'})[edge.relation] || edge.relation;
  const showLabel=edge.relation!=='import'||state.mode==='system'||selected;
  return `<g data-edge="${esc(edge.id)}" tabindex="0" role="button" aria-label="${esc(label)} 연결 근거 보기"><title>${esc(edge.description)}</title><path class="svg-edge-hit" d="${path}" fill="none" stroke="transparent" stroke-width="18"/><path d="${path}" fill="none" stroke="${color}" stroke-width="${selected?2:1.5}" ${candidate?'stroke-dasharray="5 5"':''} marker-end="url(#${candidate?'arrow-candidate':'arrow'})" pointer-events="none"/>${showLabel?`<rect x="${lx-39}" y="${ly-9}" width="78" height="18" rx="6" fill="#fcfbfe"/><text x="${lx}" y="${ly+3}" text-anchor="middle" font-size="8" font-family="system-ui" fill="${candidate?'#b29d74':'#b0a4bf'}" pointer-events="none">${esc(label)}</text>`:''}</g>`;
}

function renderGraph() {
  if(!state.data)return;
  const {nodes,edges}=graphData();const layout=calculateLayout(nodes,edges);state.layout=layout;
  const svg=$('graph');
  svg.innerHTML=`<defs><filter id="node-shadow" x="-15%" y="-15%" width="140%" height="145%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#877898" flood-opacity=".055"/></filter><filter id="selected-shadow" x="-15%" y="-15%" width="140%" height="145%"><feDropShadow dx="0" dy="3" stdDeviation="7" flood-color="#a08ae1" flood-opacity=".15"/></filter><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#b5aec6"/></marker><marker id="arrow-candidate" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#c4b18b"/></marker></defs><g>${edges.map(e=>edgeSvg(e,layout)).join('')}</g><g>${nodes.map(n=>nodeSvg(n,layout.positions.get(n.id))).join('')}</g>`;
  applyZoom();
}
function applyZoom(){if(!state.layout)return;const {w,h}=state.layout;const vw=w/state.zoom,vh=h/state.zoom;const x=(w-vw)/2+state.pan.x,y=(h-vh)/2+state.pan.y;$('graph').setAttribute('viewBox',`${x} ${y} ${vw} ${vh}`);$('zoomLabel').textContent=Math.round(state.zoom*100)+'%';}
function featureCards(features){return features.map(f=>`<button class="feature-card" data-feature="${esc(f.id)}"><div class="card-top">${esc(f.label)}<span>↗</span></div><code>${esc(f.endpoint_labels[0]||'API')}</code><small>${f.node_ids.length}개 관련 노드 · ${f.endpoint_labels.length}개 endpoint</small></button>`).join('');}
function evidenceHtml(ids){const ev=new Map(state.data.evidence.map(e=>[e.id,e]));return [...new Set(ids)].slice(0,10).map(id=>{const e=ev.get(id);if(!e)return '';const url=e.url.startsWith('https://github.com/')?e.url:'';return `<article class="code-evidence"><div class="evidence-header">${esc(e.path)}<br>L${e.line}${e.end_line!==e.line?'–'+e.end_line:''}${url?`<a href="${esc(url)}" target="_blank" rel="noopener noreferrer">고정 커밋에서 보기 ↗</a>`:''}</div><pre>${esc(e.snippet)}</pre><div class="evidence-kind">${esc(e.kind)} · ${esc(e.parser)} · ${esc(e.id.slice(-7))}</div></article>`;}).join('')+(new Set(ids).size>10?`<p class="panel-description">근거 ${new Set(ids).size}개 중 10개를 표시했습니다. 전체는 JSON 내보내기에 포함됩니다.</p>`:'');}

function renderPanel(){
  const d=state.data,panel=$('detailPanel'),feature=currentFeature();if(!d)return;
  if(state.selected){
    const {nodes,edges}=graphData();const item=state.selected.type==='node'?nodes.find(n=>n.id===state.selected.id):edges.find(e=>e.id===state.selected.id);
    if(!item){state.selected=null;return renderPanel();}
    const isEdge=state.selected.type==='edge';
    const candidate=isEdge?item.confidence==='candidate':item.kind==='virtual';
    const name=isEdge?`${nodes.find(n=>n.id===item.source)?.label} → ${nodes.find(n=>n.id===item.target)?.label}`:item.label;
    const memberPaths=!isEdge?(item.kind==='file'?[item.path]:d.nodes.filter(n=>item.member_ids.includes(n.id)).map(n=>n.path)):[];
    const symbols=d.facts.filter(f=>f.kind==='symbol'&&memberPaths.includes(f.path));
    const featureMatches=!isEdge?d.features.filter(f=>f.component_ids.includes(item.id)||f.node_ids.includes(item.id)):[];
    const ai=!isEdge?d.explanation?.node_summaries.find(n=>n.node_id===item.id):null;
    panel.innerHTML=`<button class="panel-back" data-action="clear">← ${feature?'기능 요약':'핵심 기능'}</button><div class="panel-eyebrow">${isEdge?'CONNECTION EVIDENCE':'COMPONENT EVIDENCE'}</div><h3>${esc(name)}</h3><span class="confidence-pill ${candidate?'candidate':''}">${candidate?'◌ 연결 후보 / 설명용':'● 정적 코드 근거'}</span>${item.path?`<div class="detail-path">${esc(item.path)}</div>`:''}<p class="panel-description">${esc(item.description)}</p>${ai?`<div class="ai-explanation"><strong>AI 해석 · 별도 검토 필요</strong><br>${esc(ai.summary)}</div>`:''}${symbols.length?`<div class="panel-eyebrow">DECLARED SYMBOLS</div><div class="mini-tags">${[...new Set(symbols.map(f=>f.value))].slice(0,10).map(s=>`<span class="mini-tag">${esc(s)}</span>`).join('')}</div><p class="panel-description">정의된 심볼입니다. 함수 간 실행 순서를 확정한 목록이 아닙니다.</p>`:''}${featureMatches.length&&state.mode==='system'?`<div class="panel-divider"></div><div class="panel-eyebrow">이 영역의 기능 펼치기</div>${featureCards(featureMatches)}`:''}<div class="panel-divider"></div><div class="panel-eyebrow">SOURCE EVIDENCE · ${(item.evidence_ids||[]).length}</div>${item.kind==='virtual'?'<p class="panel-description">이 노드는 이해를 돕는 설명용 요소입니다. 실행 로그로 확인한 사용자가 아닙니다.</p>':evidenceHtml(item.evidence_ids||[])}<div class="confidence-note">근거의 존재와 실제 실행 성공은 다릅니다. 호출 분기·동적 연결은 추가 확인이 필요합니다.</div>`;
  }else if(feature){
    panel.innerHTML=`<div class="panel-eyebrow">FEATURE FLOW</div><h3>${esc(feature.label)}</h3><p class="panel-description">이 기능과 관련된 파일만 펼쳤습니다. 노드나 화살표를 선택해 실제 근거를 확인하세요.</p><div class="mini-tags">${feature.endpoint_labels.map(t=>`<span class="mini-tag">${esc(t)}</span>`).join('')}</div><div class="panel-metrics"><div class="metric"><strong>${feature.node_ids.length}</strong><span>관련 노드</span></div><div class="metric"><strong>${feature.edge_ids.length}</strong><span>연결 관계</span></div></div><div class="panel-divider"></div><div class="panel-eyebrow">분석 경계</div><ul class="warning-list">${feature.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul><div class="confidence-note warn">점선 HTTP 연결은 계약 일치 후보입니다. 실제 base URL과 서버 구성을 검증하지 않았습니다.</div><button class="button subtle" data-action="system">← 전체 시스템으로 돌아가기</button>`;
  }else{
    panel.innerHTML=`<div class="panel-eyebrow">EXPLORE THE NEXT LAYER</div><h3>어떤 기능이 궁금한가요?</h3><p class="panel-description">큰 흐름은 왼쪽 지도에.<br>기능을 고르면 관련 코드가 펼쳐집니다.</p>${featureCards(d.features)||'<p class="panel-description">지원 패턴의 API를 찾지 못했습니다. 각 구성요소의 근거를 먼저 확인하세요.</p>'}<div class="panel-divider"></div><div class="panel-eyebrow">ANALYSIS COVERAGE</div><div class="panel-metrics"><div class="metric"><strong>${d.coverage.analyzed}<span style="display:inline;font-size:11px;margin-left:3px">/ ${d.coverage.eligible}</span></strong><span>읽은 파일 / 지원 후보</span></div><div class="metric"><strong>${d.evidence.length}</strong><span>소스 근거</span></div></div><div class="confidence-note">실선은 import·SDK·URL의 정적 관계입니다. 점선은 아직 실행을 검증하지 않은 연결 후보입니다.</div>${d.explanation?`<div class="panel-divider"></div><div class="ai-explanation"><strong>AI 해석 · 코드 근거 별도 검토</strong><br>${esc(d.explanation.summary)}</div>`:''}`;
  }
}

function renderPipeline(){
  const d=state.data;if(!d)return;
  const cov=d.coverage;
  $('pipelineView').innerHTML=`<div class="eyebrow">TRANSPARENT BY DESIGN</div><h2>무엇을 읽고, 무엇을 확인했는지.</h2><p class="pipeline-intro">서로 다른 AI가 그림을 따로 만들지 않습니다. 하나의 코드 근거 그래프를 만들고, 전체 지도와 기능별 지도로 투영합니다.</p><div class="pipeline-stages">${d.stages.map(s=>`<div class="pipeline-stage"><b>${esc(s.name)}</b><strong>${s.duration_ms} <span style="font-size:10px;color:#b0a8b7">ms</span></strong><span class="pipeline-status ${esc(s.status)}">${({passed:'완료',warning:'제한 있음',skipped:'미실행'})[s.status]}</span><p>${esc(s.detail)}</p></div>`).join('')}</div><div class="pipeline-columns"><div><h3>분석 범위</h3><p>발견 ${cov.discovered}개 / 지원 후보 ${cov.eligible}개<br>읽음 ${cov.analyzed}개 / 지원·보안 기준 제외 ${cov.skipped}개<br>크기·선택 제한 ${cov.omitted}개 / 읽기 실패 ${cov.failed}개<br>${(cov.bytes_read/1024).toFixed(1)} KiB · ${cov.tree_truncated?'잘린 GitHub 트리':'수집된 트리 기준'}<br><code>${esc(d.revision.slice(0,16))}</code></p><h3>개발 Skills와 제품 파이프라인</h3><p><code>AGENTS.md</code>는 개발 규칙,<br><code>SKILL.md</code>는 재사용할 작업 절차입니다.<br>실제 분석 순서는 <code>app/orchestrator.py</code>가 실행합니다. Skill 문서를 독립 에이전트가 실행 중인 것처럼 표시하지 않습니다.</p><h3>실행하지 않는 일</h3><p>대상 코드 실행 · 패키지 설치 · 저장소 쓰기 · 비공개 저장소 접근 · 자동 배포 · 무제한 AI 재시도</p></div><div><h3>확인하지 못한 부분과 주의 사항</h3><ul class="warning-list">${d.warnings.map(w=>`<li>${esc(w)}</li>`).join('')}</ul><div class="confidence-note success">검증 통과는 ID·근거 줄·상하위 연결의 일관성을 뜻합니다. 의미 분석의 완전성이나 실제 운영 동작을 보장하지 않습니다.</div></div></div>`;
}

function download(name,content,type){const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);toast('내보내기 파일을 만들었습니다.');}
function exportFile(kind){
  if(!state.data)return;const d=state.data;const base='flowlens-'+d.revision.slice(0,8);
  if(kind==='json')download(base+'.json',JSON.stringify(d,null,2),'application/json');
  if(kind==='svg'){const svg=$('graph').cloneNode(true);svg.setAttribute('viewBox',`0 0 ${state.layout.w} ${state.layout.h}`);svg.setAttribute('width',state.layout.w);svg.setAttribute('height',state.layout.h);download(base+'-'+state.mode+'.svg',new XMLSerializer().serializeToString(svg),'image/svg+xml');}
  if(kind==='md'){
    const {nodes,edges}=graphData();const ids=new Map(nodes.map((n,i)=>[n.id,'n'+i]));const safeLabel=s=>String(s).replace(/[`"<>\[\]{}|\\\n\r]/g,' ').slice(0,80);
    const diagram=['flowchart TD',...nodes.map(n=>`  ${ids.get(n.id)}["${safeLabel(n.label)}"]`),...edges.map(e=>`  ${ids.get(e.source)} ${e.confidence==='candidate'?'-.->':'-->'} ${ids.get(e.target)}`)].join('\n');
    const md=`# ${d.name}\n\n${d.summary}\n\nRevision: ${d.revision}\nAnalyzer: ${d.analyzer_version}\nMode: ${state.mode}\n\n> Static relationships are not proof of runtime execution. Dashed edges are candidates.\n\n\`\`\`mermaid\n${diagram}\n\`\`\`\n\n## Coverage\n\n${d.coverage.analyzed} of ${d.coverage.eligible} eligible files read. ${d.coverage.omitted} omitted, ${d.coverage.failed} failed.\n\n## Limitations\n\n${d.warnings.map(w=>'- '+w).join('\n')}\n\n## Source evidence\n\n${d.evidence.map(e=>'- '+e.path.replace(/[\n\r`]/g,' ')+' : L'+e.line+'–L'+e.end_line+' ('+e.kind+', '+e.parser+')').join('\n')}\n`;
    download(base+'.md',md,'text/markdown');
  }
  $('exportMenu').classList.add('hidden');$('exportButton').setAttribute('aria-expanded','false');
}

$('repoForm').addEventListener('submit',event=>{event.preventDefault();const url=$('repoUrl').value.trim();if(!url)return notice('분석할 GitHub 저장소 URL을 입력해 주세요.',true);analyze({source:'github',url});});
$('folderButton').addEventListener('click',()=>$('folderInput').click());
$('zipButton').addEventListener('click',()=>$('zipInput').click());
$('zipInput').addEventListener('change',async event=>{
  const file=event.target.files?.[0]; if(!file)return;
  if(!/\.zip$/i.test(file.name)) { notice('ZIP 파일만 선택해 주세요.',true); event.target.value=''; return; }
  await analyzeZip(file); event.target.value='';
});
$('folderInput').addEventListener('change',async event=>{
  const raw=[...event.target.files];if(!raw.length)return;
  const root=raw[0].webkitRelativePath.split('/')[0];let skipped=0,total=0;const files=[];
  for(const file of raw){
    const path=(file.webkitRelativePath||file.name).replace(new RegExp('^'+root.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'/'),'');
    const parts=path.split('/');const allowed=/\.(py|js|jsx|ts|tsx|mjs|cjs|dart)$/.test(path)||/^(package\.json|pubspec\.yaml|requirements\.txt|pyproject\.toml|tsconfig\.json)$/.test(file.name);
    const excluded=parts.some(p=>p.startsWith('.')||['node_modules','vendor','dist','build','coverage','__pycache__','tests','test','fixtures','generated','venv'].includes(p.toLowerCase()))||/secret|credential|\.test\.|\.spec\.|\.g\.dart$|\.d\.ts$|\.min\.js$/i.test(file.name);
    if(!allowed||excluded||file.size>65536||files.length>=160||total+file.size>2*1024*1024){skipped++;continue;}
    total+=file.size;files.push({path,content:await file.text()});
  }
  if(!files.length)return notice('지원하는 소스 파일이 없습니다. Python / JavaScript / TypeScript / Dart 프로젝트를 선택해 주세요.',true);
  await analyze({source:'files',files});
  if(skipped)notice(`폴더 내 ${raw.length}개 중 ${files.length}개 파일을 전송했습니다. ${skipped}개는 형식·보안·용량 기준으로 제외했습니다. 서버 통계는 전달된 파일 기준입니다.`);
  event.target.value='';
});
document.addEventListener('click',event=>{
  const demo=event.target.closest('[data-demo]');if(demo)return analyze({source:'demo',demo:demo.dataset.demo});
  const feature=event.target.closest('[data-feature]');if(feature)return showFeature(feature.dataset.feature);
  const action=event.target.closest('[data-action]');if(action){if(action.dataset.action==='system')showSystem();else{state.selected=null;renderGraph();renderPanel();}return;}
  const systemNode=event.target.closest('[data-system-node]');if(systemNode){showSystem();state.selected={type:'node',id:systemNode.dataset.systemNode};renderGraph();renderPanel();return;}
  const exp=event.target.closest('[data-export]');if(exp)return exportFile(exp.dataset.export);
  if(!event.target.closest('.export-wrap')){$('exportMenu').classList.add('hidden');$('exportButton').setAttribute('aria-expanded','false');}
});
$('systemTab').addEventListener('click',showSystem);
$('featureTab').addEventListener('click',()=>state.data?.features.length?showFeature(state.feature||state.data.features[0].id):toast('지원 패턴의 API 기능이 없습니다.'));
$('exploreNav').addEventListener('click',()=>{state.page='explorer';render();});
$('pipelineNav').addEventListener('click',()=>{state.page='pipeline';render();});
[$('helpNav'),$('helpButton')].forEach(b=>b.addEventListener('click',()=>$('helpDialog').showModal()));
$('closeHelp').addEventListener('click',()=>$('helpDialog').close());
$('helpDialog').addEventListener('click',event=>{if(event.target===$('helpDialog')){const r=event.target.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)event.target.close();}});
$('exportButton').addEventListener('click',()=>{const closed=$('exportMenu').classList.toggle('hidden');$('exportButton').setAttribute('aria-expanded',String(!closed));});
$('zoomIn').addEventListener('click',()=>{state.zoom=Math.min(2.5,state.zoom+.2);applyZoom();});
$('zoomOut').addEventListener('click',()=>{state.zoom=Math.max(.6,state.zoom-.2);applyZoom();});
$('fitView').addEventListener('click',()=>{state.zoom=1;state.pan={x:0,y:0};applyZoom();});
function selectGraph(target){const node=target.closest('[data-node]'),edge=target.closest('[data-edge]');if(node)state.selected={type:'node',id:node.dataset.node};else if(edge)state.selected={type:'edge',id:edge.dataset.edge};else return;renderGraph();renderPanel();$('detailPanel').scrollTop=0;}
$('graph').addEventListener('click',e=>selectGraph(e.target));
$('graph').addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();selectGraph(e.target);}});
$('graph').addEventListener('wheel',e=>{if(!e.ctrlKey)return;e.preventDefault();state.zoom=Math.min(2.5,Math.max(.6,state.zoom+(e.deltaY<0?.1:-.1)));applyZoom();},{passive:false});
let drag=null;
$('graph').addEventListener('pointerdown',e=>{if(e.target.closest('[data-node],[data-edge]'))return;drag={x:e.clientX,y:e.clientY,pan:{...state.pan}};$('graph').setPointerCapture(e.pointerId);});
$('graph').addEventListener('pointermove',e=>{if(!drag||!state.layout)return;const rect=$('graph').getBoundingClientRect();const factor=Math.max(state.layout.w/rect.width,state.layout.h/rect.height)/state.zoom;state.pan={x:drag.pan.x-(e.clientX-drag.x)*factor,y:drag.pan.y-(e.clientY-drag.y)*factor};applyZoom();});
$('graph').addEventListener('pointerup',()=>drag=null);
$('graph').addEventListener('pointercancel',()=>drag=null);
$('explainToggle').addEventListener('change',()=>{if($('explainToggle').checked)toast('다음 분석에서 일부 코드 근거를 OpenAI로 전송합니다. 비밀 값을 먼저 제거하세요.');});
fetch('/api/health').then(r=>r.json()).then(d=>{$('aiNote').textContent=d.ai_configured?'선택 시 일부 코드 근거가 OpenAI로 전송됩니다.':'API 키 없이 정적 분석 · AI 설명은 서버 키/모델 설정 후 사용';}).catch(()=>{});
analyze({source:'demo',demo:'mobile'});
