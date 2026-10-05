"""Fix readiness checks without relaxing the application's Content Security Policy."""
from pathlib import Path
p=Path('scripts/browser_smoke.py')
s=p.read_text(encoding='utf-8').replace('from playwright.sync_api import sync_playwright','from playwright.sync_api import sync_playwright, expect')
replacements={
    'page.wait_for_function("document.querySelector(\'#repoName\').textContent.includes(\'TaskBoard\')")': 'expect(page.locator("#repoName")).to_contain_text("TaskBoard")',
    'page.wait_for_function("document.querySelector(\'#sourceBadge\').textContent === \'Local files\'")': 'expect(page.locator("#sourceBadge")).to_have_text("Local files")',
    'page.wait_for_function("document.querySelector(\'#sourceBadge\').textContent === \'ZIP archive\'")': 'expect(page.locator("#sourceBadge")).to_have_text("ZIP archive")',
    'page.wait_for_function("document.querySelector(\'#repoName\').textContent.includes(\'FlowCare\')")': 'expect(page.locator("#repoName")).to_contain_text("FlowCare")',
}
for before,after in replacements.items():
    if s.count(before)!=1:raise SystemExit('Unexpected browser test baseline')
    s=s.replace(before,after)
p.write_text(s,encoding='utf-8')
