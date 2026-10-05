"""One-time, reviewed v0.2.0 -> v0.2.1 source migration. Remove after validation."""
from pathlib import Path
import hashlib
root=Path(__file__).resolve().parents[1]
expected={'app/intake.py':'9ea07df3d062405c50ebe2ad9ee5bda0cf75c04868d3a44fa82f3608f03dd0d2','app/extractor.py':'ee4347f2cfb7eba05d201cda0486d279e53b75c102a6f708e082f7666afdcb6e','app/graph.py':'bceca7421e44cafcd9ba15f647f3f1ff2723aa275f3fb170367e4fa255a066b4','app/models.py':'6b006e8f755a3ba1480a392e2752a0b46096b14df4f2bacc92a0141bb764bcd8','app/main.py':'08d6238b4632e3d5efd36ef01923c74aff28cdc747d2770c53542c64bde1b088','app/__init__.py':'de19b0936dfaa3392f5034543fd09b2a702e7b42eeece997759adb8ac866b1f0','scripts/browser_smoke.py':'069527f81a4b34bef73f74900b7e519dde1fe4752540d3dc29d5f264284b0a8c'}
for name,digest in expected.items():
    if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Refusing to patch changed baseline: '+name)
p=root/'app/intake.py'; s=p.read_text(); s=s.replace('import zipfile\n','import zipfile\nimport zlib\n')
s=s.replace("elif re.search(r'(^|/)(main|index|app)\\.(py|tsx?|jsx?|dart)$', p):", "elif re.search(r'(^|/)(main|index|app|server|node-server|runtime|providers)\\.(py|tsx?|jsx?|dart)$', p):")
s=s.replace("elif 'route' in p:\n        rank = 2", "elif re.search(r'route|controller|provider|/storage/|/(algorithm|auth)\\.', p):\n        rank = 2")
s=s.replace('candidates.append(item)', 'candidates.append(SourceFile(path=path, content=item.content))')
start=s.index('def from_zip_bytes(');end=s.index('\ndef load_demo(',start)
s=s[:start]+'''def from_zip_bytes(data: bytes, filename: str = 'repository.zip') -> Snapshot:
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
            path = valid_path(info.orig_filename.replace('\\\\', '/'))
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
                if len(raw) != info.file_size or b'\\x00' in raw:
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
''' + s[end:]
s=s.replace('로컬 폴더 분석을 사용할 수 있습니다.', 'ZIP 또는 로컬 폴더 분석을 사용할 수 있습니다.').replace('로컬 폴더를 사용해 주세요.', 'ZIP 또는 로컬 폴더를 사용해 주세요.')
p.write_text(s)
p=root/'app/extractor.py';s=p.read_text().replace(r'\b(?:import|export)\s+[^;\n]*?\bfrom',r'\b(?:import|export)\s+[^;]{1,3000}?\bfrom').replace(r'(get|post|put|patch|delete|options|head)\s*\(',r'(get|post|put|patch|delete|options|head)\s*(?:<[^;()]{1,200}>)?\s*\(')
s=s.replace("'import',m.group(1),'lexical')", "'import',m.group(1),'lexical',end_line=text.count('\\n',0,m.end())+1)").replace("value,'lexical',method.upper())", "value,'lexical',method.upper(),end_line=text.count('\\n',0,m.end())+1)")
p.write_text(s)
p=root/'app/graph.py';s=p.read_text().replace('if len(system_nodes)>8:', 'if len(system_nodes)>7:').replace('8-(len(system_nodes)-len(infra_nodes))-1','7-(len(system_nodes)-len(infra_nodes))-1');p.write_text(s)
p=root/'app/__init__.py';p.write_text(p.read_text().replace('0.2.0','0.2.1'))
p=root/'app/models.py';p.write_text(p.read_text().replace('from typing import Literal','from typing import Literal\nfrom . import __version__').replace('analyzer_version: str = "0.2.0"','analyzer_version: str = __version__'))
p=root/'app/main.py';s=p.read_text().replace('        snapshot=from_zip_bytes(bytes(raw), filename=filename)\n','').replace('            async with asyncio.timeout(140):\n                result=await analyze_snapshot(snapshot, explain)','            async with asyncio.timeout(140):\n                snapshot=await asyncio.to_thread(from_zip_bytes, bytes(raw), filename)\n                result=await analyze_snapshot(snapshot, explain)');p.write_text(s)
p=root/'scripts/browser_smoke.py';s=p.read_text().replace("parser.add_argument('--url',default='http://127.0.0.1:8000')", "parser.add_argument('--url',default='http://127.0.0.1:8000')\n    parser.add_argument('--output',default=str(ROOT/'evidence'))").replace("args=parser.parse_args(); out=ROOT/'evidence';out.mkdir(exist_ok=True)", "args=parser.parse_args(); out=Path(args.output);out.mkdir(parents=True,exist_ok=True)")
s=s.replace("content=options.get('body'))", "content=bytes(options['body']) if isinstance(options.get('body'),list) else options.get('body'))").replace('body:opts.body});return new Response','body:opts.body instanceof Blob?Array.from(new Uint8Array(await opts.body.arrayBuffer())):opts.body});return new Response')
s=s.replace('        if not args.bridge:\n            with tempfile.TemporaryDirectory() as td:', '        if True:  # Both modes test selected ZIP bytes.\n            with tempfile.TemporaryDirectory() as td:')
p.write_text(s)
