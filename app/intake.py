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
from .models import Coverage, Snapshot, SourceFile, FileMetadata, ReadFailure, BrowserSelection

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

def exclusion_reason(path: str) -> str:
    """One server-owned eligibility policy, shared by folder, ZIP and GitHub."""
    p = PurePosixPath(valid_path(path))
    if any(part.startswith('.') or SECRET.search(part) for part in p.parts):
        return 'secret_or_hidden'
    if any(part.lower() in EXCLUDED_PARTS for part in p.parts):
        return 'excluded_directory'
    if re.search(r'(\.test\.|\.spec\.|\.d\.ts$|\.g\.dart$|\.freezed\.dart$|\.min\.js$)', p.name):
        return 'generated_or_test'
    if p.suffix.lower() not in SOURCE_SUFFIXES and p.name not in MANIFESTS:
        return 'unsupported_type'
    return ''

def eligible_path(path: str) -> bool:
    return not exclusion_reason(path)

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

def plan_files(entries: list[FileMetadata], *, strip_root: bool = False,
               symlinks: set[int] | None = None) -> tuple[list[dict], Coverage]:
    """Select by metadata BEFORE reading. Reused by folder preflight and ZIP.

    A failed read consumes its selected slot/byte budget; there is no format-
    dependent backfill. Recheck the manifest on submission, never trust counts.
    """
    if len(entries) > MAX_ZIP_ENTRIES:
        raise IntakeError(f'파일 목록은 최대 {MAX_ZIP_ENTRIES}개까지 지원합니다.')
    paths = [valid_path(e.path) for e in entries]
    if len(set(paths)) != len(paths):
        raise IntakeError('중복된 파일 경로입니다.')
    mapping = _strip_common_zip_root(paths) if strip_root else dict(zip(paths, paths))
    cov = Coverage(discovered=len(entries), notes=[
        '선택되거나 수집된 파일만 분석합니다. 문서·테스트·빌드 결과·비밀 파일은 제외합니다.'])
    candidates = []
    for i, entry in enumerate(entries):
        path = mapping[paths[i]]
        reason = exclusion_reason(path)
        if reason:
            cov.skipped += 1
            cov.reason_counts[reason] = cov.reason_counts.get(reason, 0) + 1
        else:
            cov.eligible += 1
            candidates.append({'index': i, 'path': path, 'size': entry.size})
    selected = []; total = 0
    for item in sorted(candidates, key=lambda x: priority(x['path'])):
        reason = ('symlink' if item['index'] in (symlinks or set()) else
                  'file_bytes' if item['size'] > MAX_FILE_BYTES else
                  'file_count' if len(selected) >= MAX_FILES else
                  'total_bytes' if total + item['size'] > MAX_TOTAL_BYTES else '')
        if reason:
            cov.omitted += 1
            cov.reason_counts[reason] = cov.reason_counts.get(reason, 0) + 1
        else:
            selected.append(item); total += item['size']
    cov.partial = bool(cov.omitted)
    return selected, cov


def _snapshot(files: list[SourceFile], coverage: Coverage, name: str, source: str) -> Snapshot:
    if not any(PurePosixPath(f.path).suffix.lower() in SOURCE_SUFFIXES for f in files):
        raise IntakeError('분석할 지원 소스가 없습니다. Python / JavaScript / TypeScript / Dart 파일을 선택해 주세요.')
    coverage.analyzed = len(files)
    coverage.bytes_read = sum(len(f.content.encode('utf-8')) for f in files)
    coverage.partial = bool(coverage.omitted or coverage.failed)
    digest = hashlib.sha256()
    for f in sorted(files, key=lambda x: x.path):
        digest.update(f.path.encode()+b'\x00'+f.content.encode()+b'\x00')
    warnings = []
    if coverage.partial:
        warnings.append(f'부분 분석: 지원 후보 {coverage.eligible}개 중 {coverage.analyzed}개 분석, '
                        f'{coverage.omitted}개 제한 제외, {coverage.failed}개 읽기 실패.')
    return Snapshot(name=name, source=source, revision=digest.hexdigest(), files=files,
                    coverage=coverage, warnings=warnings)


