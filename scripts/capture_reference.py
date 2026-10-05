"""Read a public repository as data for acceptance; never execute its files."""
from __future__ import annotations
import argparse,asyncio,os,sys
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.intake import GitHubReader
async def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='https://github.com/Dowon-Kang/vibecare-pilot');p.add_argument('--output',default='evidence/reference/snapshot.json');a=p.parse_args()
    headers={'Accept':'application/vnd.github+json','User-Agent':'FlowLens-Acceptance'}
    if os.getenv('GITHUB_TOKEN'):headers['Authorization']='Bearer '+os.environ['GITHUB_TOKEN']
    async with httpx.AsyncClient(headers=headers,timeout=20,trust_env=False) as client:s=await GitHubReader(client).read(a.url)
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(s.model_dump_json(),encoding='utf-8');print(s.revision,s.coverage.model_dump())
if __name__=='__main__':asyncio.run(main())
