"""Provenance contract for the three preregistered official Council of State PDFs."""
import json
from pathlib import Path
import subprocess
import unittest

from kingscode.common import ROOT, file_hash


class CorpusV03AcquisitionTests(unittest.TestCase):
    def test_source_selection_was_committed_before_acquisition_and_bytes_match(self):
        root = ROOT / "corpora/corpus-v03-additions"
        acquisition = json.loads((root / "acquisition.json").read_text(encoding="utf-8"))
        self.assertTrue(acquisition["selection_pre_registered_before_download"])
        self.assertEqual(acquisition["selection_plan_commit"], "3808846")
        subprocess.check_call(["git", "cat-file", "-e", "3808846^{commit}"], cwd=ROOT)
        self.assertEqual(acquisition["downloaded"], 3)
        for document in acquisition["documents"]:
            self.assertTrue(document["source_url"].startswith("https://www.consejodeestado.gov.co/") or
                            document["source_url"].startswith("https://consejodeestado.gov.co/"))
            self.assertEqual(document["http_status"], 200)
            self.assertEqual(document["content_type"], "application/pdf")
            self.assertTrue(document["tls_verified"])
            raw = ROOT / document["raw_path"]
            self.assertEqual(file_hash(raw), document["source_sha256"])
            self.assertNotIn("test_992", document["raw_path"].casefold())
        self.assertEqual({d["doc_id"] for d in acquisition["documents"]}, {
            "consejo_estado_suj_032_ce_s2_2023", "consejo_estado_unif_s3_24897_2012",
            "consejo_estado_suj_4_002_2022"})

    def test_v03_manifest_keeps_blank_terminal_pages_explicit(self):
        manifest = json.loads((ROOT / "corpora/corpus-v03-additions/manifest.json").read_text(encoding="utf-8"))
        rows = {row["doc_id"]: row for row in manifest["documentos"]}
        self.assertEqual(rows["consejo_estado_suj_032_ce_s2_2023"]["pdf_skip_pages"], [73])
        self.assertEqual(rows["consejo_estado_unif_s3_24897_2012"]["pdf_skip_pages"], [69])
        self.assertNotIn("pdf_skip_pages", rows["consejo_estado_suj_4_002_2022"])


if __name__ == "__main__":
    unittest.main()
