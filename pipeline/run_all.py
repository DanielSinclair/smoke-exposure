#!/usr/bin/env python3
"""Single entrypoint for downloading, rebuilding, validating, and inventorying data."""

from __future__ import annotations

import argparse
import subprocess
import sys


MODULES = (
    "pipeline.process_census",
    "pipeline.process_mtbs",
    "pipeline.process_canada",
    "pipeline.process_smoke",
    "pipeline.aggregate_stanford",
    "pipeline.process_operational_extension",
    "pipeline.process_current_fire_activity",
    "pipeline.process_historical_smoke_evidence",
    "pipeline.process_event_history",
    "pipeline.process_all_fire_history",
    "pipeline.process_fire_history",
    "pipeline.build_dashboard",
    "pipeline.validate",
    "pipeline.checksums",
    "pipeline.render_social_graphics",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--download",
        action="store_true",
        help="fetch checksum-pinned raw inputs before processing",
    )
    parser.add_argument(
        "--odell-extension",
        action="store_true",
        help="process locally available O'Dell/Ford Dryad mean-background archives",
    )
    args = parser.parse_args()
    commands = []
    if args.download:
        commands.extend((
            [sys.executable, "-m", "pipeline.download"],
            [sys.executable, "-m", "pipeline.download_extension_inputs"],
            [sys.executable, "-m", "pipeline.download_current_inputs"],
            [sys.executable, "-m", "pipeline.download_fire_history_inputs"],
            [sys.executable, "-m", "pipeline.download_historical_smoke_inputs"],
        ))
    commands.extend([sys.executable, "-m", module] for module in MODULES)
    if args.odell_extension:
        commands.insert(-5, [sys.executable, "-m", "pipeline.process_odell_extension"])
    for command in commands:
        print(f"\n== {' '.join(command[2:])} ==", flush=True)
        subprocess.run(command, check=True)


if __name__ == "__main__":
    main()
