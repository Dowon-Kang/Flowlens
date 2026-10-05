from __future__ import annotations
import asyncio
import os
from time import perf_counter
import httpx
from .models import AnalyzeRequest, Analysis, StageRecord, Snapshot
from .intake import GitHubReader, from_files, load_demo
from .extractor import extract_facts
from .graph import build_analysis
from .verifier import verify_analysis
from .ai import explain, ExplanationError

async def analyze_snapshot(snapshot: Snapshot, explain_requested: bool = False) -> Analysis:
    stages=[]
    def record(name: str,start: float,detail: str,status: str='passed'):
        stages.append(StageRecord(name=name,status=status,duration_ms=round((perf_counter()-start)*1000),detail=detail))
    t=perf_counter()
    record('INTAKE',t,f'{snapshot.coverage.analyzed} files · {snapshot.revision[:8]}','warning' if snapshot.coverage.partial else 'passed')
    t=perf_counter();facts,evidence,warnings=extract_facts(snapshot)
    record('EXTRACT',t,f'{len(facts)} facts · {len(evidence)} evidence records')
    t=perf_counter();result=build_analysis(snapshot,facts,evidence,warnings)
    record('BUILD',t,f'{len(result.nodes)} canonical nodes → {len(result.system_nodes)} overview nodes')
    t=perf_counter();verify_analysis(result,snapshot)
    record('VERIFY',t,'Evidence ranges, IDs, feature subsets and parent mapping checked')
    t=perf_counter()
    if explain_requested:
        key=os.environ.get('OPENAI_API_KEY','');model=os.environ.get('OPENAI_MODEL','')
        if key and model:
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(35,connect=5),headers={'Authorization':'Bearer '+key},trust_env=False) as client:
                    async with asyncio.timeout(45):
                        result.explanation=await explain(result,client,model)
                record('EXPLAIN',t,'1 opt-in model call · existing node IDs only')
            except (ExplanationError, TimeoutError) as exc:
                message=str(exc) if isinstance(exc,ExplanationError) else 'AI 응답 시간 초과. 정적 결과를 유지합니다.'
                result.warnings.append(message);record('EXPLAIN',t,message,'warning')
        else:
            result.warnings.append('AI 설명을 요청했지만 서버의 OPENAI_API_KEY / OPENAI_MODEL 설정이 없습니다. 정적 분석만 실행했습니다.')
            record('EXPLAIN',t,'Model credentials not configured','skipped')
    else: record('EXPLAIN',t,'User did not request an external AI call','skipped')
    result.stages=stages
    return result


async def run_analysis(request: AnalyzeRequest) -> Analysis:
    if request.source=='demo':
        snapshot=load_demo(request.demo)
    elif request.source=='files':
        snapshot=from_files(request.files)
    else:
        headers={'Accept':'application/vnd.github+json','User-Agent':'FlowLens-MVP','X-GitHub-Api-Version':'2022-11-28'}
        token=os.environ.get('GITHUB_TOKEN','')
        if token: headers['Authorization']='Bearer '+token
        async with httpx.AsyncClient(timeout=httpx.Timeout(12,connect=5),headers=headers,trust_env=False) as client:
            async with asyncio.timeout(90):
                snapshot=await GitHubReader(client).read(request.url)
    return await analyze_snapshot(snapshot, request.explain)
