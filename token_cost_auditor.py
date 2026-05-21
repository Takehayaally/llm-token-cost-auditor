from __future__ import annotations

import argparse
import csv
import html
import json
from collections import defaultdict
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        row["_line"] = line_number
        rows.append(row)
    return rows


def load_pricing(path: Path) -> dict[str, dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["models"]


def estimate_cost(row: dict, pricing: dict[str, dict]) -> float:
    model = row.get("model", "unknown")
    model_price = pricing.get(model, pricing.get("default", {"input_per_million": 0, "output_per_million": 0}))
    input_tokens = int(row.get("input_tokens", 0))
    output_tokens = int(row.get("output_tokens", 0))
    return (
        input_tokens / 1_000_000 * float(model_price["input_per_million"])
        + output_tokens / 1_000_000 * float(model_price["output_per_million"])
    )


def audit(rows: list[dict], pricing: dict[str, dict], expensive_threshold: float) -> tuple[list[dict], dict]:
    audited = []
    summary = defaultdict(lambda: {"requests": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for row in rows:
        cost = estimate_cost(row, pricing)
        model = row.get("model", "unknown")
        input_tokens = int(row.get("input_tokens", 0))
        output_tokens = int(row.get("output_tokens", 0))
        flags = []
        if cost >= expensive_threshold:
            flags.append("expensive")
        if input_tokens + output_tokens == 0:
            flags.append("missing_tokens")

        audited_row = {
            "line": row["_line"],
            "timestamp": row.get("timestamp", ""),
            "request_id": row.get("request_id", ""),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost, 6),
            "flags": ",".join(flags),
        }
        audited.append(audited_row)
        summary[model]["requests"] += 1
        summary[model]["input_tokens"] += input_tokens
        summary[model]["output_tokens"] += output_tokens
        summary[model]["cost_usd"] += cost
    return audited, dict(summary)


def write_csv(path: Path, audited: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(audited[0].keys()) if audited else ["line"])
        writer.writeheader()
        writer.writerows(audited)


def write_html(path: Path, audited: list[dict], summary: dict) -> None:
    summary_rows = []
    for model, values in summary.items():
        summary_rows.append(
            "<tr>"
            f"<td>{html.escape(model)}</td>"
            f"<td>{values['requests']}</td>"
            f"<td>{values['input_tokens']}</td>"
            f"<td>{values['output_tokens']}</td>"
            f"<td>${values['cost_usd']:.4f}</td>"
            "</tr>"
        )
    detail_rows = []
    for row in audited:
        detail_rows.append(
            "<tr>"
            f"<td>{row['line']}</td><td>{html.escape(row['timestamp'])}</td>"
            f"<td>{html.escape(row['request_id'])}</td><td>{html.escape(row['model'])}</td>"
            f"<td>{row['input_tokens']}</td><td>{row['output_tokens']}</td>"
            f"<td>${row['cost_usd']:.6f}</td><td>{html.escape(row['flags'])}</td>"
            "</tr>"
        )
    path.write_text(
        f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<title>LLM Token Cost Audit</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 32px; color: #1f2937; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
th, td {{ border: 1px solid #d1d5db; padding: 8px; text-align: left; }}
th {{ background: #f3f4f6; }}
</style>
<h1>LLM Token Cost Audit</h1>
<h2>By Model</h2>
<table><thead><tr><th>Model</th><th>Requests</th><th>Input</th><th>Output</th><th>Cost</th></tr></thead><tbody>{''.join(summary_rows)}</tbody></table>
<h2>Requests</h2>
<table><thead><tr><th>Line</th><th>Time</th><th>Request</th><th>Model</th><th>Input</th><th>Output</th><th>Cost</th><th>Flags</th></tr></thead><tbody>{''.join(detail_rows)}</tbody></table>
</html>
""",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit LLM JSONL token logs.")
    parser.add_argument("--logs", required=True)
    parser.add_argument("--pricing", required=True)
    parser.add_argument("--expensive-threshold", type=float, default=0.05)
    parser.add_argument("--html-out", default="llm-cost-report.html")
    parser.add_argument("--csv-out", default="llm-cost-report.csv")
    args = parser.parse_args(argv)

    rows = load_jsonl(Path(args.logs))
    pricing = load_pricing(Path(args.pricing))
    audited, summary = audit(rows, pricing, args.expensive_threshold)
    write_csv(Path(args.csv_out), audited)
    write_html(Path(args.html_out), audited, summary)
    print(f"Audited {len(audited)} requests across {len(summary)} models")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
