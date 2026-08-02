"""Interactive HTML report renderer.

Renders the report model as a self-contained HTML dashboard: an executive summary,
then sections for run and dataset facts, validation, quality (with an analytical
bar chart of dimension scores), change detection, provenance, artefacts, errors,
warnings and performance. The chart is inline SVG built from the data, not a
decorative image -- it exists to compare dimension scores at a glance -- and the
page carries no external scripts or network calls, so it stays usable offline
after the run.

Every value that originated outside the framework -- field messages, source URIs,
error text -- is HTML-escaped through :func:`html.escape` before it reaches the
page, so a malicious extracted value cannot inject markup or script. That escaping
is the single most important line of defence in this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from html import escape
from pathlib import Path

from nexusai.domain.model.persistence import ReportManifest
from nexusai.domain.model.report import Report
from nexusai.infrastructure.reporting.writer import (
    atomic_output,
    build_report_manifest,
    resolve_target,
)
from nexusai.shared.types import JsonValue

_VERSION = "1.0"


def _as_float(value: JsonValue) -> float:
    """Coerce a JSON value to a float, defaulting to 0.0 for non-numerics."""
    return float(value) if isinstance(value, (int, float)) else 0.0


class HtmlReportRenderer:
    """Renders a report as a self-contained interactive HTML dashboard."""

    report_format = "html"
    media_type = "text/html"

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def render(self, report: Report, destination: str) -> ReportManifest:
        """Write ``report`` as HTML and return the manifest."""
        html = _render_document(report)
        with atomic_output(self._base, destination) as temp:
            temp.write_text(html, encoding="utf-8")
        return build_report_manifest(
            resolve_target(self._base, destination),
            dataset_id=report.dataset.dataset_id,
            dataset_version=report.dataset.version,
            report_format=self.report_format,
            media_type=self.media_type,
            generator_version=_VERSION,
        )


def _render_document(report: Report) -> str:
    sections = "\n".join(
        [
            _executive_summary(report),
            _dataset_section(report),
            _validation_section(report),
            _quality_section(report),
            _change_section(report),
            _rendering_section(report),
            _provenance_section(report),
            _artifacts_section(report),
            _issues_section("Errors", report.errors),
            _issues_section("Warnings", report.warnings),
            _performance_section(report),
        ]
    )
    subtitle = (
        f"Generated {escape(report.generated_at.isoformat())} "
        f"&middot; framework {escape(report.framework_version)}"
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus AI Report {escape(report.dataset.dataset_id)}</title>
<style>{_STYLE}</style>
</head>
<body>
<header><h1>Nexus AI Data Report</h1>
<p class="sub">{subtitle}</p>
</header>
<main>{sections}</main>
</body>
</html>
"""


def _card(label: str, value: str, tone: str = "") -> str:
    return (
        f'<div class="card {tone}">'
        f'<span class="label">{escape(label)}</span>'
        f'<span class="value">{escape(value)}</span></div>'
    )


def _executive_summary(report: Report) -> str:
    status = report.validation.status
    tone = {"PASS": "ok", "WARNING": "warn", "FAIL": "bad"}.get(status, "")
    cards = "".join(
        [
            _card("Records", str(report.dataset.record_count)),
            _card("Validation", status, tone),
            _card("Quality grade", report.quality.grade or "n/a"),
            _card("Composite score", f"{report.quality.composite_score:.3f}"),
            _card("Changes", str(report.change.total)),
            _card("Sources", str(report.dataset.source_count)),
        ]
    )
    return f'<section><h2>Executive Summary</h2><div class="cards">{cards}</div></section>'


def _dataset_section(report: Report) -> str:
    rows = [
        ("Dataset ID", report.dataset.dataset_id),
        ("Version", str(report.dataset.version)),
        ("Run ID", report.run.run_id or "n/a"),
        ("Fields", str(report.dataset.field_count)),
    ]
    return f"<section><h2>Dataset &amp; Run</h2>{_kv_table(rows)}</section>"


