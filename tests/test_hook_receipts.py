"""Receipt safety and concurrency; these are deterministic tests, not native evidence."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
import unittest

from pa_devtools.hooks import append_receipt


class ReceiptTests(unittest.TestCase):
    def test_private_external_regular_file_and_concurrent_appends(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            log = Path(directory) / "events.jsonl"
            log.touch(mode=0o600)

            def append(number):
                append_receipt(root, str(log), {"number": number})

            with ThreadPoolExecutor(max_workers=8) as pool:
                list(pool.map(append, range(100)))
            self.assertEqual(
                {json.loads(line)["number"] for line in log.read_text().splitlines()},
                set(range(100)),
            )
            link = Path(directory) / "link"
            link.symlink_to(log)
            with self.assertRaises(OSError):
                append_receipt(root, str(link), {})
            log.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "private regular"):
                append_receipt(root, str(log), {})
            log.chmod(0o600)
            os.link(log, Path(directory) / "hardlink")
            with self.assertRaisesRegex(ValueError, "private regular"):
                append_receipt(root, str(log), {})

    def test_fifo_and_missing_file_do_not_block_or_create(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "source"
            root.mkdir()
            path = Path(directory) / "events"
            with self.assertRaises(OSError):
                append_receipt(root, str(path), {})
            self.assertFalse(path.exists())
            os.mkfifo(path, 0o600)
            with self.assertRaises(OSError):
                append_receipt(root, str(path), {})
