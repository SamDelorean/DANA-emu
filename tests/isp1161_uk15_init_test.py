#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Native successor to the obsolete pre-PTD source-extraction init test.

The old constexpr mock assumed a four-byte HC-only window and no chip SRAM,
timers, DC or downstream transport. It no longer compiled the production chip.
This entry point now executes the existing physical bus and 68000 HC fixtures
in the sole canonical MAME instance, sequentially. It never patches Palm ROM.
"""
import argparse
import datetime
import subprocess
import sys
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="store_true")
    parser.add_argument("--case", default="init-" + datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%d-%H%M%S"))
    args = parser.parse_args()
    if not args.case.replace("-", "").replace("_", "").isalnum():
        parser.error("case must contain only letters, digits, '-' and '_'")
    runner = Path(__file__).with_name("run_isp1161_native.py")
    for suffix, mode in [("bus", "bus"), ("host", "host-printer")]:
        command = [sys.executable, str(runner), "--case",
                   args.case + "-" + suffix, "--mode", mode]
        if not args.candidate:
            command.append("--installed")
        subprocess.run(command, check=True)
    print("ISP1161_NATIVE_INIT_PROTOCOL_PASS")

if __name__ == "__main__":
    main()
