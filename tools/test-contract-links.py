#!/usr/bin/env python3
"""Focused rejection cases for the offline contract-reference check."""

import copy
import json
from pathlib import Path
import runpy
import shutil
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CHECKS = runpy.run_path(str(ROOT / "tools/check-contract-links.py"))


class ContractLinkFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dist = self.root / "dist"
        shutil.copytree(ROOT / "dist", self.dist)
        self.data = CHECKS["read_metadata"](ROOT / "src/data/contract.json")

    def change_page(self, old, new):
        page = self.dist / "api.html"
        text = page.read_text(encoding="utf-8")
        self.assertIn(old, text, "rejection case did not change its target")
        page.write_text(text.replace(old, new, 1), encoding="utf-8")

    def test_rejects_mutable_revision_and_unqualified_release(self):
        for field, value in (("revision", "main"), ("release", "0.1.0")):
            with self.subTest(field=field):
                data = copy.deepcopy(self.data)
                data[field] = value
                path = self.root / "metadata.json"
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.assertRaises(ValueError):
                    CHECKS["read_metadata"](path)

    def test_rejects_mutable_link_in_built_page(self):
        self.change_page(f"/blob/{self.data['revision']}/", "/blob/main/")
        with self.assertRaisesRegex(ValueError, "mismatched"):
            CHECKS["check_pages"](self.dist, self.data)

    def test_rejects_missing_contract_reference(self):
        self.change_page('data-contract-reference="request"', 'data-contract-reference="missing"')
        with self.assertRaisesRegex(ValueError, "unknown contract reference"):
            CHECKS["check_pages"](self.dist, self.data)

    def test_rejects_stale_visible_version(self):
        version = self.data["schema_version"]
        self.change_page(f'data-contract-version="schema">{version}', f'data-contract-version="schema">{version + 1}')
        with self.assertRaisesRegex(ValueError, "stale schema version"):
            CHECKS["check_pages"](self.dist, self.data)

    def test_rejects_stale_request_example(self):
        version = self.data["abi_version"]
        self.change_page(f'&quot;abi_version&quot;: {version}', f'&quot;abi_version&quot;: {version + 1}')
        with self.assertRaisesRegex(ValueError, "stale negotiation example"):
            CHECKS["check_pages"](self.dist, self.data)

    def test_requires_a_build(self):
        with self.assertRaisesRegex(ValueError, "no built HTML"):
            CHECKS["check_pages"](self.root / "absent", self.data)


if __name__ == "__main__":
    unittest.main()