def _validation_section(report: Report) -> str:
    v = report.validation
    counts = _kv_table(
        [
            ("Status", v.status),
            ("Passing", str(v.passing_records)),
            ("Warnings", str(v.warning_records)),
            ("Failing", str(v.failing_records)),
        ]
    )
    if v.issues:
        header = "<tr><th>Code</th><th>Severity</th><th>Message</th><th>Location</th></tr>"
        body = "".join(
            f"<tr><td>{escape(str(i.get('code','')))}</td>"
            f"<td>{escape(str(i.get('severity','')))}</td>"
            f"<td>{escape(str(i.get('message','')))}</td>"
            f"<td>{escape(str(i.get('location','') or ''))}</td></tr>"
            for i in v.issues
        )
        issues = f'<table class="grid">{header}{body}</table>'
    else:
        issues = '<p class="muted">No validation issues recorded.</p>'
    return f"<section><h2>Validation</h2>{counts}{issues}</section>"


def _quality_section(report: Report) -> str:
    dims = report.quality.dimensions
    chart = _bar_chart(dims) if dims else '<p class="muted">No dimension scores.</p>'
    return f"<section><h2>Quality Scores</h2>{chart}</section>"


def _bar_chart(dimensions: Sequence[Mapping[str, JsonValue]]) -> str:
    items = [(str(d.get("dimension", "")), _as_float(d.get("score", 0.0))) for d in dimensions]
    bar_h, gap, width = 26, 10, 460
    height = len(items) * (bar_h + gap) + gap
    bars = []
    for index, (name, score) in enumerate(items):
        y = gap + index * (bar_h + gap)
        w = max(1, int(score * width))
        colour = "#2f9e44" if score >= 0.8 else "#f08c00" if score >= 0.5 else "#e03131"
        base = y + bar_h - 7
        bars.append(
            f'<rect x="120" y="{y}" width="{w}" height="{bar_h}" '
            f'fill="{colour}" rx="3"></rect>'
            f'<text x="112" y="{base}" text-anchor="end" '
            f'class="axis">{escape(name)}</text>'
            f'<text x="{124 + w}" y="{base}" class="axis">{score:.2f}</text>'
        )
    return (
        f'<svg viewBox="0 0 {width + 160} {height}" role="img" '
        f'aria-label="Quality dimension scores" class="chart">{"".join(bars)}</svg>'
    )


def _change_section(report: Report) -> str:
    c = report.change
    rows = [
        ("Added", str(c.added)),
        ("Removed", str(c.removed)),
        ("Modified", str(c.modified)),
        ("Detectors", ", ".join(c.detectors) or "n/a"),
    ]
    return f"<section><h2>Change Detection</h2>{_kv_table(rows)}</section>"


def _provenance_section(report: Report) -> str:
    if not report.provenance:
        return (
            '<section><h2>Source Provenance</h2><p class="muted">No sources recorded.</p></section>'
        )
    header = "<tr><th>URI</th><th>Method</th><th>Retrieved</th></tr>"
    body = "".join(
        f"<tr><td>{escape(e.uri)}</td><td>{escape(e.method)}</td>"
        f"<td>{escape(e.retrieved_at.isoformat() if e.retrieved_at else '')}</td></tr>"
        for e in report.provenance
    )
    return (
        f'<section><h2>Source Provenance</h2><table class="grid">{header}{body}</table></section>'
    )


def _artifacts_section(report: Report) -> str:
    if not report.artifacts:
        return '<section><h2>Artifacts</h2><p class="muted">No artifacts recorded.</p></section>'
    header = "<tr><th>Type</th><th>Locator</th><th>Media type</th></tr>"
    body = "".join(
        f"<tr><td>{escape(a.artifact_type)}</td><td>{escape(a.locator)}</td>"
        f"<td>{escape(a.media_type)}</td></tr>"
        for a in report.artifacts
    )
    return f'<section><h2>Artifacts</h2><table class="grid">{header}{body}</table></section>'


