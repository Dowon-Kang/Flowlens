import pytest
from app.intake import parse_github_url,from_files,eligible_path,IntakeError
from app.models import SourceFile
from app.extractor import extract_facts

@pytest.mark.parametrize('url',['http://github.com/a/b','https://github.com.evil.test/a/b','https://github.com@evil.test/a/b','https://github.com:443/a/b','https://localhost/a/b','https://github.com/a/b/tree/main','https://github.com/a/b?x=1'])
def test_reject_unsafe_urls(url):
    with pytest.raises(IntakeError): parse_github_url(url)

def test_valid_github_url():
    assert parse_github_url('https://github.com/openai/codex.git')==('openai','codex')

@pytest.mark.parametrize('path',['../secret.py','/etc/passwd','foo/../../bar.py','C:/Users/file.py','foo\\bar.py'])
def test_path_escape_rejected(path):
    with pytest.raises(IntakeError): from_files([SourceFile(path=path,content='x=1')])

@pytest.mark.parametrize('path',['.env','.env.local','config/secrets.json','node_modules/evil.js','tests/main.py','src/main.test.ts','src/file.g.dart','venv/module.py'])
def test_sensitive_and_generated_files_not_eligible(path):
    assert not eligible_path(path)

def test_comments_and_strings_do_not_create_imports():
    text='''// import x from './fake';
const message = "import y from './also-fake'";
/* app.post('/fake', () => {}); */
import { Hono } from 'hono';
const app = new Hono();
app.get('/real', () => {});
'''
    s=from_files([SourceFile(path='server/index.ts',content=text)])
    facts,_,_=extract_facts(s)
    assert [x.value for x in facts if x.kind=='import']==['hono']
    assert [x.value for x in facts if x.kind=='route']==['/real']

def test_reject_duplicate_path():
    with pytest.raises(IntakeError):
        from_files([SourceFile(path='a.py',content='x=1'),SourceFile(path='a.py',content='x=2')])

def test_limits_are_disclosed():
    files=[SourceFile(path=f'src/m{i}.py',content='x=1') for i in range(170)]
    s=from_files(files)
    assert s.coverage.analyzed==160 and s.coverage.omitted==10 and s.coverage.partial
