"""Generate a self-contained UI demo from real analyses of synthetic fixtures.
It does not analyze new repositories or invoke AI. Run the server for those features.
"""
from pathlib import Path
import asyncio,json,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.models import AnalyzeRequest
from app.orchestrator import run_analysis

async def build():
    snapshots={}
    for name in ['mobile','python']:
        result=await run_analysis(AnalyzeRequest(source='demo',demo=name))
        snapshots[name]=result.model_dump()
    data=json.dumps(snapshots,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    css=(ROOT/'static/styles.css').read_text(encoding='utf-8')
    css+='\n.source-box,.source-options{display:none!important}.offline-banner{margin:0 0 22px;padding:14px 18px;border:1px solid #d9d2ee;border-radius:10px;background:#f0edfa;color:#635778;font-size:12px;line-height:1.8}.offline-banner strong{color:#433355}\n'
    script=(ROOT/'static/app.js').read_text(encoding='utf-8')
    stub="""
const offlineSnapshots = __DATA__;
window.fetch = async (path, options={}) => {
  if (path==='/api/health') return new Response(JSON.stringify({ok:true,ai_configured:false,mode:'offline-snapshot-demo'}),{status:200});
  if (path==='/api/analyze') {
    const request=JSON.parse(options.body || '{}');
    if(request.source==='demo' && offlineSnapshots[request.demo || 'mobile'])
      return new Response(JSON.stringify(offlineSnapshots[request.demo || 'mobile']),{status:200});
  }
  return new Response(JSON.stringify({error:'오프라인 데모는 합성 예제만 탐색합니다. 새로운 저장소 분석은 Python 서버를 실행해 주세요.'}),{status:501});
};
""".replace('__DATA__',data)
    html=(ROOT/'static/index.html').read_text(encoding='utf-8')
    html=re.sub(r'<link[^>]*>','',html)
    html=re.sub(r'<script[^>]*>.*?</script>','',html,flags=re.S)
    html=html.replace('</head>',f'<style>{css}</style></head>')
    html=html.replace('href="/"','href="#"')
    html=html.replace('<section class="source-box"','<div class="offline-banner"><strong>오프라인 인터랙티브 데모</strong> · 왼쪽 예제를 고르고 기능·노드·화살표를 눌러 보세요.<br>두 합성 저장소를 실제 분석기로 처리한 결과를 포함합니다. 이 파일은 새 저장소를 분석하거나 AI를 호출하지 않습니다.</div><section class="source-box"')
    html=html.replace('</body>','<script type="module">'+stub+'\n'+script+'</script></body>')
    target=ROOT/'demo.html';target.write_text(html,encoding='utf-8')
    print(f'{target}: {target.stat().st_size:,} bytes, 2 synthetic analysis snapshots')
if __name__=='__main__':asyncio.run(build())