def _rendering_section(report: Report) -> str:
    """Render the browser-rendering evidence, when present. All values escaped."""
    rendering = report.rendering
    if rendering is None:
        return ""
    rows = [("Rendered", "yes" if rendering.rendered else "no")]
    if rendering.visual_status is not None:
        rows.append(("Visual status", rendering.visual_status))
    if rendering.visual_difference_ratio is not None:
        rows.append(("Visual difference", f"{rendering.visual_difference_ratio:.1%}"))
    if rendering.visual_comparable is not None:
        rows.append(("Comparable", "yes" if rendering.visual_comparable else "no"))
    rows.append(("Lifecycle screenshots", str(rendering.staged_screenshot_count)))
    network = rendering.network
    if network:
        rows.append(("Network requests", str(network.get("total_requests", 0))))
        rows.append(("Failed requests", str(network.get("failed_requests", 0))))
        rows.append(("API (XHR/fetch) requests", str(network.get("api_request_count", 0))))
    body = "".join(
        f"<tr><td>{escape(str(label))}</td><td>{escape(str(value))}</td></tr>"
        for label, value in rows
    )
    return f'<section><h2>Browser rendering</h2><table class="grid">{body}</table></section>'


def _issues_section(title: str, items: Sequence[str]) -> str:
    listed = list(items)
    if not listed:
        return f'<section><h2>{escape(title)}</h2><p class="muted">None.</p></section>'
    body = "".join(f"<li>{escape(str(item))}</li>" for item in listed)
    return f"<section><h2>{escape(title)}</h2><ul>{body}</ul></section>"


def _performance_section(report: Report) -> str:
    metrics = report.performance.metrics
    if not metrics:
        return '<section><h2>Performance</h2><p class="muted">No metrics recorded.</p></section>'
    rows = [(name, f"{value:.4f}") for name, value in sorted(metrics.items())]
    return f"<section><h2>Performance</h2>{_kv_table(rows)}</section>"


def _kv_table(rows: Sequence[tuple[str, str]]) -> str:
    body = "".join(f"<tr><th>{escape(str(k))}</th><td>{escape(str(v))}</td></tr>" for k, v in rows)
    return f'<table class="kv">{body}</table>'


_STYLE = """
:root{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#212529}
body{margin:0;background:#f8f9fa}
header{background:#1864ab;color:#fff;padding:20px 28px}
header h1{margin:0;font-size:22px}
.sub{margin:4px 0 0;opacity:.85;font-size:13px}
main{max-width:960px;margin:0 auto;padding:20px}
section{background:#fff;border:1px solid #dee2e6;border-radius:8px;padding:16px 20px;margin:16px 0}
h2{margin:0 0 12px;font-size:16px;border-bottom:1px solid #f1f3f5;padding-bottom:8px}
.cards{display:flex;flex-wrap:wrap;gap:12px}
.card{flex:1 1 120px;border:1px solid #e9ecef;border-radius:6px;
padding:10px 12px;display:flex;flex-direction:column}
.card .label{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:#868e96}
.card .value{font-size:20px;font-weight:600;margin-top:4px}
.card.ok .value{color:#2f9e44}.card.warn .value{color:#f08c00}.card.bad .value{color:#e03131}
table{border-collapse:collapse;width:100%;font-size:13px}
table.kv th{text-align:left;width:180px;color:#495057;font-weight:600;padding:4px 8px}
table.kv td{padding:4px 8px}
table.grid th,table.grid td{border:1px solid #e9ecef;padding:6px 8px;text-align:left}
table.grid th{background:#f1f3f5}
.muted{color:#868e96;font-size:13px}
.chart{max-width:100%;height:auto}
.axis{font-size:11px;fill:#495057}
ul{margin:0;padding-left:20px;font-size:13px}
"""
