"""The FOOPS! score summary and its report page."""

from __future__ import annotations

import html as h
from dataclasses import dataclass
from pathlib import Path

PAGE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>FOOPS! Report — {title}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; line-height: 1.5; }}
    h1 {{ margin-bottom: .25rem; }}
    .meta {{ color: #555; margin-bottom: 1.5rem; }}
    a {{ color: #0b5fff; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 1100px; font-size: .9rem; }}
    th, td {{ border: 1px solid #e5e7eb; padding: .5rem .75rem; text-align: left; vertical-align: top; }}
    th {{ background: #f9fafb; }}
    tr:hover {{ background: #f0f9ff; }}
    code {{ color: #0b5fff; }}
  </style>
</head>
<body>
  <h1>FOOPS! Report</h1>
  <div class="meta">
    <div><strong>Ontology:</strong> <a href="../">{title}</a></div>
    <div><strong>IRI:</strong> <code>{iri}</code></div>
    <div><strong>Overall score:</strong> {overall}</div>
  </div>
  {error}
  <table>
    <thead><tr><th>ID</th><th>Check</th><th>Score</th><th>Explanation</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
</body>
</html>
"""


@dataclass(frozen=True)
class FoopsSummary:
    label: str
    checks: list[dict]


def summarize_foops(data: dict) -> FoopsSummary:
    checks = list(data["checks"])
    n = len(checks)
    total = sum(c["total_passed_tests"] / c["total_tests_run"] for c in checks if c["total_tests_run"])
    pct = total / n * 100 if n else 0.0
    return FoopsSummary(f"{pct:.1f}% ({total:.2f} in {n} tests)", checks)


def _row(c: dict) -> str:
    cid = c.get("id", "")
    passed = c.get("total_passed_tests", 0)
    total = c.get("total_tests_run", 1)
    color = "#16a34a" if passed == total else "#dc2626" if passed == 0 else "#d97706"
    explanation = c.get("explanation", c.get("description", ""))
    return (
        f"<tr><td><code>{h.escape(str(cid))}</code></td>"
        f"<td>{h.escape(str(c.get('title', cid)))}</td>"
        f"<td style='color:{color};font-weight:bold;white-space:nowrap'>{passed}/{total}</td>"
        f"<td>{h.escape(str(explanation))}</td></tr>\n"
    )


def write_foops_page(
    summary: FoopsSummary | None, out: Path, title: str, iri: str, error: str = ""
) -> None:
    """Write ``out/foops/index.html``; summary None means the results could not be loaded."""
    out = Path(out)
    (out / "foops").mkdir(parents=True, exist_ok=True)
    if summary is None:
        msg = h.escape(error or "no results")
        err = f"<p style='color:red'>Could not load FOOPS results: {msg}</p>"
    else:
        err = ""
    page = PAGE.format(
        title=h.escape(title),
        iri=h.escape(iri),
        overall=h.escape(summary.label) if summary else "N/A",
        error=err,
        rows="".join(_row(c) for c in summary.checks) if summary else "",
    )
    (out / "foops" / "index.html").write_text(page, encoding="utf-8")
