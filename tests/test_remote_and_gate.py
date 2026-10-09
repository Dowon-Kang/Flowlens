"""External services are mocks; these tests do not claim live GitHub access."""
import asyncio, base64
import httpx, pytest
from app.intake import GitHubReader, IntakeError, valid_path, load_demo
from app.extractor import extract_facts
from app.graph import build_analysis
from app.verifier import verify_analysis, VerificationError

SHA='a'*40
TREE='b'*40
BLOB='c'*40
BLOB_CONTENT=b'from fastapi import FastAPI\napp = FastAPI()\n'

def remote(handler):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await GitHubReader(client).read('https://github.com/example/project')
    return asyncio.run(run())

def transport(private=False, truncated=False, failed=False, symlink=False):
    calls=[]
    def handler(request):
        calls.append(str(request.url)); p=request.url.path
        assert request.url.host=='api.github.com'
        if p=='/repos/example/project': return httpx.Response(200,json={'private':private,'default_branch':'main'})
        if '/commits/' in p: return httpx.Response(200,json={'sha':SHA,'commit':{'tree':{'sha':TREE}}})
        if '/git/trees/' in p:
            assert TREE in p
            entries=[{'path':'main.py','type':'blob','mode':'100644','size':len(BLOB_CONTENT),'sha':BLOB}]
            if symlink: entries.append({'path':'link.py','type':'blob','mode':'120000','size':8,'sha':'d'*40})
            return httpx.Response(200,json={'tree':entries,'truncated':truncated})
        if '/git/blobs/' in p:
            if failed: return httpx.Response(404)
            assert BLOB in p
            return httpx.Response(200,json={'encoding':'base64','content':base64.b64encode(BLOB_CONTENT).decode()})
        raise AssertionError(p)
    return handler,calls

def test_remote_pins_commit_and_reads_blob():
    handler,calls=transport(); result=remote(handler)
    assert result.revision==SHA and result.files[0].path=='main.py'
    assert len(calls)==4

def test_remote_private_repo_rejected_before_tree():
    handler,calls=transport(private=True)
    with pytest.raises(IntakeError): remote(handler)
    assert len(calls)==1

def test_remote_truncated_tree_is_disclosed():
    handler,_=transport(truncated=True); result=remote(handler)
    assert result.coverage.partial and result.coverage.tree_truncated

def test_remote_symlink_not_followed():
    handler,calls=transport(symlink=True); result=remote(handler)
    assert len(result.files)==1 and result.coverage.omitted==1
    assert not any('d'*40 in c for c in calls)

@pytest.mark.parametrize('status',[301,403,404,429,500])
def test_remote_errors_do_not_become_fake_success(status):
    with pytest.raises(IntakeError): remote(lambda r:httpx.Response(status,headers={'Location':'https://127.0.0.1/'}))

def test_remote_unreadable_sources_fail():
    handler,_=transport(failed=True)
    with pytest.raises(IntakeError): remote(handler)

@pytest.mark.parametrize('path',['line\nbreak.py','tab\tname.py','control\x7fname.py'])
def test_control_chars_in_path_rejected(path):
    with pytest.raises(IntakeError): valid_path(path)

@pytest.mark.parametrize('mutation',['snippet','parent','overview_evidence','candidate','feature_node'])
def test_structural_gate_rejects_corruption(mutation):
    snapshot=load_demo(); facts,ev,warnings=extract_facts(snapshot); result=build_analysis(snapshot,facts,ev,warnings)
    if mutation=='snippet': result.evidence[0].snippet='invented source'
    elif mutation=='parent': result.nodes[0].component_id='nonexistent'
    elif mutation=='overview_evidence': next(n for n in result.system_nodes if n.kind!='virtual').evidence_ids=['fake']
    elif mutation=='candidate': next(e for e in result.edges if e.relation=='http-contract').confidence='confirmed'
    else: result.features[0].node_ids.append('invented-node')
    with pytest.raises(VerificationError): verify_analysis(result,snapshot)
