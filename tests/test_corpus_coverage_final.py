"""Tests for structured, answer-free corpus coverage reporting."""
from pathlib import Path
import json
import shutil
import tempfile
import unittest

from kingscode.common import ROOT, file_hash, write_json, write_jsonl
from tools.analyze_corpus_coverage import analyze_corpus, _assert_not_blind_path


class CorpusCoverageFinalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(dir=ROOT))
        self.corpus = self.tmp / "tiny_corpus"
        (self.corpus / "graph").mkdir(parents=True)
        (self.corpus / "index").mkdir()
        docs = [{"doc_id": "ce_sample", "norm_name": "Sentencia Consejo de Estado", "document_title": "Sentencia demo",
                 "canonical_body": ["jurisprudencia", "CE-1", "2022"], "source_type": "decision",
                 "areas": ["Derecho administrativo", "Derecho procesal"], "court": "Consejo de Estado",
                 "source_url": "https://example.gov.co/judgment.pdf", "source_sha256": "a" * 64,
                 "retrieved_at": "2026-01-01T00:00:00+00:00", "status": "parsed", "n_fragmentos": 2, "n_indexed": 1}]
        passages = [
            {"passage_id": "ce_sample:00001", "doc_id": "ce_sample", "source_type": "decision", "areas": docs[0]["areas"],
             "text": "Texto indexable", "retrieval_eligible": True, "graph_node_ids": ["doc:ce_sample"]},
            {"passage_id": "ce_sample:00002", "doc_id": "ce_sample", "source_type": "decision", "areas": docs[0]["areas"],
             "text": "Texto histórico excluido", "retrieval_eligible": False, "graph_node_ids": ["doc:ce_sample"]},
        ]
        write_jsonl(self.corpus / "passages.jsonl", passages)
        write_jsonl(self.corpus / "graph/nodes.jsonl", [{"node_id": "doc:ce_sample"}])
        write_jsonl(self.corpus / "graph/edges.jsonl", [])
        (self.corpus / "index/bm25.json").write_text("{}", encoding="utf-8")
        hashes = {name: file_hash(self.corpus / name) for name in ["passages.jsonl", "graph/nodes.jsonl", "graph/edges.jsonl"]}
        write_json(self.corpus / "manifest.json", {"version": "fixture", "parser_version": "test", "documentos": docs,
                                                    "hashes": hashes, "bm25_sha256": file_hash(self.corpus / "index/bm25.json")})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_area_authority_type_matrix_and_exclusions(self):
        report = analyze_corpus(self.corpus)
        self.assertEqual(report["totals"]["documents"], 1)
        self.assertEqual(report["totals"]["indexed_passages"], 1)
        self.assertEqual(report["totals"]["excluded_passages"], 1)
        self.assertEqual(report["documents_by_authority"]["Consejo de Estado"], 1)
        cell = next(c for c in report["coverage_matrix"] if c["area"] == "procedural" and c["authority"] == "Consejo de Estado" and c["source_type"] == "decision")
        self.assertEqual((cell["documents"], cell["indexed_passages"], cell["status"]), (1, 1, "sparse"))
        self.assertEqual(report["source_inventory"][0]["source_sha256"], "a" * 64)
        self.assertEqual(len(report["parser_failures"]), 0)

    def test_report_is_deterministic_and_blind_path_is_rejected_without_opening(self):
        first = analyze_corpus(self.corpus)
        second = analyze_corpus(self.corpus)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        blind_path = ROOT / "data/test_992.jsonl"
        with self.assertRaisesRegex(ValueError, "Blind competitive file"):
            _assert_not_blind_path(blind_path)


if __name__ == "__main__":
    unittest.main()
