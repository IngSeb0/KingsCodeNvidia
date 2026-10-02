"""Mechanical unit/regression tests; fixtures are not competitive training data."""
from copy import deepcopy
from pathlib import Path
import re
from unittest.mock import patch
import unittest

from kingscode.common import ROOT, read_json, read_jsonl
from kingscode.corpus import ARTICLE, blocks_from_html, parse_document, segments
from kingscode.evaluation import ranking_metrics, supports
from kingscode.retrieval import BM25Index, Retriever, reciprocal_rank_fusion, tokenize


def timing_free(value):
    """Drop wall-clock *_ms telemetry (differs between identical calls) before comparing results."""
    if isinstance(value, dict):
        return {k: timing_free(v) for k, v in value.items() if not k.endswith("_ms")}
    if isinstance(value, list):
        return [timing_free(v) for v in value]
    return value


class SparseTests(unittest.TestCase):
    def test_bm25_hand_calculation_and_stable_tie(self):
        import math
        docs = [{"passage_id": "b", "text": "alpha beta"}, {"passage_id": "a", "text": "alpha beta"}]
        index = BM25Index(docs)
        rank, scores = index.ranking("alpha", 2)
        self.assertEqual(rank, [1, 0])
        self.assertAlmostEqual(scores[0], math.log(1 + .5 / 2.5))

    def test_accent_stopwords_and_exact_numbers(self):
        self.assertEqual(tokenize("Artículo 1324 de la Constitución"), ["articulo", "1324", "constitucion"])

    def test_empty_and_unknown(self):
        index = BM25Index([{"passage_id": "a", "text": "alpha"}])
        self.assertEqual(index.ranking("xyz", 10)[0], [])
        self.assertEqual(index.ranking("", 10)[0], [])

    def test_rrf_deduplicates_within_ranker(self):
        scores = reciprocal_rank_fusion([[0, 0, 1], [1, 0]])
        self.assertAlmostEqual(scores[0], scores[1])
        self.assertAlmostEqual(scores[0], 1 / 61 + 1 / 62)

    def test_stale_index_rejected(self):
        docs = [{"passage_id": "a", "text": "alpha"}]
        test_root = ROOT / "tmp/test_knowledge"
        test_root.mkdir(parents=True, exist_ok=True)
        # A normal workspace directory also works under Windows sandbox ACLs.
        path = test_root / "stale_index.json"
        BM25Index(docs).save(path, "first")
        with self.assertRaises(ValueError):
            BM25Index.load(path, docs, "second")


class MetricTests(unittest.TestCase):
    def test_mention_is_not_source_evidence(self):
        p = {"canonical_body": ["ley", "1", "2000"], "article": "2", "text": "Ley 2 de 2000"}
        self.assertFalse(supports(p, ("ley", "2", "2000", None)))
        self.assertFalse(supports(p, ("ley", "1", "2000", "3")))

    def test_recall_counts_distinct_targets(self):
        a = {"canonical_body": ["code", None, None], "article": "1"}
        b = {"canonical_body": ["code", None, None], "article": "2"}
        targets = {("code", None, None, "1"), ("code", None, None, "2")}
        m = ranking_metrics([a, a, b], targets)
        self.assertEqual(m["Recall@1"], .5)
        self.assertEqual(m["Recall@3"], 1)
        self.assertLess(m["nDCG@10_unique_targets"], 1)
        self.assertEqual(m["MRR@10"], 1)

    def test_no_labels_not_counted_as_success(self):
        self.assertEqual(ranking_metrics([], set()), {"evaluable": False})


