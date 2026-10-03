"""Unit tests for the internal retrieval benchmark evaluator.

Tests use hand-built passages/gold. They do not open sample_50, answers, or
legal_basis and never invoke a model or network.
"""
from __future__ import annotations

import unittest
from pathlib import Path
import tempfile
from unittest.mock import patch

from kingscode.benchmark_builder import BENCHMARK_ROOT, verify as verify_benchmark
from kingscode.common import ROOT, file_hash, read_jsonl, write_json
from kingscode.retrieval_benchmark import (
    GPU_VARIANT_PREREQUISITES,
    aggregate,
    bootstrap_reports,
    complementarity,
    paired_bootstrap,
    per_question_metrics,
    retrieval_input,
    run,
    benchmark_manifest,
    _verify_declared_hashes,
)


def p(pid: str, doc: str, article: str, start: int = 0, end: int = 20):
    return {"passage_id": pid, "doc_id": doc, "source_type": "law",
            "canonical_body": ["ley", doc.split("_")[-1], "2020"], "norm_name": f"Ley {doc}",
            "article": article, "clean_start": start, "clean_end": end,
            "text": "texto oficial " + pid, "text_prefix": "", "retrieval_eligible": True,
            "graph_node_ids": [], "source_url": "https://example.test"}


def gold(passages):
    from kingscode.metadata import canonical_document_id, canonical_fragment_id
    return {"record_type": "gold", "id": "KC-CIV-001",
            "gold_document_ids": list(dict.fromkeys(canonical_document_id(x) for x in passages)),
            "gold_fragment_ids": [canonical_fragment_id(x) for x in passages],
            "evidence": [{"canonical_fragment_id": canonical_fragment_id(x), "relevance": "direct"} for x in passages],
            "gold_spans": [{"canonical_fragment_id": canonical_fragment_id(x), "passage_id": x["passage_id"],
                            "clean_start": x["clean_start"], "clean_end": x["clean_end"]} for x in passages]}


class InputBoundaryTests(unittest.TestCase):
    def test_retrieval_input_projects_only_text(self):
        q = {"id": "KC-CIV-001", "question": "texto seguro", "area": "civil", "tags": [], "format": "retrieval"}
        self.assertEqual(retrieval_input(q), "texto seguro")

    def test_retrieval_input_rejects_gold_leakage(self):
        with self.assertRaises(ValueError):
            retrieval_input({"question": "x", "gold_fragment_ids": ["secret"]})

    def test_holdout_requires_explicit_protection_override(self):
        with self.assertRaises(PermissionError):
            run("R0", "holdout")
    def test_holdout_declaration_only_allows_predeclared_r0(self):
        from kingscode.retrieval_benchmark import _assert_holdout_policy
        with self.assertRaises(PermissionError):
            _assert_holdout_policy("holdout", "R1-QWEN", True, "predeclared_baseline")

    def test_holdout_rejects_custom_output_root(self):
        with self.assertRaises(PermissionError):
            run("R0", "holdout", output_root=Path("outside"), allow_holdout=True,
                holdout_purpose="predeclared_baseline")

    def test_holdout_blocked_report_requires_same_override(self):
        from kingscode.retrieval_benchmark import record_gpu_blocked
        with self.assertRaises(PermissionError):
            record_gpu_blocked("R1-QWEN", "holdout")


