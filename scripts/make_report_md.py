from __future__ import annotations

import argparse
import csv
from pathlib import Path


METRICS = [
    ("throughput_rps", "Throughput (rps)", "higher"),
    ("p95_latency_ms", "P95 latency (ms)", "lower"),
    ("sla_violation_rate", "SLA violation rate", "lower"),
    ("cost_per_success", "Cost per success", "lower"),
]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as fp:
        return list(csv.DictReader(fp))


def _f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def format_val(mean: float, ci95: float, metric_key: str) -> str:
    if metric_key.endswith("_rate"):
        return f"{mean:.4f} +- {ci95:.4f}"
    if metric_key.endswith("_ms"):
        return f"{mean:.1f} +- {ci95:.1f}"
    return f"{mean:.4f} +- {ci95:.4f}"


def best_policy(rows: list[dict[str, str]], metric_key: str, direction: str) -> str:
    best_by_policy: dict[str, float] = {}
    for row in rows:
        policy = row["policy"]
        value = _f(row, metric_key)
        if policy not in best_by_policy:
            best_by_policy[policy] = value
            continue
        if direction == "higher":
            best_by_policy[policy] = max(best_by_policy[policy], value)
        else:
            best_by_policy[policy] = min(best_by_policy[policy], value)

    items = list(best_by_policy.items())
    if direction == "higher":
        return max(items, key=lambda kv: kv[1])[0]
    return min(items, key=lambda kv: kv[1])[0]


def markdown_for_sweep(name: str, rows: list[dict[str, str]]) -> str:
    lines: list[str] = []
    lines.append(f"## {name}")
    lines.append("")
    lines.append("### Best policy per metric")
    lines.append("")
    for key, label, direction in METRICS:
        winner = best_policy(rows, key, direction)
        lines.append(f"- {label}: `{winner}` ({direction} is better)")
    lines.append("")

    lines.append("### Full table")
    lines.append("")
    lines.append(
        "| policy | mix (s:a) | throughput | p95 latency | SLA viol. | cost/success |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|")

    for row in rows:
        mix = f"{_f(row, 'streaming_ratio'):.1f}:{_f(row, 'agentic_ratio'):.1f}"
        throughput = format_val(
            _f(row, "throughput_rps"), _f(row, "throughput_rps_ci95"), "throughput_rps"
        )
        p95 = format_val(
            _f(row, "p95_latency_ms"), _f(row, "p95_latency_ms_ci95"), "p95_latency_ms"
        )
        sla = format_val(
            _f(row, "sla_violation_rate"),
            _f(row, "sla_violation_rate_ci95"),
            "sla_violation_rate",
        )
        cost = format_val(
            _f(row, "cost_per_success"),
            _f(row, "cost_per_success_ci95"),
            "cost_per_success",
        )
        lines.append(
            f"| {row['policy']} | {mix} | {throughput} | {p95} | {sla} | {cost} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate markdown report from sweep CSVs"
    )
    parser.add_argument("--baseline", required=True, help="Baseline sweep CSV path")
    parser.add_argument(
        "--contention", required=True, help="High-contention sweep CSV path"
    )
    parser.add_argument(
        "--output", default="docs/results.md", help="Output markdown path"
    )
    args = parser.parse_args()

    baseline_rows = load_csv(Path(args.baseline))
    contention_rows = load_csv(Path(args.contention))

    doc: list[str] = []
    doc.append("# Mixed Workload Benchmark Results")
    doc.append("")
    doc.append(
        "This document is auto-generated from sweep CSV outputs. Values are mean +- 95% CI across replicates."
    )
    doc.append("")
    doc.append(markdown_for_sweep("Baseline Scenario", baseline_rows))
    doc.append(markdown_for_sweep("High-Contention Scenario", contention_rows))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(doc))
    print(output)


if __name__ == "__main__":
    main()
