"""Tests for the append-only corpus C1 decision gate; no blind-set inputs."""
from pathlib import Path
import shutil
import tempfile
import unittest

from kingscode.common import ROOT, file_hash, write_json, write_jsonl
from tools.gate_corpus_expansion import TARGET_AREAS, assess


METRICS = ["Recall@1", "Recall@3", "Recall@5", "Recall@8", "Recall@10", "MRR@10", "MAP@10", "nDCG@10",
           "Document Recall@10", "Document Mismatch Rate", "Passage Recall@10", "Evidence Completeness@8",
           "Evidence Completeness@10", "Span Recall", "Span Precision", "retrieved_passages", "retrieved_characters",
           "retrieved_tokens", "unique_documents", "duplicate_fragment_count"]


class CorpusExpansionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT))
        self.base, self.candidate = self.tmp / "base", self.tmp / "candidate"
        self.base.mkdir()
        self.candidate.mkdir()
        self.coverage = self.tmp / "coverage.json"
        write_json(self.coverage, {"report": {"decision_documents_by_authority": {"Consejo de Estado": 3}}})
        self.rows = []
        for i, area in enumerate(TARGET_AREAS.values()):
            self.rows.append({"id": f"q{i}", "question": {"area": area, "tags": []},
                              "latency_ms": 5, "metrics": {name: 0.0 for name in METRICS}})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_run(self, directory, rows, *, candidate=False):
        write_jsonl(directory / "per_question.jsonl", rows)
        report = {"status": "passed", "variant": "R0", "split": "dev",
                  "git": {"commit": "same-sha", "branch": "codex/test"},
                  "benchmark": {"manifest_sha256": "benchmark-sha"},
                  "corpus": {"version": "candidate" if candidate else "corpus-v0.1",
                             "hashes": {"passages.jsonl": "different" if candidate else "baseline"}},
                  "per_question_sha256": file_hash(directory / "per_question.jsonl"),
                  "metrics": {}, "subgroups": {}}
        if candidate:
            report["corpus_extension_validation"] = {"baseline_passage_prefix_preserved": True,
                                                       "baseline_passages_sha256": "baseline"}
        write_json(directory / "report.json", report)

    def test_gate_requires_overall_and_undercovered_area_improvement(self):
        better = [{**row, "metrics": {name: 1.0 for name in METRICS}} for row in self.rows]
        self._write_run(self.base, self.rows)
        self._write_run(self.candidate, better, candidate=True)
        result = assess(self.base, self.candidate, self.coverage)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(set(result["checks"]["improved_target_areas"]), set(TARGET_AREAS))

    def test_tie_is_not_a_corpus_expansion_pass(self):
        self._write_run(self.base, self.rows)
        self._write_run(self.candidate, self.rows, candidate=True)
        result = assess(self.base, self.candidate, self.coverage)
        self.assertEqual(result["status"], "NOT_PASSED")
        self.assertFalse(result["checks"]["overall_evidence_completeness_at_8_improved_with_paired_95ci"])


if __name__ == "__main__":
    unittest.main()
