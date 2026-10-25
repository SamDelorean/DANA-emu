#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Parser failure cases only; no emulator or commercial firmware fixture."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location('audit', Path(__file__).resolve().parents[1] / 'tools/palm_updater_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


def database(entries):
    header = bytearray(78)
    struct.pack_into('>H', header, 32, 1)
    struct.pack_into('>H', header, 76, len(entries))
    offset = 78 + 10 * len(entries)
    table, bodies = b'', b''
    for kind, number, body in entries:
        table += struct.pack('>4sHI', kind, number, offset)
        bodies += body
        offset += len(body)
    return header + table + bodies


def chunk(data):
    return data + struct.pack('>I', sum(data) & 0xffffffff)


class ResourceParsing(unittest.TestCase):
    def test_byte_sum_and_id_order(self):
        data = database([(b'Flas', 2001, chunk(b'right')), (b'Flas', 2000, chunk(b'left'))])
        self.assertEqual(audit.payload(audit.resources(data)), (b'leftright', [2000, 2001]))

    def test_checksum_corruption_rejected(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            audit.payload({(b'Flas', 2000): chunk(b'data')[:-1] + b'\x00'})

    def test_missing_resource_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Nonconsecutive'):
            audit.payload({(b'Flas', 2000): chunk(b'a'), (b'Flas', 2002): chunk(b'b')})

    def test_duplicate_identity_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            audit.resources(database([(b'Flas', 2000, chunk(b'a')), (b'Flas', 2000, chunk(b'b'))]))

    def test_table_overlap_rejected(self):
        data = database([(b'Flas', 2000, chunk(b'a'))])
        struct.pack_into('>I', data, 84, 78)
        with self.assertRaisesRegex(ValueError, 'bounds'):
            audit.resources(data)

    def test_truncated_database_rejected(self):
        data = database([(b'Flas', 2000, chunk(b'a'))])
        for end in (0, 77, 85):
            with self.subTest(end=end), self.assertRaises(ValueError):
                audit.resources(data[:end])


if __name__ == '__main__':
    unittest.main()
