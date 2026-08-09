from pathlib import Path

from locust_templates.analysis_service import analyze_decision

FIX = Path(__file__).parents[1] / "fixtures" / "intelligence"


def test_shared_analysis_service_returns_report_and_canonical_decision():
    report, decision = analyze_decision(
        str(FIX / "run_b/run_b"),
        baseline_prefix=str(FIX / "run_a/run_a"),
        slos={"p95": 500},
        label="release",
        environment="test",
        branch="main",
        input_hashes={"stats": "abc"},
    )
    assert report.exit_code == 2
    assert decision["run"] == {"label": "release", "environment": "test", "branch": "main"}
    assert decision["inputs"] == {"stats": "abc"}
    assert decision["endpoint_comparison"] and decision["timeline"]["aligned"]
