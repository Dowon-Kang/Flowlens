"""Self-contained replay of a real saved analysis with the SAME product renderer.
No fabricated nodes/labels and no new repository or model requests in the demo.
"""
from pathlib import Path
import argparse,json,re,sys
ROOT=Path(__file__).resolve().parents[1]

def build(analysis_path: Path, output: Path):
    result=json.loads(analysis_path.read_text(encoding='utf-8'))
    data=json.dumps(result,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    html=re.sub(r'<link[^>]*>','',html);html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
    css=(ROOT/'static/styles.css').read_text(encoding='utf-8')+'\n.source-box,.source-options,.repo-button,.demo-note{display:none!important}.replay-banner{padding:14px 18px;margin-bottom:20px;border:1px solid #ddd8f5;border-radius:10px;background:#f2f0fb;font-size:13px;line-height:1.8}.review-shortcuts{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}'
    html=html.replace('</head>','<style>'+css+'</style></head>').replace('href="/"','href="#"')
    html=html.replace('EXAMPLE REPOSITORIES','SAVED REAL ANALYSIS')
    notice='<div class="replay-banner"><strong>FlowLens v0.3 · 실제 VibeCare 결과 체험</strong><br>전체 구조 → 기능 처리 단계 → 함수 내부 → 소스 근거. 저장된 분석 결과이며 새 저장소 분석·AI 호출·대상 코드 실행은 하지 않습니다.<div class="review-shortcuts"><button class="button" id="reviewSystem">① 전체 구조</button><button class="button" id="reviewRecommendation">② 추천 단계</button><button class="button" id="reviewHealth">③ Health 비교</button></div></div>'
    html=html.replace('<section class="source-box"',notice+'<section class="source-box"')
    stub='''
const savedAnalysis=__DATA__;
window.fetch=async(path,options={})=>{
 if(path==='/api/health')return new Response(JSON.stringify({ok:true,ai_configured:false}),{status:200});
 if(path==='/api/analyze' && JSON.parse(options.body||'{}').source==='demo')return new Response(JSON.stringify(savedAnalysis),{status:200});
 return new Response(JSON.stringify({error:'저장 결과 체험입니다. 새 입력 분석은 로컬 서버를 실행하세요.'}),{status:501});
};
'''.replace('__DATA__',data)
    extra='''
document.getElementById('reviewSystem').onclick=showSystem;
document.getElementById('reviewRecommendation').onclick=()=>{const f=state.data?.features.find(f=>f.endpoint_labels.some(x=>x.includes('/recommendations/authorize')));if(f)showFeature(f.id)};
document.getElementById('reviewHealth').onclick=()=>{const f=state.data?.features.find(f=>f.endpoint_labels.includes('GET /health'));if(f)showFeature(f.id)};
'''
    script=(ROOT/'static/app.js').read_text(encoding='utf-8')
    html=html.replace('</body>','<script type="module">'+stub+'\n'+script+'\n'+extra+'</script></body>')
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(html,encoding='utf-8');print(output)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('analysis');p.add_argument('output');a=p.parse_args();build(Path(a.analysis),Path(a.output))
