from pathlib import Path

from locust_templates.comparison_view import render_comparison
from locust_templates.decision_artifact import build_decision
from locust_templates.intelligence import analyze_run

FIX=Path(__file__).parents[1]/"fixtures/intelligence"
def test_us004_accessible_chart_table_and_compatibility():
    report=analyze_run(str(FIX/"run_b/run_b"),baseline_prefix=str(FIX/"run_a/run_a"),slos={"p95":500})
    html=render_comparison(build_decision(report))
    assert 'role="img"' in html and '<title id="timeline-title">' in html
    assert 'View accessible timeline data' in html and '<caption>Timeline data' in html
    assert '<caption>Current run compared with baseline</caption>' in html
    assert 'Baseline compatibility' in html and 'Percent delta' in html
