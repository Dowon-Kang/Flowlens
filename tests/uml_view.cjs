// Executes FlowLens rendering helpers only. This is NOT an HTTP browser test.
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const source=fs.readFileSync('static/app.js','utf8');
const begin=source.indexOf('// UML ACTIVITY HELPERS');
if(begin<0)throw new Error('Activity helpers are missing');
const end=source.indexOf('// END UML ACTIVITY HELPERS',begin);
const sandbox={console,Map,Set,Math,JSON, state:{data:input,selected:null},
 esc:s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 truncate:(s,n=35)=>String(s).length>n?String(s).slice(0,n-1)+'…':String(s)};
vm.createContext(sandbox);vm.runInContext(source.slice(begin,end),sandbox);
const flow=input.flows.find(f=>f.kind==='route');
sandbox.flow=flow;
const result=vm.runInContext(`(()=>{ const g=activityGraph(flow),l=activityLayout(g.nodes,g.edges);return {nodes:g.nodes,edges:g.edges,w:l.w,h:l.h,positions:[...l.positions],svg:g.nodes.map(n=>activityNodeSvg(n,l.positions.get(n.id))).join('')+g.edges.map(e=>activityEdgeSvg(e,l)).join(''),mermaid:activityMermaid(g.nodes,g.edges)};})()`,sandbox);
process.stdout.write(JSON.stringify(result));
