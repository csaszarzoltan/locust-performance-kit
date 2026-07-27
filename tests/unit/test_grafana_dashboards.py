"""Pre-development tests for Grafana Dashboard JSON templates.

Interface tests verify that all three dashboard JSON files exist and are
valid JSON. Behavioral tests verify the required panel titles, data source
references, and tags.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GRAFANA_DIR = REPO_ROOT / "grafana" / "dashboards"

DASHBOARD_FILES = [
    "locust-overview.json",
    "locust-traces.json",
    "locust-combined.json",
]


@pytest.fixture(scope="module")
def dashboards() -> dict[str, dict]:
    """Parse and cache all dashboards once per module."""
    result: dict[str, dict] = {}
    for filename in DASHBOARD_FILES:
        with open(GRAFANA_DIR / filename) as f:
            result[filename] = json.load(f)
    return result


# ──────────────────────────────────────────────────────────────
# Interface smoke tests
# ──────────────────────────────────────────────────────────────


class TestInterfaceSmoke:
    """Verify that all dashboard JSON files exist and are valid JSON."""

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_file_exists(self, filename):
        """Each dashboard JSON file must exist."""
        path = GRAFANA_DIR / filename
        assert path.exists(), f"Dashboard file not found: {path}"

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_is_valid_json(self, filename):
        """Each dashboard file must parse as valid JSON."""
        path = GRAFANA_DIR / filename
        with open(path) as f:
            data = json.load(f)
        assert isinstance(data, dict)

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_has_title(self, filename):
        """Each dashboard must have a 'title' key."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert "title" in data
        assert isinstance(data["title"], str)
        assert len(data["title"]) > 0

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_has_uid(self, filename):
        """Each dashboard must have a 'uid' key."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert "uid" in data
        assert isinstance(data["uid"], str)
        assert data["uid"].startswith("locust-")

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_has_tags(self, filename):
        """Each dashboard must have a 'tags' list."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert "tags" in data
        assert isinstance(data["tags"], list)

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_has_panels(self, filename):
        """Each dashboard must have a 'panels' list."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert "panels" in data
        assert isinstance(data["panels"], list)

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_has_schema_version(self, filename):
        """Each dashboard must have a schemaVersion (Grafana v8+)."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert "schemaVersion" in data
        assert isinstance(data["schemaVersion"], int)
        assert data["schemaVersion"] >= 30  # Grafana v8+

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_is_editable(self, filename):
        """Each dashboard must be editable (editable: true)."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert data.get("editable", False) is True

    @pytest.mark.parametrize("filename", DASHBOARD_FILES)
    def test_dashboard_has_timezone(self, filename):
        """Each dashboard must have timezone setting."""
        with open(GRAFANA_DIR / filename) as f:
            data = json.load(f)
        assert "timezone" in data
        assert data["timezone"] == "browser"

    def test_all_uids_unique(self, dashboards):
        """All dashboard UIDs must be unique."""
        uids = [data["uid"] for data in dashboards.values()]
        assert len(uids) == len(set(uids)), (
            f"Duplicate UIDs found: {uids}"
        )


# ──────────────────────────────────────────────────────────────
# Behavioral tests — dashboard content and semantics
# ──────────────────────────────────────────────────────────────


class TestDashboardContentBehavior:
    """Behavioral tests for dashboard content and semantics."""

    def test_locust_overview_has_required_panels(self, dashboards):
        """locust-overview.json must have panels for Active Users,
        RPS, Latency, Error Rate."""
        overview = dashboards["locust-overview.json"]
        panel_titles = [p["title"] for p in overview["panels"]]
        required = ["Active Users", "RPS", "Latency", "Error Rate"]
        # Check that panel titles contain the required keywords
        title_text = " ".join(panel_titles)
        for req in required:
            assert req.lower() in title_text.lower(), (
                f"locust-overview missing panel containing '{req}'"
            )

    def test_locust_overview_panels_use_prometheus(self, dashboards):
        """locust-overview.json panels must query Prometheus data source."""
        overview = dashboards["locust-overview.json"]
        for panel in overview["panels"]:
            ds = panel.get("datasource", {})
            ds_type = ds.get("type", "")
            assert ds_type == "prometheus", (
                f"Panel '{panel['title']}' must use prometheus datasource, "
                f"got '{ds_type}'"
            )

    def test_locust_overview_has_p95_latency_panel(self, dashboards):
        """locust-overview.json must have a p95 Latency panel with PromQL expression."""
        overview = dashboards["locust-overview.json"]
        panel_titles = [p["title"] for p in overview["panels"]]
        has_p95 = any("p95" in t.lower() for t in panel_titles)
        assert has_p95, (
            "locust-overview must have a panel containing 'p95' in title"
        )

    def test_locust_overview_has_p99_latency_panel(self, dashboards):
        """locust-overview.json must have a p99 Latency panel with PromQL expression."""
        overview = dashboards["locust-overview.json"]
        panel_titles = [p["title"] for p in overview["panels"]]
        has_p99 = any("p99" in t.lower() for t in panel_titles)
        assert has_p99, (
            "locust-overview must have a panel containing 'p99' in title"
        )

    def test_locust_overview_has_error_rate_panel(self, dashboards):
        """locust-overview.json must have an Error Rate panel."""
        overview = dashboards["locust-overview.json"]
        panel_titles = [p["title"] for p in overview["panels"]]
        has_error = any("error" in t.lower() for t in panel_titles)
        assert has_error, (
            "locust-overview must have a panel containing 'Error' in title"
        )

    def test_locust_overview_has_top_slow_endpoints_table(self, dashboards):
        """locust-overview.json must have a Top Slow Endpoints table."""
        overview = dashboards["locust-overview.json"]
        panel_titles = [p["title"] for p in overview["panels"]]
        has_slow = any("slow" in t.lower() for t in panel_titles)
        assert has_slow, (
            "locust-overview must have a 'Top Slow Endpoints' panel"
        )

    def test_locust_overview_has_failure_hotspots_table(self, dashboards):
        """locust-overview.json must have a Failure Hotspots table."""
        overview = dashboards["locust-overview.json"]
        panel_titles = [p["title"] for p in overview["panels"]]
        has_failure = any("failure" in t.lower() for t in panel_titles)
        assert has_failure, (
            "locust-overview must have a 'Failure Hotspots' panel"
        )

    def test_locust_traces_has_service_graph(self, dashboards):
        """locust-traces.json must have a Service Graph panel."""
        traces = dashboards["locust-traces.json"]
        panel_titles = [p["title"] for p in traces["panels"]]
        has_graph = any(
            "service" in t.lower() and "graph" in t.lower()
            for t in panel_titles
        )
        assert has_graph, (
            "locust-traces must have a 'Service Graph' panel"
        )

    def test_locust_traces_has_trace_list(self, dashboards):
        """locust-traces.json must have a Trace List panel."""
        traces = dashboards["locust-traces.json"]
        panel_titles = [p["title"] for p in traces["panels"]]
        has_trace_list = any(
            "trace" in t.lower() and "list" in t.lower()
            for t in panel_titles
        )
        assert has_trace_list, (
            "locust-traces must have a 'Trace List' panel"
        )

    def test_locust_traces_uses_tempo_or_jaeger(self, dashboards):
        """locust-traces.json panels must reference Tempo or Jaeger data source."""
        traces = dashboards["locust-traces.json"]
        for panel in traces["panels"]:
            ds = panel.get("datasource", {})
            ds_type = ds.get("type", "")
            assert ds_type in ("tempo", "jaeger"), (
                f"Panel '{panel['title']}' must use tempo/jaeger datasource, "
                f"got '{ds_type}'"
            )

    def test_locust_traces_has_span_duration_heatmap(self, dashboards):
        """locust-traces.json must have a Span Duration Heatmap panel."""
        traces = dashboards["locust-traces.json"]
        panel_titles = [p["title"] for p in traces["panels"]]
        has_heatmap = any(
            "heatmap" in t.lower() or "duration" in t.lower()
            for t in panel_titles
        )
        assert has_heatmap, (
            "locust-traces must have a 'Span Duration Heatmap' or similar panel"
        )

    def test_locust_traces_has_error_spans_list(self, dashboards):
        """locust-traces.json must have an Error Spans list panel."""
        traces = dashboards["locust-traces.json"]
        panel_titles = [p["title"] for p in traces["panels"]]
        has_error_spans = any(
            "error" in t.lower() and "span" in t.lower()
            for t in panel_titles
        )
        # Also check for just "error" in a list
        if not has_error_spans:
            has_error_spans = any("error" in t.lower() for t in panel_titles)
        assert has_error_spans, (
            "locust-traces must have an 'Error Spans' panel"
        )

    def test_locust_combined_has_both_metrics_and_traces(self, dashboards):
        """locust-combined.json must combine Prometheus metrics
        and Tempo/Jaeger traces."""
        combined = dashboards["locust-combined.json"]
        panel_ds_types = [
            p.get("datasource", {}).get("type", "") for p in combined["panels"]
        ]
        has_prometheus = "prometheus" in panel_ds_types
        has_tempo = "tempo" in panel_ds_types or "jaeger" in panel_ds_types
        assert has_prometheus, (
            "locust-combined must have Prometheus panels"
        )
        assert has_tempo, (
            "locust-combined must have Tempo/Jaeger trace panels"
        )

    def test_locust_combined_has_system_resource_panels(self, dashboards):
        """locust-combined.json must include CPU/memory/network panels."""
        combined = dashboards["locust-combined.json"]
        panel_titles = [p["title"] for p in combined["panels"]]
        title_text = " ".join(panel_titles)
        assert "CPU" in title_text or "cpu" in title_text.lower(), (
            "locust-combined must have a CPU panel"
        )
        assert "Memory" in title_text or "memory" in title_text.lower(), (
            "locust-combined must have a Memory panel"
        )
        assert "Network" in title_text or "network" in title_text.lower(), (
            "locust-combined must have a Network panel"
        )

    def test_all_dashboards_have_locust_tag(self, dashboards):
        """All dashboards must have 'locust' in their tags list."""
        for filename, data in dashboards.items():
            tags = [t.lower() for t in data.get("tags", [])]
            assert "locust" in tags, (
                f"{filename} missing 'locust' tag, got tags={tags}"
            )

    def test_all_dashboards_have_performance_tag(self, dashboards):
        """All dashboards must have 'performance-testing' in their tags list."""
        for filename, data in dashboards.items():
            tags = [t.lower() for t in data.get("tags", [])]
            assert "performance-testing" in tags, (
                f"{filename} missing 'performance-testing' tag, got tags={tags}"
            )

    def test_all_dashboards_have_observability_tag(self, dashboards):
        """All dashboards must have 'observability' in their tags list."""
        for filename, data in dashboards.items():
            tags = [t.lower() for t in data.get("tags", [])]
            assert "observability" in tags, (
                f"{filename} missing 'observability' tag, got tags={tags}"
            )

    def test_dashboards_have_templating_variables(self, dashboards):
        """Dashboards must have datasource and environment template variables."""
        for filename, data in dashboards.items():
            templating = data.get("templating", {}).get("list", [])
            var_names = [v.get("name", "") for v in templating]
            assert "datasource" in var_names, (
                f"{filename} missing 'datasource' template variable"
            )
            assert "environment" in var_names, (
                f"{filename} missing 'environment' template variable"
            )

    def test_dashboards_environment_variable_defaults_to_production(self, dashboards):
        """$environment variable must default to 'production'."""
        for filename, data in dashboards.items():
            templating = data.get("templating", {}).get("list", [])
            env_vars = [v for v in templating if v.get("name") == "environment"]
            assert len(env_vars) == 1, (
                f"{filename} must have exactly one 'environment' variable"
            )
            assert env_vars[0].get("query") == "production", (
                f"{filename} environment variable must default to 'production'"
            )

    def test_dashboards_null_handling_defaults(self, dashboards):
        """Dashboard panels must have fieldConfig defaults to prevent broken panels."""
        for filename, data in dashboards.items():
            for panel in data.get("panels", []):
                field_config = panel.get("fieldConfig", {})
                assert field_config, (
                    f"Panel '{panel['title']}' in {filename} must have 'fieldConfig' "
                    f"for null-value handling"
                )
