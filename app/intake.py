"""Bounded, read-only source intake. No git clone, subprocess, or repo execution."""
from __future__ import annotations
import asyncio
import base64
import hashlib
import io
import re
import stat
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse, quote
import httpx
from .models import Coverage, Snapshot, SourceFile

MAX_FILES = 160
MAX_REMOTE_FILES = 160
MAX_FILE_BYTES = 64 * 1024
MAX_TOTAL_BYTES = 2 * 1024 * 1024
MAX_ZIP_BYTES = 12 * 1024 * 1024
MAX_ZIP_ENTRIES = 2500
MAX_ZIP_MEMBER_BYTES = 256 * 1024
SOURCE_SUFFIXES = {'.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.dart'}
MANIFESTS = {'package.json', 'pubspec.yaml', 'requirements.txt', 'pyproject.toml', 'tsconfig.json'}
EXCLUDED_PARTS = {'node_modules', 'vendor', 'dist', 'build', 'coverage', '__pycache__', 'test', 'tests', 'fixtures', 'generated', 'migrations', 'venv'}
SECRET = re.compile(r'(^\.env(?:\.|$)|secret|credential|id_rsa|id_ed25519|\.pem$|\.key$)', re.I)

class IntakeError(ValueError):
    pass

def valid_path(path: str) -> str:
    if not path or any(ord(c)<32 or ord(c)==127 for c in path) or '\\' in path or ':' in path:
        raise IntakeError('안전하지 않은 파일 경로입니다.')
    p = PurePosixPath(path)
    if p.is_absolute() or any(x in {'..', ''} for x in path.split('/')) or len(path) > 240:
        raise IntakeError('상대 경로만 허용하며 .. 경로는 사용할 수 없습니다.')
    return str(p)

def eligible_path(path: str) -> bool:
    p = PurePosixPath(valid_path(path))
    if any(part.startswith('.') or part.lower() in EXCLUDED_PARTS for part in p.parts):
        return False
    if SECRET.search(p.name) or re.search(r'(\.test\.|\.spec\.|\.d\.ts$|\.g\.dart$|\.freezed\.dart$|\.min\.js$)', p.name):
        return False
    return p.suffix.lower() in SOURCE_SUFFIXES or p.name in MANIFESTS

def priority(path: str) -> tuple[int, str]:
    p = path.lower()
    if PurePosixPath(p).name in MANIFESTS:
        rank = 0
    elif re.search(r'(^|/)(main|index|app|server|node-server|runtime|providers)\.(py|tsx?|jsx?|dart)$', p):
        rank = 1
    elif re.search(r'route|controller|provider|/storage/|/(algorithm|auth)\.', p):
        rank = 2
    elif 'service' in p or 'controller' in p or 'client' in p:
        rank = 3
    else:
        rank = 4
    return rank, path

def from_files(files: list[SourceFile], name: str = 'Local repository', source: str = 'files') -> Snapshot:
    seen: set[str] = set()
    candidates: list[SourceFile] = []
    warnings: list[str] = []
    oversized = 0
    for item in files:
        path = valid_path(item.path)
        if path in seen:
            raise IntakeError(f'중복된 파일 경로입니다: {path}')
        seen.add(path)
        if eligible_path(path):
            if len(item.content.encode('utf-8')) > MAX_FILE_BYTES or '\x00' in item.content:
                oversized += 1
                continue
            candidates.append(SourceFile(path=path, content=item.content))
    accepted: list[SourceFile] = []
    total = 0
    for item in sorted(candidates, key=lambda x: priority(x.path)):
        size = len(item.content.encode('utf-8'))
        if len(accepted) >= MAX_FILES or total + size > MAX_TOTAL_BYTES:
            continue
        accepted.append(item)
        total += size
    omitted = len(candidates) - len(accepted) + oversized
    if omitted:
        warnings.append(f'용량·개수 제한으로 {omitted}개 파일을 분석하지 못했습니다.')
    if not any(PurePosixPath(f.path).suffix in SOURCE_SUFFIXES for f in accepted):
        raise IntakeError('분석할 지원 소스가 없습니다. Python / JavaScript / TypeScript / Dart 파일을 선택해 주세요.')
    coverage = Coverage(discovered=len(files), eligible=len(candidates)+oversized,
                        analyzed=len(accepted), skipped=len(files)-len(candidates)-oversized,
                        omitted=omitted, bytes_read=total, partial=bool(omitted),
                        notes=['선택되거나 수집된 파일만 분석합니다. 문서·테스트·빌드 결과·비밀 파일은 제외합니다.'])
    digest = hashlib.sha256()
    for f in sorted(accepted, key=lambda x: x.path):
        digest.update(f.path.encode()+b'\x00'+f.content.encode()+b'\x00')
    return Snapshot(name=name, source=source, revision=digest.hexdigest(), files=accepted, coverage=coverage, warnings=warnings)



