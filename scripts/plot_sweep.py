from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def load_rows(csv_path: Path) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    with csv_path.open(newline="") as fp:
        reader = csv.DictReader(fp)
        for raw in reader:
            rows.append(
                {
                    "policy": raw["policy"],
                    "streaming_ratio": float(raw["streaming_ratio"]),
                    "agentic_ratio": float(raw["agentic_ratio"]),
                    "throughput_rps": float(raw["throughput_rps"]),
                    "p95_latency_ms": float(raw["p95_latency_ms"]),
                    "p99_latency_ms": float(raw["p99_latency_ms"]),
                    "sla_violation_rate": float(raw["sla_violation_rate"]),
                    "cost_per_success": float(raw["cost_per_success"]),
                }
            )
    return rows


def metric_for(
    rows: list[dict[str, float | str]], policy: str, mix: float, key: str
) -> float:
    for row in rows:
        if row["policy"] == policy and row["streaming_ratio"] == mix:
            value = row[key]
            if isinstance(value, float):
                return value
    raise ValueError(f"Missing row for policy={policy}, mix={mix}, metric={key}")


def barplot(rows: list[dict[str, float | str]], output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    policies = sorted({str(r["policy"]) for r in rows})
    mixes = sorted({float(r["streaming_ratio"]) for r in rows}, reverse=True)
    labels = [f"{m:.1f}:{1.0 - m:.1f}" for m in mixes]

    plots = [
        ("throughput_rps", "Throughput (rps)", "higher"),
        ("p95_latency_ms", "P95 latency (ms)", "lower"),
        ("sla_violation_rate", "SLA violation rate", "lower"),
        ("cost_per_success", "Cost per success", "lower"),
    ]

    written: list[Path] = []
    for metric_key, title, direction in plots:
        width = 0.22
        x = list(range(len(mixes)))

        fig, ax = plt.subplots(figsize=(9, 5))
        for i, policy in enumerate(policies):
            vals = [metric_for(rows, policy, mix, metric_key) for mix in mixes]
            offset = [v + (i - (len(policies) - 1) / 2) * width for v in x]
            ax.bar(offset, vals, width=width, label=policy)

        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_xlabel("Workload mix (streaming:agentic)")
        ax.set_ylabel(title)
        ax.set_title(f"{title} by policy and mix ({direction} is better)")
        ax.legend()
        ax.grid(True, axis="y", alpha=0.3)

        out_path = output_dir / f"{metric_key}.png"
        fig.tight_layout()
        fig.savefig(out_path, dpi=180)
        plt.close(fig)
        written.append(out_path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot sweep CSV metrics")
    parser.add_argument("--input", required=True, help="Path to sweep CSV")
    parser.add_argument(
        "--output-dir", default="results/plots", help="Output directory"
    )
    args = parser.parse_args()

    rows = load_rows(Path(args.input))
    written = barplot(rows, Path(args.output_dir))
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
