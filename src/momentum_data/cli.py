"""Small public CLI; importing it does not load market data or Nautilus."""

import argparse
import json


def execute(command):
    if command == "smoke":
        from .demo import smoke

        return smoke()
    if command == "verify":
        from .data.preflight import verify_inputs

        result = verify_inputs()[3]
        print(json.dumps(result))
        return result
    if command == "replay":
        from .backtest.workflow import replay

        return replay()
    if command == "summary":
        from .backtest.workflow import print_summary

        return print_summary()
    if command == "publish":
        from .reporting.publication import publish

        return publish()
    raise ValueError(command)


def main():
    parser = argparse.ArgumentParser(
        description="Frozen crypto factor research: verify, reproduce and inspect results"
    )
    parser.add_argument("command", choices=["smoke", "verify", "replay", "summary", "publish"])
    args = parser.parse_args()
    execute(args.command)


def compatibility_main():
    parser = argparse.ArgumentParser(
        description="Compatibility entry point; prefer python -m momentum_data"
    )
    parser.add_argument(
        "--stage", choices=["all", "preflight", "simulate", "report", "summary"], default="all"
    )
    args = parser.parse_args()
    stages = {
        "preflight": "verify",
        "simulate": "replay",
        "report": "publish",
        "summary": "summary",
    }
    for command in ["verify", "replay", "publish"] if args.stage == "all" else [stages[args.stage]]:
        execute(command)