def _zip_member_is_symlink(info: zipfile.ZipInfo) -> bool:
    mode = (info.external_attr >> 16) & 0xFFFF
    return stat.S_ISLNK(mode)

def _strip_common_zip_root(paths: list[str]) -> dict[str, str]:
    """Strip one archive wrapper directory (typical GitHub ZIP) without guessing deeper structure."""
    if not paths:
        return {}
    first_parts = [PurePosixPath(path).parts for path in paths]
    if all(len(parts) > 1 for parts in first_parts):
        root = first_parts[0][0]
        if all(parts[0] == root for parts in first_parts):
            return {path: PurePosixPath(*PurePosixPath(path).parts[1:]).as_posix() for path in paths}
    return {path: path for path in paths}

def from_zip_bytes(data: bytes, filename: str = 'repository.zip') -> Snapshot:
    """Bound decompression before reads; never extract or execute target code."""
    if not data:
        raise IntakeError('ZIP 파일이 비어 있습니다.')
    if len(data) > MAX_ZIP_BYTES:
        raise IntakeError(f'ZIP 파일은 {MAX_ZIP_BYTES // (1024*1024)} MiB 이하만 지원합니다.')
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, ValueError) as exc:
        raise IntakeError('올바른 ZIP 파일이 아닙니다.') from exc
    with archive:
        entries = archive.infolist()
        if len(entries) > MAX_ZIP_ENTRIES:
            raise IntakeError(f'ZIP 내부 항목이 너무 많습니다. 최대 {MAX_ZIP_ENTRIES}개까지 검사합니다.')
        infos = [info for info in entries if not info.is_dir()]
        paths: list[str] = []
        seen: set[str] = set()
        for info in infos:
            path = valid_path(info.orig_filename.replace('\\', '/'))
            if path in seen:
                raise IntakeError(f'ZIP에 중복된 경로가 있습니다: {path[:120]}')
            seen.add(path)
            if info.flag_bits & 0x1:
                raise IntakeError('암호화된 ZIP 파일은 지원하지 않습니다.')
            paths.append(path)
        mapping = _strip_common_zip_root(paths)
        candidates = [(info, mapping[path]) for info, path in zip(infos, paths)
                      if eligible_path(mapping[path])]
        files: list[SourceFile] = []
        omitted = failed = consumed = attempts = 0
        for info, path in sorted(candidates, key=lambda item: priority(item[1])):
            if (_zip_member_is_symlink(info) or info.file_size > MAX_FILE_BYTES
                    or attempts >= MAX_FILES or consumed + info.file_size > MAX_TOTAL_BYTES):
                omitted += 1
                continue
            attempts += 1
            consumed += info.file_size
            try:
                raw = archive.read(info)
                if len(raw) != info.file_size or b'\x00' in raw:
                    raise ValueError('invalid text member')
                files.append(SourceFile(path=path, content=raw.decode('utf-8')))
            except (UnicodeError, RuntimeError, zipfile.BadZipFile, zlib.error, EOFError, ValueError):
                failed += 1
        name = PurePosixPath(filename or 'repository.zip').name.removesuffix('.zip') or 'ZIP repository'
        snapshot = from_files(files, name=name, source='zip')
        cov = snapshot.coverage
        cov.discovered = len(infos)
        cov.eligible = len(candidates)
        cov.skipped = len(infos) - len(candidates)
        cov.omitted += omitted
        cov.failed = failed
        cov.partial = bool(cov.omitted or failed)
        if cov.partial:
            snapshot.warnings.append(f'ZIP 부분 분석: 지원 후보 {cov.eligible}개 중 {cov.analyzed}개 분석, {cov.omitted}개 제한 제외, {failed}개 읽기 실패.')
        cov.notes.append('ZIP은 메모리에서 읽으며 파일을 디스크에 풀거나 대상 코드를 실행하지 않습니다.')
        cov.notes.append('압축 해제 전에 파일당 64 KiB, 최대 파일 수와 총 2 MiB 읽기 예산을 적용합니다.')
        return snapshot