def from_files(files: list[SourceFile], name: str = 'Local repository', source: str = 'files',
               *, manifest: list[FileMetadata] | None = None,
               read_failures: list[ReadFailure] | None = None) -> Snapshot:
    failures = read_failures or []
    paths = [valid_path(f.path) for f in files]
    if len(set(paths)) != len(paths):
        raise IntakeError('중복된 파일 경로입니다.')
    try:
        sizes = [len(f.content.encode('utf-8')) for f in files]
    except UnicodeError as exc:
        raise IntakeError('올바른 UTF-8 소스가 아닙니다.') from exc
    entries = manifest if manifest is not None else [
        FileMetadata(path=p, size=size) for p, size in zip(paths, sizes)]
    selected, cov = plan_files(entries, strip_root=manifest is not None)
    by_path = {p: f for p, f in zip(paths, files)}
    failed = {valid_path(f.path): f.reason for f in failures}
    if manifest is not None:
        picked = {item['path'] for item in selected}
        if (len(failed) != len(failures) or set(failed) & set(by_path)
                or set(by_path) | set(failed) != picked):
            raise IntakeError('전송 파일·읽기 실패 목록이 서버의 파일 선택 결과와 다릅니다.')
        if any(len(by_path[x['path']].content.encode('utf-8')) != x['size']
               for x in selected if x['path'] in by_path):
            raise IntakeError('파일 내용 크기가 선택 목록과 다릅니다.')
    elif failures:
        raise IntakeError('읽기 실패 목록에는 원본 파일 목록이 필요합니다.')
    accepted = []
    for item in selected:
        path = item['path']; reason = failed.get(path, '')
        f = by_path.get(path)
        if not reason and f is not None and '\x00' in f.content:
            reason = 'invalid_text'
        if reason:
            cov.failed += 1
            cov.reason_counts[reason] = cov.reason_counts.get(reason, 0) + 1
        else:
            accepted.append(SourceFile(path=path, content=f.content))
    snapshot = _snapshot(accepted, cov, name, source)
    if manifest is not None:
        cov.browser_selection = BrowserSelection(discovered=len(entries), transmitted=len(files),
            skipped=cov.skipped, omitted=cov.omitted, failed=cov.failed, reason_counts=dict(cov.reason_counts))
        cov.notes.append('폴더 발견 수·파일 크기·읽기 실패는 브라우저 보고입니다. 서버가 선택 정책과 전송 내용을 재검사했지만 로컬 디스크를 직접 검증하지는 않았습니다.')
    return snapshot


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
        # Never erase a security exclusion by treating it as an archive wrapper.
        if root.startswith('.') or SECRET.search(root) or root.lower() in EXCLUDED_PARTS:
            return {path: path for path in paths}
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
        selected, cov = plan_files([FileMetadata(path=p, size=i.file_size) for p, i in zip(paths, infos)],
            strip_root=True, symlinks={i for i, info in enumerate(infos) if _zip_member_is_symlink(info)})
        files = []
        for item in selected:
            info = infos[item['index']]
            reason = ''
            try:
                raw = archive.read(info)
                if len(raw) != info.file_size or b'\x00' in raw:
                    raise ValueError('invalid text member')
                files.append(SourceFile(path=item['path'], content=raw.decode('utf-8')))
            except (UnicodeError, ValueError):
                reason = 'invalid_text'
            except (RuntimeError, NotImplementedError, zipfile.BadZipFile, zlib.error, EOFError):
                reason = 'read_error'
            if reason:
                cov.failed += 1
                cov.reason_counts[reason] = cov.reason_counts.get(reason, 0) + 1
        name = PurePosixPath(filename or 'repository.zip').name.removesuffix('.zip') or 'ZIP repository'
        snapshot = _snapshot(files, cov, name, 'zip')
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
        if not isinstance(entries, list) or any(not isinstance(x, dict) for x in entries):
            raise IntakeError('예상하지 못한 GitHub 트리 형식입니다.')
        blobs = [x for x in entries if x.get('type') == 'blob']
        # Same server-owned metadata plan as folder/ZIP: decide BEFORE requests,
        # not after downloading 160 potentially-large blobs.
        try:
            metadata = [FileMetadata(path=x.get('path'), size=x.get('size')) for x in blobs]
        except ValueError as exc:
            raise IntakeError('GitHub 파일 경로·크기 메타데이터가 올바르지 않습니다.') from exc
        picked, cov = plan_files(metadata,
            symlinks={i for i, x in enumerate(blobs) if x.get('mode') == '120000'})
        semaphore = asyncio.Semaphore(4)

        async def fetch_one(item: dict) -> tuple[SourceFile | None, str]:
            x = blobs[item['index']]
            if not re.fullmatch(r'[a-fA-F0-9]{40}', str(x.get('sha', ''))):
                return None, 'read_error'
            async with semaphore:
                try:
                    blob = await self.get(prefix + '/git/blobs/' + x['sha'], limit=120000)
                    if blob.get('encoding') != 'base64' or not isinstance(blob.get('content'), str):
                        raise IntakeError('미지원 blob 인코딩')
                    encoded = re.sub(r'\s+', '', blob['content'])
                    raw = base64.b64decode(encoded, validate=True)
                    if len(raw) != item['size'] or len(raw) > MAX_FILE_BYTES:
                        raise IntakeError('blob 크기가 고정된 트리 메타데이터와 다릅니다.')
                except (ValueError, IntakeError):
                    return None, 'read_error'
                try:
                    if b'\x00' in raw:
                        return None, 'invalid_text'
                    return SourceFile(path=item['path'], content=raw.decode('utf-8')), ''
                except (UnicodeError, ValueError):
                    return None, 'invalid_text'

        fetched = await asyncio.gather(*(fetch_one(x) for x in picked))
        files = []; failures = []
        for item, (file, reason) in zip(picked, fetched):
            if reason:
                failures.append(item['path'])
                cov.failed += 1
                cov.reason_counts[reason] = cov.reason_counts.get(reason, 0) + 1
            else:
                files.append(file)
        snapshot = _snapshot(files, cov, f'{owner}/{repo}', 'github')
        snapshot.revision = sha
        snapshot.repository_url = f'https://github.com/{owner}/{repo}'
        cov.tree_truncated = bool(tree.get('truncated'))
        cov.partial = bool(cov.omitted or cov.failed or cov.tree_truncated)
        cov.notes.append('GitHub도 폴더·ZIP과 같은 메타데이터 계획으로 읽기 전에 파일 수·총 바이트를 제한합니다.')
        if failures:
            snapshot.warnings.append('읽기 실패: ' + ', '.join(failures[:6]))
        if cov.tree_truncated:
            snapshot.warnings.append('GitHub 파일 트리가 잘렸습니다. 전체 저장소 크기와 완전성을 알 수 없습니다.')
        return snapshot
