"""Operational splitter tests use a synthetic fixture, never the blind set."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from kingscode.common import ROOT
from tools.split_test_stratified import split_rows


class StratifiedBlindSplitTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT))
        self.source = self.tmp / "test_992.jsonl"
        rows = []
        for area in ("administrativo", "civil"):
            for fmt in ("open_ended", "semi_open"):
                for n in range(5):
                    rows.append({"id": f"{area}-{fmt}-{n}", "area": area, "formato": fmt,
                                 "pregunta": "fixture question text"})
        self.source.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_parts_balance_each_area_format_stratum_and_preserve_rows(self):
        report = split_rows(self.source, 2)
        self.assertEqual(report["rows"], 20)
        self.assertEqual([p["rows"] for p in report["parts"]], [10, 10])
        parts = []
        for item in report["parts"]:
            rows = [json.loads(line) for line in (self.tmp / item["path"]).read_text(encoding="utf-8").splitlines()]
            parts.extend(rows)
            self.assertEqual(len(item["strata"]), 4)
            self.assertTrue(all(count in {2, 3} for count in item["strata"].values()))
        self.assertEqual({row["id"] for row in parts}, {f"{a}-{f}-{n}" for a in ("administrativo", "civil") for f in ("open_ended", "semi_open") for n in range(5)})

    def test_only_accepts_blind_filename_and_refuses_overwrite(self):
        split_rows(self.source, 2)
        with self.assertRaises(FileExistsError):
            split_rows(self.source, 2)
        other = self.tmp / "sample_50.jsonl"
        other.write_text(self.source.read_text(encoding="utf-8"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "only data/test_992.jsonl"):
            split_rows(other, 2)


if __name__ == "__main__":
    unittest.main()