def load_demo(name: str = 'mobile') -> Snapshot:
    if name not in {'mobile', 'python'}:
        raise IntakeError('알 수 없는 예제입니다.')
    root = Path(__file__).resolve().parents[1] / 'fixtures' / f'{name}-demo'
    files = [SourceFile(path=p.relative_to(root).as_posix(), content=p.read_text(encoding='utf-8')) for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
    snapshot = from_files(files, 'FlowCare · 합성 예제' if name == 'mobile' else 'TaskBoard · 합성 예제', 'demo')
    snapshot.warnings.insert(0, '이 예제는 분석기 검증용 합성 소스입니다. 실제 VibeCare 코드나 운영 시스템이 아닙니다.')
    return snapshot

def parse_github_url(url: str) -> tuple[str, str]:
    p = urlparse(url.strip())
    if p.scheme != 'https' or p.netloc != 'github.com' or p.username or p.password or p.query or p.fragment:
        raise IntakeError('https://github.com/소유자/저장소 형식만 허용합니다.')
    parts = p.path.strip('/').split('/')
    if len(parts) != 2:
        raise IntakeError('브랜치·파일 주소가 아닌 저장소의 루트 URL을 입력해 주세요.')
    owner, repo = parts
    repo = repo.removesuffix('.git')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}', owner) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}', repo) or repo in {'.', '..'}:
        raise IntakeError('올바르지 않은 GitHub 저장소 이름입니다.')
    return owner, repo

