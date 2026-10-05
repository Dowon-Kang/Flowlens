import asyncio,json
import httpx,pytest
from app.ai import validate_explanation,explain,redact,ExplanationError
from tests.test_graph import analyze

def test_unknown_ai_node_is_rejected():
    with pytest.raises(ExplanationError):
        validate_explanation({'summary':'x','node_summaries':[{'node_id':'fake','summary':'x','evidence_ids':['fake']}]},analyze())

def test_evidence_must_belong_to_node():
    r=analyze();n=next(n for n in r.system_nodes if n.kind!='virtual')
    with pytest.raises(ExplanationError):
        validate_explanation({'summary':'x','node_summaries':[{'node_id':n.id,'summary':'x','evidence_ids':['unrelated']}]},r)

def test_valid_ai_uses_existing_nodes_only():
    r=analyze();n=next(n for n in r.system_nodes if n.kind!='virtual')
    e=validate_explanation({'summary':'정적 분석 설명','node_summaries':[{'node_id':n.id,'summary':'설명','evidence_ids':n.evidence_ids[:1]}]},r)
    assert e.node_summaries[0].node_id==n.id

def test_mock_responses_api_contract():
    r=analyze();n=next(n for n in r.system_nodes if n.kind!='virtual')
    data={'summary':'정적 분석 설명','node_summaries':[{'node_id':n.id,'summary':'설명','evidence_ids':n.evidence_ids[:1]}]}
    def handler(request):
        body=json.loads(request.content)
        assert request.url.host=='api.openai.com'
        assert body['text']['format']['strict'] is True
        assert body['store'] is False
        assert 'tools' not in body
        return httpx.Response(200,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(data)}]}]})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await explain(r,c,'configured-model')
    out=asyncio.run(run())
    assert out.summary==data['summary']

def test_redaction():
    assert 'sk-abcdefghijklmnopqrst' not in redact('key="sk-abcdefghijklmnopqrst"')
    assert 'abcxyz' not in redact('password = "abcxyz"')
