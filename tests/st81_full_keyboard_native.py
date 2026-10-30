#!/usr/bin/env python3
"""One native guest-CPU campaign for the ENTIRE Dana physical keyboard.

Checks every raw ST scan from the 81 MAME input callbacks and several
simultaneous-key packets. No peripheral shortcuts, no guest OS key injection,
no MAME source edits, no extra executable. Requires an explicitly authorized
T run; this script never runs on its own.
"""
import json
import re
from pathlib import Path

PORT = re.compile(r'PORT_START\("(KEYS|EXKEY[0-3])"\)')
LABEL = re.compile(r'PORT_NAME\("((?:\\.|[^"\\])*)"\)')
SCAN = re.compile(r'st_key_changed\),(\d+)\)')
MASK = re.compile(r'PORT_BIT\(0x([0-9a-f]+),', re.IGNORECASE)


def inventory(source):
    tag = None
    result = []
    for line in source.splitlines():
        p = PORT.search(line)
        if p:
            tag = p.group(1)
        if tag and 'PORT_BIT(' in line and 'st_key_changed' in line:
            m, n, b = LABEL.search(line), SCAN.search(line), MASK.search(line)
            if not m or not n or not b:
                raise ValueError('Unparseable physical key mapping: '+line)
            result.append((tag, json.loads('"'+m.group(1)+'"'), int(n.group(1)), int(b.group(1), 16)))
    codes = [scan for _, _, scan, _ in result]
    if len(codes) != 81 or len(set(codes)) != 81:
        raise ValueError('Expected 81 distinct physical Dana scan codes')
    if not all(0 < x < 128 for x in codes):
        raise ValueError('Invalid Dana ST scan code')
    return result


def main():
    # Historical entry point; current qualification includes the original OS
    # and AlphaWord rather than stopping at a diagnostic packet ledger.
    from run_keyboard_campaign import main as campaign
    campaign()

if __name__ == '__main__':
    main()
