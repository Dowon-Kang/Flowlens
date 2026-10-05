"""Small deterministic skill-format check; not a certification of skill quality."""
from pathlib import Path
import re
ROOT=Path(__file__).resolve().parents[1]
paths=sorted((ROOT/'.agents/skills').glob('*/SKILL.md'))
assert len(paths)==2, 'This MVP deliberately has exactly two project-specific skills.'
for path in paths:
    text=path.read_text(encoding='utf-8')
    assert text.startswith('---\n'), path
    header=text.split('---',2)[1]
    match=re.search(r'^name: ([a-z0-9-]+)$',header,re.M)
    assert match and match[1]==path.parent.name, path
    assert re.search(r'^description: .+',header,re.M), path
    assert len(text)<12000, 'Keep skill procedures focused.'
assert (ROOT/'AGENTS.md').exists()
assert (ROOT/'app/orchestrator.py').exists()
print('PASS: 2 focused Skills, names/descriptions and runtime separation checked.')