class GitHubReader:
    """HTTP client injection makes all external paths testable without network."""
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def get(self, path: str, limit: int = 5 * 1024 * 1024) -> dict:
        try:
            async with self.client.stream('GET', 'https://api.github.com' + path, follow_redirects=False) as response:
                if response.status_code in {403, 429}:
                    raise IntakeError('GitHub 요청 제한 또는 권한 오류입니다. 잠시 후 다시 시도하거나 ZIP 또는 로컬 폴더를 사용해 주세요.')
                if response.status_code == 404:
                    raise IntakeError('공개 저장소 또는 해당 파일을 찾지 못했습니다.')
                if response.status_code != 200:
                    raise IntakeError(f'GitHub가 요청을 처리하지 못했습니다 (HTTP {response.status_code}).')
                data = bytearray()
                async for chunk in response.aiter_bytes():
                    data.extend(chunk)
                    if len(data) > limit:
                        raise IntakeError('GitHub 응답이 허용 크기를 초과했습니다.')
                import json
                result = json.loads(data)
                if not isinstance(result, dict):
                    raise IntakeError('예상하지 못한 GitHub 응답입니다.')
                return result
        except (httpx.HTTPError, ValueError) as exc:
            if isinstance(exc, IntakeError):
                raise
            raise IntakeError('GitHub 연결 또는 응답 해석에 실패했습니다. ZIP 또는 로컬 폴더 분석을 사용할 수 있습니다.') from exc

    async def read(self, url: str) -> Snapshot:
        owner, repo = parse_github_url(url)
        prefix = f'/repos/{owner}/{repo}'
        meta = await self.get(prefix)
        if meta.get('private') is not False:
            raise IntakeError('이 MVP는 공개 저장소만 지원합니다.')
        branch = meta.get('default_branch')
        if not isinstance(branch, str) or not branch:
            raise IntakeError('저장소의 기본 브랜치를 확인하지 못했습니다.')
        commit = await self.get(prefix + '/commits/' + quote(branch, safe=''))
        sha = commit.get('sha', '')
        if not re.fullmatch(r'[a-fA-F0-9]{40}', sha):
            raise IntakeError('저장소 커밋을 고정하지 못했습니다.')
        tree_sha = commit.get('commit', {}).get('tree', {}).get('sha', '')
        if not re.fullmatch(r'[a-fA-F0-9]{40}', tree_sha):
            raise IntakeError('저장소 파일 트리를 확인하지 못했습니다.')
        tree = await self.get(prefix + f'/git/trees/{tree_sha}?recursive=1')
        entries = tree.get('tree', [])
        blobs = [x for x in entries if x.get('type') == 'blob']
        candidates = []
        for x in blobs:
            try:
                eligible = eligible_path(x.get('path', ''))
            except IntakeError:
                eligible = False
            if eligible:
                candidates.append(x)
        readable = [x for x in candidates if x.get('mode') != '120000' and isinstance(x.get('size'), int) and x['size'] <= MAX_FILE_BYTES and re.fullmatch(r'[a-fA-F0-9]{40}', x.get('sha', ''))]
        picked = sorted(readable, key=lambda x: priority(x['path']))[:MAX_REMOTE_FILES]
        semaphore = asyncio.Semaphore(4)
        failures: list[str] = []
        async def fetch_one(x: dict) -> SourceFile | None:
            async with semaphore:
                try:
                    blob = await self.get(prefix + '/git/blobs/' + x['sha'], limit=120000)
                    if blob.get('encoding') != 'base64':
                        raise IntakeError('미지원 인코딩')
                    raw = base64.b64decode(blob.get('content', ''), validate=False)
                    if len(raw) > MAX_FILE_BYTES:
                        raise IntakeError('파일 크기 초과')
                    return SourceFile(path=x['path'], content=raw.decode('utf-8'))
                except (ValueError, UnicodeError, IntakeError):
                    failures.append(x['path'])
                    return None
        fetched = await asyncio.gather(*(fetch_one(x) for x in picked))
        snapshot = from_files([f for f in fetched if f], f'{owner}/{repo}', 'github')
        snapshot.revision = sha
        snapshot.repository_url = f'https://github.com/{owner}/{repo}'
        cov = snapshot.coverage
        cov.discovered = len(blobs)
        cov.eligible = len(candidates)
        cov.skipped = len(blobs)-len(candidates)
        cov.failed = len(failures)
        cov.omitted = len(candidates)-cov.analyzed-cov.failed
        cov.tree_truncated = bool(tree.get('truncated'))
        cov.partial = bool(cov.omitted or failures or cov.tree_truncated)
        if cov.partial:
            snapshot.warnings.append(f'부분 분석: 지원 후보 {cov.eligible}개 중 {cov.analyzed}개를 읽었습니다. 파일 선택/실패/잘린 트리 범위를 확인하세요.')
        if failures:
            snapshot.warnings.append('읽기 실패: ' + ', '.join(failures[:6]))
        if cov.tree_truncated:
            snapshot.warnings.append('GitHub 파일 트리가 잘렸습니다. 전체 저장소 크기와 완전성을 알 수 없습니다.')
        return snapshot
