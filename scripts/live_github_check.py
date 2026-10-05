"""Manual network check for FlowLens GitHub intake.

This script is intentionally not part of the default test suite because CI/sandboxes
may block outbound DNS. It performs read-only GitHub API requests and never executes
repository code.
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
import httpx
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.intake import GitHubReader, IntakeError
from app.orchestrator import analyze_snapshot

async def main(url: str) -> int:
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'FlowLens-live-check',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if os.getenv('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15, connect=6), headers=headers, trust_env=False) as client:
            snapshot = await GitHubReader(client).read(url)
        result = await analyze_snapshot(snapshot)
    except IntakeError as exc:
        print(json.dumps({'ok': False, 'url': url, 'error': str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps({
        'ok': True,
        'url': url,
        'name': result.name,
        'revision': result.revision,
        'coverage': result.coverage.model_dump(),
        'system_nodes': [n.label for n in result.system_nodes],
        'features': [f.label for f in result.features],
        'warnings': result.warnings,
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('url', nargs='?', default='https://github.com/Dowon-Kang/vibecare-pilot')
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.url)))