class ParserTests(unittest.TestCase):
    def test_full_dotted_article_number_from_official_heading(self):
        for heading, number in [("ARTÍCULO 2.2.1 . 2.1.5.1. Estudios previos", "2.2.1.2.1.5.1"),
                                ("ARTÍCULO 2.2.1.2,3.5.1. Garantías", "2.2.1.2.3.5.1"),
                                ("ARTÍCULO 134 A. Actos de discriminación", "134A")]:
            self.assertEqual(re.sub(r"\s+", "", ARTICLE.match(heading)[2]).replace(",", "."), number)

    def test_all_ambiguous_article_occurrences_are_excluded(self):
        # Mechanical segmentation fixture, never a QA/training/index dataset.
        meta = {"doc_id": "test", "source_type": "law", "norm_name": "Test", "norm_number": "1", "year": 2000,
                "canonical_body": ["ley", "1", "2000"], "source_url": "https://example.test/", "source_sha256": "a"*64,
                "retrieved_at": "2000-01-01T00:00:00Z", "areas": []}
        blocks = ["ARTÍCULO 1. ALFA", "ARTÍCULO 2. BETA", "ARTÍCULO 1. GAMMA"]
        with patch("kingscode.corpus.blocks_from_html", return_value=(blocks, "Test")):
            _, passages, _, _, info = parse_document(meta, b"html")
        self.assertEqual([p["retrieval_eligible"] for p in passages], [False, True, False])
        self.assertEqual(info["n_ambiguous_fragments"], 2)

    def test_dom_preserves_text_outside_paragraphs_and_skips_hidden(self):
        html = b'<div class="descripcion-contenido"><p>alpha</p>beta<div style="display:none"><p>historical</p></div><p>gamma</p></div>'
        blocks, _ = blocks_from_html(html)
        self.assertEqual(blocks, ["alpha", "beta", "gamma"])

    def test_chunk_offsets_preserve_every_nonspace_character(self):
        text = ("alpha beta. " * 800) + "\n\ngamma"
        spans = list(segments(text, 0, len(text)))
        self.assertEqual("".join("".join(text[a:b].split()) for a, b in spans), "".join(text.split()))
        self.assertTrue(all(b - a <= 3600 for a, b in spans))

    def test_real_amendment_not_mislabelled_as_new_article(self):
        path = ROOT / "corpus/raw/ley_979_de_2005.meta.json"
        if not path.exists():
            self.skipTest("official snapshot required")
        meta = read_json(path)
        clean, passages, _, _, info = parse_document(meta, (ROOT / meta["raw_path"]).read_bytes())
        self.assertEqual(info["n_articulos"], 5)
        self.assertFalse(info["duplicate_headings"])
        self.assertIn("quedará así", clean)
        for p in passages:
            self.assertEqual(p["text"], p["text_prefix"] + clean[p["clean_start"]:p["clean_end"]])


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (ROOT / "corpus/manifest.json").exists():
            raise unittest.SkipTest("build corpus first")
        cls.retriever = Retriever()

    def test_contract_limits_errors_and_no_mutation(self):
        r = self.retriever
        self.assertEqual(r.retrieve("", 8), [])
        self.assertEqual(r.retrieve("contrato", 0), [])
        with self.assertRaises(TypeError):
            r.retrieve({"pregunta": "x", "legal_basis": "x"})
        with self.assertRaises(ValueError):
            r.retrieve("x", 1, "invalid")
        with self.assertRaises(ValueError):
            r.retrieve("x", -1)
        result = r.retrieve("salario contrato trabajo", 3, "off")
        expected = deepcopy(result)
        result[0]["scores"]["bm25"] = -100
        result[0]["graph_node_ids"].clear()
        self.assertEqual(timing_free(expected), timing_free(r.retrieve("salario contrato trabajo", 3, "off")))

    def test_repeated_queries_and_graph_modes(self):
        r = self.retriever
        for mode in ["off", "auto", "on"]:
            a = r.retrieve("artículo modificado contrato trabajo", 5, mode)
            self.assertEqual(timing_free(a), timing_free(r.retrieve("artículo modificado contrato trabajo", 5, mode)))
            self.assertTrue(all(p["is_current_text"] is not False for p in a))
            self.assertTrue(all(p["retrieval_eligible"] for p in a))
            self.assertEqual(len(a), len({p["passage_id"] for p in a}))

    def test_missing_dense_is_explicit(self):
        if not (ROOT / "corpus/index/dense.meta.json").exists():
            with self.assertRaisesRegex(RuntimeError, "Dense index is missing"):
                Retriever(mode="hybrid")


if __name__ == "__main__":
    unittest.main()
