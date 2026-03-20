from __future__ import annotations

import argparse

from .config import load_config
from .runner import run_single_to_json, run_sweep_to_csv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mws-bench", description="Mixed workload serving benchmark"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Run replicates for one config")
    run_cmd.add_argument("--config", required=True, help="Path to config JSON")
    run_cmd.add_argument("--output", required=True, help="Path to output JSON")

    sweep_cmd = sub.add_parser("sweep", help="Run policy x mix sweep")
    sweep_cmd.add_argument(
        "--config", default="configs/default.json", help="Path to base config JSON"
    )
    sweep_cmd.add_argument("--output", required=True, help="Path to output CSV")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.command == "run":
        run_single_to_json(cfg, args.output)
        return

    if args.command == "sweep":
        run_sweep_to_csv(cfg, args.output)
        return

    raise ValueError(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
