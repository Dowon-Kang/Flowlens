"""Regression cases from the real-repository verification cycle."""
import asyncio
import io
import stat
import zipfile
import pytest
from app import intake
from app.intake import SourceFile, from_files, from_zip_bytes, IntakeError
from app.orchestrator import analyze_snapshot


def make_zip(items):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for path, data in items:
            z.writestr(path, data)
    return buf.getvalue()


def analyze(items):
    return asyncio.run(analyze_snapshot(from_files([SourceFile(path=p, content=c) for p,c in items])))


def test_typed_dio_request_and_multiline_evidence():
    result = analyze([
        ('mobile/lib/services/measurement.dart', "import 'package:dio/dio.dart';\nFuture<void> load() async {\n  _dio.get<Map<String, dynamic>>(\n    '/v1/participants/me/vitals',\n  );\n}\n"),
        ('backend/routes/measurement.ts', "import { Hono } from 'hono';\nconst app = new Hono();\napp.get('/v1/participants/me/vitals', c => c.json([]));\n"),
    ])
    requests = [f for f in result.facts if f.kind == 'request']
    assert len(requests) == 1
    assert requests[0].value == '/v1/participants/me/vitals'
    edges = [e for e in result.edges if e.relation == 'http-contract']
    assert len(edges) == 1 and edges[0].confidence == 'candidate'
    assert '/v1/participants/me/vitals' in next(e.snippet for e in result.evidence if e.id == requests[0].evidence_id)


def test_multiline_import():
    result=analyze([('backend/index.ts', "import {\n  Hono\n} from 'hono';\nconst app = new Hono();\n")])
    assert any(f.kind == 'import' and f.value == 'hono' for f in result.facts)
    assert any(n.label == 'Hono Backend' for n in result.system_nodes)


def test_fake_typed_requests_ignored():
    result=analyze([('client/service.dart', '''import 'package:dio/dio.dart';
// _dio.get<Map<String, dynamic>>('/fake');
final text = "_dio.get<Map<String, dynamic>>('/fake-too')";
''')])
    assert not [f for f in result.facts if f.kind == 'request']


def test_storage_before_helpers():
    assert intake.priority('backend/src/storage/postgres-database.ts') < intake.priority('backend/src/services/zz-helper.ts')


def test_oversized_coverage():
    snap=from_zip_bytes(make_zip([('repo/main.py','x=1'),('repo/big.py','x'*(intake.MAX_FILE_BYTES+1)),('repo/README.md','# ignored')]))
    c=snap.coverage
    assert c.eligible==2 and c.omitted==1 and c.analyzed==1
    assert c.discovered==c.analyzed+c.skipped+c.omitted+c.failed
    assert c.partial


def test_zip_decompression_budget(monkeypatch):
    data=make_zip([(f'repo/src/f{i}.py','x=1') for i in range(4)])
    monkeypatch.setattr(intake,'MAX_FILES',2)
    original=zipfile.ZipFile.read
    reads=[]
    def tracked(self, member, *args, **kwargs):
        reads.append(member)
        return original(self,member,*args,**kwargs)
    monkeypatch.setattr(zipfile.ZipFile,'read',tracked)
    snap=from_zip_bytes(data)
    assert len(reads)<=2
    assert snap.coverage.omitted==2 and snap.coverage.partial


def test_symlink_coverage():
    link=zipfile.ZipInfo('repo/link.py')
    link.create_system=3
    link.external_attr=(stat.S_IFLNK|0o777)<<16
    c=from_zip_bytes(make_zip([('repo/main.py','x=1'),(link,'main.py')])).coverage
    assert c.eligible==2 and c.omitted==1
    assert c.discovered==c.analyzed+c.skipped+c.omitted+c.failed


def test_unsupported_compression(monkeypatch):
    data=make_zip([('repo/main.py','x=1')])
    def unsupported(*args,**kwargs): raise NotImplementedError('unsupported compression')
    monkeypatch.setattr(zipfile.ZipFile,'read',unsupported)
    with pytest.raises(IntakeError): from_zip_bytes(data)


def test_duplicate_ignored_paths():
    with pytest.warns(UserWarning):
        data=make_zip([('repo/main.py','x=1'),('repo/README.md','one'),('repo/README.md','two')])
    with pytest.raises(IntakeError): from_zip_bytes(data)


def test_overview_budget_includes_user():
    result=analyze([('backend/main.py','\n'.join(['import fastapi','import psycopg','import redis','import sqlite3','import openai','import supabase','import requests',*[f"requests.get('https://service{i}.example/items')" for i in range(6)]]))])
    assert len(result.system_nodes)<=8
