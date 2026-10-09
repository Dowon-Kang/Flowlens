"""Regression captured by actual remote Chromium, not a mock browser run."""


def test_browser_guard_assertions_read_svg_text_content_not_inner_text():
    """Regression from actual Chromium: SVG does not implement HTMLElement.innerText."""
    from pathlib import Path
    source=Path('scripts/browser_smoke.py').read_text()
    assert "page.locator('#graph').inner_text()" not in source
    assert "assert '[true]' in page.locator('#graph').text_content()" in source
    assert "assert '[false]' in page.locator('#graph').text_content()" in source
