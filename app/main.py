from __future__ import annotations
import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import ValidationError
from . import __version__
from .models import AnalyzeRequest, FilePlanRequest
from .orchestrator import run_analysis, analyze_snapshot
from .intake import IntakeError, load_demo, from_zip_bytes, MAX_ZIP_BYTES, plan_files
from .verifier import VerificationError

ROOT=Path(__file__).resolve().parents[1]
app=FastAPI(title='FlowLens API',version=__version__,docs_url='/api/docs',redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1','localhost','testserver'])
semaphore=asyncio.Semaphore(2)
MAX_BODY=3*1024*1024

@app.middleware('http')
async def safety_headers(request: Request,call_next):
    # Local-first app, no permissive CORS or cross-origin source submissions.
    if request.method=='POST':
        origin=request.headers.get('origin')
        if origin:
            parsed=urlparse(origin)
            if parsed.netloc!=request.headers.get('host') or parsed.scheme not in {'http','https'}:
                return JSONResponse({'error':'교차 출처 요청을 허용하지 않습니다.'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Cache-Control']='no-store'
    if request.url.path=='/':
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'self'"
    return response

@app.get('/api/health')
async def health():
    return {'ok':True,'version':__version__,'ai_configured':bool(os.getenv('OPENAI_API_KEY') and os.getenv('OPENAI_MODEL')),'mode':'local-first'}

@app.post('/api/file-plan')
async def file_plan(request: Request):
    """Metadata only. Reuse ZIP selection policy before browser content reads."""
    if 'application/json' not in request.headers.get('content-type', ''):
        return JSONResponse({'error': 'JSON 요청만 지원합니다.'}, status_code=415)
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > MAX_BODY:
            return JSONResponse({'error': '요청 크기가 3 MiB를 초과했습니다.'}, status_code=413)
    try:
        data = FilePlanRequest.model_validate_json(raw)
        selected, coverage = plan_files(data.entries, strip_root=True)
        return {'selected': selected, 'coverage': coverage.model_dump()}
    except ValidationError:
        return JSONResponse({'error': '파일 목록 형식·개수·크기를 확인해 주세요.'}, status_code=422)
    except IntakeError as exc:
        return JSONResponse({'error': str(exc)}, status_code=400)

@app.post('/api/analyze')
async def analyze(request: Request):
    if 'application/json' not in request.headers.get('content-type',''):
        return JSONResponse({'error':'JSON 요청만 지원합니다.'},status_code=415)
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>MAX_BODY:
            return JSONResponse({'error':'요청 크기가 3 MiB를 초과했습니다.'},status_code=413)
    try:
        data=AnalyzeRequest.model_validate_json(raw)
    except ValidationError:
        return JSONResponse({'error':'입력 형식, 파일 크기 또는 파일 수 제한을 확인해 주세요.'},status_code=422)
    try:
        # Refuse a busy request instead of silently queuing unbounded analysis work.
        try: await asyncio.wait_for(semaphore.acquire(),timeout=0.1)
        except TimeoutError: return JSONResponse({'error':'분석이 진행 중입니다. 현재 요청이 끝난 뒤 다시 시도해 주세요.'},status_code=429)
        try:
            async with asyncio.timeout(140):
                result=await run_analysis(data)
            return JSONResponse(result.model_dump())
        finally: semaphore.release()
    except IntakeError as exc:
        return JSONResponse({'error':str(exc)},status_code=400)
    except TimeoutError:
        return JSONResponse({'error':'분석 시간이 제한을 초과했습니다. 더 작은 저장소나 로컬 폴더를 사용해 주세요.'},status_code=504)
    except VerificationError:
        return JSONResponse({'error':'분석 결과의 근거 일관성 검사에 실패했습니다. 불확실한 결과를 공개하지 않습니다.'},status_code=500)


@app.post('/api/analyze-zip')
async def analyze_zip(request: Request, explain: bool = False, filename: str = 'repository.zip'):
    content_type=request.headers.get('content-type','').split(';',1)[0].strip().lower()
    if content_type not in {'application/zip','application/x-zip-compressed','application/octet-stream'}:
        return JSONResponse({'error':'ZIP 파일 본문만 지원합니다.'},status_code=415)
    raw=bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw)>MAX_ZIP_BYTES:
            return JSONResponse({'error':f'ZIP 파일은 {MAX_ZIP_BYTES // (1024*1024)} MiB 이하만 지원합니다.'},status_code=413)
    try:
        try:
            await asyncio.wait_for(semaphore.acquire(),timeout=0.1)
        except TimeoutError:
            return JSONResponse({'error':'분석이 진행 중입니다. 현재 요청이 끝난 뒤 다시 시도해 주세요.'},status_code=429)
        try:
            async with asyncio.timeout(140):
                snapshot=await asyncio.to_thread(from_zip_bytes, bytes(raw), filename)
                result=await analyze_snapshot(snapshot, explain)
            return JSONResponse(result.model_dump())
        finally:
            semaphore.release()
    except IntakeError as exc:
        return JSONResponse({'error':str(exc)},status_code=400)
    except TimeoutError:
        return JSONResponse({'error':'분석 시간이 제한을 초과했습니다.'},status_code=504)
    except VerificationError:
        return JSONResponse({'error':'분석 결과의 근거 일관성 검사에 실패했습니다. 불확실한 결과를 공개하지 않습니다.'},status_code=500)

@app.get('/api/demo/{name}')
async def demo_source(name: str):
    try: snapshot=load_demo(name)
    except IntakeError: return JSONResponse({'error':'예제를 찾을 수 없습니다.'},status_code=404)
    return {'files':[f.model_dump() for f in snapshot.files]}

@app.get('/')
async def index():
    return FileResponse(ROOT/'static'/'index.html')

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