class MetricTests(unittest.TestCase):
    def test_multi_evidence_metrics(self):
        a, b, wrong = p("a", "law_1", "1"), p("b", "law_1", "2", 20, 40), p("wrong", "law_2", "1")
        m = per_question_metrics([wrong, a, b], gold([a, b]))
        self.assertEqual(m["Recall@1"], 0)
        self.assertEqual(m["Recall@3"], 1)
        self.assertEqual(m["Evidence Completeness@3"], 1)
        self.assertAlmostEqual(m["MRR@10"], .5)
        self.assertAlmostEqual(m["MAP@10"], (1 / 2 + 2 / 3) / 2)
        self.assertEqual(m["Document Mismatch Rate"], 1)

    def test_partial_evidence_is_not_complete(self):
        a, b = p("a", "law_1", "1"), p("b", "law_1", "2", 20, 40)
        m = per_question_metrics([a], gold([a, b]))
        self.assertEqual(m["Recall@10"], .5)
        self.assertEqual(m["Evidence Completeness@10"], 0)
        self.assertEqual(m["Span Recall"], .5)
        self.assertEqual(m["Span Precision"], 1)

    def test_empty_result_is_document_mismatch(self):
        a = p("a", "law_1", "1")
        m = per_question_metrics([], gold([a]))
        self.assertEqual(m["Document Mismatch Rate"], 1)
        self.assertEqual(m["Recall@10"], 0)

    def test_context_budget_and_stable_values(self):
        a = p("a", "law_1", "1")
        row = {"latency_ms": 5.0, "metrics": per_question_metrics([a], gold([a]))}
        summary = aggregate([row, row])
        self.assertEqual(summary["retrieved_passages"], 1)
        self.assertEqual(summary["unique_documents"], 1)
        self.assertEqual(summary["latency_p50_ms"], 5.0)


class ComplementarityTests(unittest.TestCase):
    def test_oracle_union_recall_uses_fragment_union(self):
        left = [{"id": "q", "metrics": {"Recall@5": .5}, "gold_direct_count": 2,
                 "matched_direct_fragment_ids_by_k": {"5": ["a"]}}]
        right = [{"id": "q", "metrics": {"Recall@5": .5}, "gold_direct_count": 2,
                  "matched_direct_fragment_ids_by_k": {"5": ["b"]}}]
        r = complementarity(left, right, k=5)
        self.assertEqual(r["counts"]["both_hit"], 1)
        self.assertEqual(r["oracle_union_recall"], 1)

    def test_same_ids_required(self):
        with self.assertRaises(ValueError):
            complementarity([], [{"id": "other"}])


class BootstrapTests(unittest.TestCase):
    def test_bootstrap_is_reproducible(self):
        a, b = [0, 1, 0, 1], [1, 1, 1, 1]
        self.assertEqual(paired_bootstrap(a, b), paired_bootstrap(a, b))

    def test_bootstrap_report_same_ids(self):
        left = [{"id": "a", "metrics": {"Evidence Completeness@8": 0, "Recall@10": 0, "MRR@10": 0}}]
        right = [{"id": "a", "metrics": {"Evidence Completeness@8": 1, "Recall@10": 1, "MRR@10": 1}}]
        report = bootstrap_reports(left, right)
        self.assertEqual(report["Recall@10"]["delta"], 1)
        self.assertEqual(report["MRR@10"]["resamples"], 10_000)


