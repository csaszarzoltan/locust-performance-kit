"""US-001..US-006 browser RC flows; run with Playwright Chromium."""
from __future__ import annotations

import os
import zipfile
from pathlib import Path

import pytest

if os.getenv("LPK_RUN_E2E") != "1":
    pytest.skip("set LPK_RUN_E2E=1 for browser RC validation", allow_module_level=True)

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Page, expect

FIXTURES = Path(__file__).parents[1] / "fixtures" / "intelligence"
BASE = os.getenv("LPK_E2E_BASE_URL", "http://127.0.0.1:8080")
SHOTS = Path(os.getenv("LPK_SCREENSHOT_DIR", "screenshots"))


def _zip(folder: Path, output: Path, *, duplicate: bool = False) -> Path:
    with zipfile.ZipFile(output, "w") as archive:
        for prefix in (("one", "two") if duplicate else ("",)):
            for source in folder.iterdir():
                archive.write(source, f"{prefix}/{source.name}" if prefix else source.name)
    return output


def _axe(page: Page) -> None:
    axe = Path(os.getenv("AXE_CORE_PATH", "node_modules/axe-core/axe.min.js"))
    if not axe.is_file():
        pytest.fail(f"axe-core missing: {axe}")
    page.add_script_tag(content=axe.read_text())
    result = page.evaluate("async () => await axe.run(document, {runOnly: {type:'tag', values:['wcag2a','wcag2aa','wcag22aa']}})")
    serious = [item for item in result["violations"] if item.get("impact") in {"critical", "serious"}]
    assert serious == []


def _shot(page: Page, name: str) -> None:
    SHOTS.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(SHOTS / name), full_page=True)
    _axe(page)


@pytest.mark.parametrize("viewport", [{"width": 360, "height": 800}, {"width": 768, "height": 1024}, {"width": 1440, "height": 900}])
def test_us001_us003_responsive_empty_sample(page: Page, viewport: dict[str, int]):
    page.set_viewport_size(viewport)
    page.goto(f"{BASE}/workspace/runs")
    expect(page.get_by_role("heading", name="Runs")).to_be_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    _shot(page, f"inbox-{viewport['width']}.png")
    page.get_by_role("link", name="Try sample run").click()
    page.get_by_role("button", name="Load sample").click()
    expect(page.get_by_role("heading", name="Sample: regressed checkout API")).to_be_visible()


def test_us001_import_ambiguity_error_and_recovery(page: Page, tmp_path: Path):
    ambiguous = _zip(FIXTURES / "run_a", tmp_path / "ambiguous.zip", duplicate=True)
    page.goto(f"{BASE}/workspace/runs/import")
    _shot(page, "import.png")
    page.locator("input[type=file]").set_input_files(str(ambiguous))
    page.get_by_role("button", name="Validate run").click()
    expect(page.get_by_role("heading", name="Review detected run")).to_be_visible()
    expect(page.locator("input[name=candidate]")).to_have_count(2)
    _shot(page, "ambiguous-preview.png")

    traversal = tmp_path / "traversal.zip"
    with zipfile.ZipFile(traversal, "w") as archive:
        archive.writestr("../escape", "x")
    page.goto(f"{BASE}/workspace/runs/import")
    page.locator("input[type=file]").set_input_files(str(traversal))
    page.get_by_role("button", name="Validate run").click()
    expect(page.get_by_role("alert")).to_contain_text("ARCHIVE_PATH_UNSAFE")
    _shot(page, "validation-error.png")


def test_us004_us006_fail_comparison_timeline_downloads(page: Page):
    page.goto(f"{BASE}/workspace/sample")
    page.get_by_role("button", name="Load sample").click()
    expect(page.get_by_text("FAIL", exact=True).first).to_be_visible()
    expect(page.get_by_role("heading", name="Baseline compatibility")).to_be_visible()
    expect(page.get_by_role("heading", name="Endpoint comparison")).to_be_visible()
    expect(page.locator("svg[role=img]")).to_be_visible()
    page.get_by_text("View accessible timeline data").click()
    expect(page.get_by_text("Timeline data in elapsed seconds")).to_be_visible()
    _shot(page, "fail-comparison-timeline.png")
    with page.expect_download() as download:
        page.get_by_role("link", name="Download decision JSON").click()
    assert download.value.suggested_filename.endswith("decision.json")
    with page.expect_download() as download:
        page.get_by_role("link", name="Download Markdown").click()
    assert download.value.suggested_filename.endswith("summary.md")