class ArtifactIntegrityTests(unittest.TestCase):
    @unittest.skipUnless((ROOT / "corpus/passages.jsonl").exists(), "corpus snapshot required")
    def test_schema_split_and_canonical_gold_integrity(self):
        report = verify_benchmark()
        self.assertTrue(report["ok"])
        self.assertTrue(report["question_gold_separated"])
        self.assertTrue(report["gold_ids_resolved"])
        self.assertFalse(report["split_overlap"])

    def test_question_files_have_no_gold_fields(self):
        forbidden = {"gold_document_ids", "gold_fragment_ids", "evidence", "gold_spans", "legal_basis", "expected_answer"}
        for split in ["dev", "validation", "holdout"]:
            for row in read_jsonl(BENCHMARK_ROOT / "questions" / f"{split}.jsonl"):
                self.assertFalse(forbidden & row.keys())

    def test_question_and_gold_ids_are_unique_per_split(self):
        all_ids = set()
        for split in ["dev", "validation", "holdout"]:
            questions = read_jsonl(BENCHMARK_ROOT / "questions" / f"{split}.jsonl")
            golds = read_jsonl(BENCHMARK_ROOT / "gold" / f"{split}.jsonl")
            ids = {row["id"] for row in questions}
            self.assertEqual(len(ids), len(questions))
            self.assertEqual(ids, {row["id"] for row in golds})
            self.assertFalse(all_ids & ids)
            all_ids |= ids

    def test_explicit_candidate_gate_requires_exact_pinned_passage_prefix(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp:
            repo = Path(temp)
            base, candidate = repo / "corpus", repo / "candidate"
            for directory in (base / "graph", base / "index", candidate / "graph", candidate / "index"):
                directory.mkdir(parents=True, exist_ok=True)
            base_files = {
                "passages.jsonl": b'{"passage_id":"base:1"}\n',
                "graph/nodes.jsonl": b'{"node_id":"base"}\n',
                "graph/edges.jsonl": b"",
                "index/bm25.json": b"{\"vocabulary\": []}\n",
            }
            for name, content in base_files.items():
                (base / name).write_bytes(content)
            base_manifest = {"version": "corpus-v0.1",
                             "hashes": {name: file_hash(base / name) for name in base_files if name != "index/bm25.json"},
                             "bm25_sha256": file_hash(base / "index/bm25.json")}
            write_json(base / "manifest.json", base_manifest)
            (candidate / "passages.jsonl").write_bytes(base_files["passages.jsonl"] + b'{"passage_id":"add:1"}\n')
            for name in ("graph/nodes.jsonl", "graph/edges.jsonl"):
                (candidate / name).write_bytes(base_files[name])
            (candidate / "index/bm25.json").write_bytes(base_files["index/bm25.json"])
            candidate_manifest = {
                "version": "candidate", "status": "diagnostic_not_competitive_freeze",
                "inputs": {"corpus": {"version": base_manifest["version"],
                                      "manifest_sha256": file_hash(base / "manifest.json"),
                                      "passages_sha256": file_hash(base / "passages.jsonl")}},
                "hashes": {name: file_hash(candidate / name) for name in ("passages.jsonl", "graph/nodes.jsonl", "graph/edges.jsonl")},
                "bm25_sha256": file_hash(candidate / "index/bm25.json"),
                "n_documentos": 2, "n_indexed": 2,
            }
            write_json(candidate / "manifest.json", candidate_manifest)
            declared = benchmark_manifest()
            declared["corpus"] = {"version": "corpus-v0.1",
                                   **{name: base_manifest["hashes"][name] for name in base_manifest["hashes"]},
                                   "bm25_sha256": base_manifest["bm25_sha256"]}
            with patch("kingscode.retrieval_benchmark.ROOT", repo), \
                 patch("kingscode.retrieval_benchmark.benchmark_manifest", return_value=declared):
                proof = _verify_declared_hashes(candidate, allow_corpus_additions=True)
                self.assertEqual(proof["status"], "verified_append_only_extension")
                self.assertTrue(proof["baseline_passage_prefix_preserved"])
                self.assertEqual(proof["baseline_passages_sha256"], file_hash(base / "passages.jsonl"))

                (candidate / "passages.jsonl").write_bytes(b'{"passage_id":"tampered"}\n')
                candidate_manifest["hashes"]["passages.jsonl"] = file_hash(candidate / "passages.jsonl")
                write_json(candidate / "manifest.json", candidate_manifest)
                with self.assertRaisesRegex(ValueError, "preserve every baseline passage"):
                    _verify_declared_hashes(candidate, allow_corpus_additions=True)


class VariantRegistrationTests(unittest.TestCase):
    def test_diagnostic_configuration_records_actual_graph_and_parameters(self):
        from kingscode.retrieval_benchmark import _executed_config
        self.assertEqual(_executed_config("R0-GRAPH-AUTO-DIAGNOSTIC")["graph_mode"], "auto")
        r6 = _executed_config("R6-BM25-DIAGNOSTIC")
        self.assertEqual(r6["experiment"], "R6")
        self.assertEqual(r6["effective_parameters"]["candidate_multiplier"], 4)
        self.assertTrue(r6["diagnostic"])

    def test_all_planned_neural_variants_registered(self):
        for variant in ["R1-BGE", "R1-QWEN", "R2-BGE", "R2-QWEN", "R3", "R4", "R5", "R6", "R7", "R8"]:
            self.assertIn(variant, GPU_VARIANT_PREREQUISITES)


if __name__ == "__main__":
    unittest.main()
