"""Focused regressions for citation quality and fail-fast GPU diagnostics."""
from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from kingscode.common import ROOT
from kingscode.generation.hf_decoder import DecoderFailure, HFDecoder
from kingscode.reasoning.batch import BatchRunner
from kingscode.reasoning.citation_builder import build_references, render_reference
from kingscode.reasoning.citation_repair import repair_citations
from kingscode.reasoning.contracts import Question


FIXTURES = json.loads((ROOT / "tests/fixtures/member_b_official_passages.json").read_text(encoding="utf-8"))


class CitationQualityTests(unittest.TestCase):
    def test_cli_fill_limit_is_forwarded_and_identified_without_loading_gpu(self):
        from tools.member_b import _pipeline, build_parser

        args = build_parser().parse_args([
            "batch", "--fixture-evidence", "--citation-fill", "--citation-fill-extra", "0"])
        pipeline, identity = _pipeline(args)
        self.assertEqual(pipeline.citation_fill_extra, 0)
        self.assertEqual(identity["citation_fill_extra"], 0)
        self.assertEqual(identity["cite_mentions"], 0)
        args = build_parser().parse_args(["batch", "--fixture-evidence", "--citation-fill-extra", "1"])
        with self.assertRaises(ValueError):
            _pipeline(args)

    def test_wrong_article_does_not_loop_through_code_renames(self):
        passage = dict(FIXTURES[0])
        passage.update(article="240", canonical_body=["codigo_penal", None, None],
                       norm_name="Código Penal", text="Código Penal. ARTÍCULO 240. Hurto calificado.")
        row = {"respuesta": "El artículo 241 del Código Penal regula este hecho."}
        fixed, report = repair_citations(row, [passage])
        self.assertNotIn("241", fixed["respuesta"])
        self.assertEqual(sum(a["action"] == "renamed_to_evidence_name" for a in report["actions"]), 0)
        self.assertLess(len(report["actions"]), 5)

    def test_unsupported_only_sentence_is_not_left_grammatically_broken(self):
        row = {"respuesta": "El artículo 113 del Código Civil establece el requisito."}
        fixed, report = repair_citations(row, [FIXTURES[0]])
        self.assertEqual(fixed["respuesta"], "")
        self.assertIn("emptied_after_unsupported_citation", [a["action"] for a in report["actions"]])

    def test_fill_cap_preserves_declared_source_and_limits_unselected_sources(self):
        passages = FIXTURES[:5]
        used = [passages[0]["passage_id"]]
        declared = build_references(passages, used, max_refs=5, fill_ranked=True, fill_ranked_limit=0)
        one_extra = build_references(passages, used, max_refs=5, fill_ranked=True, fill_ranked_limit=1)
        self.assertEqual(declared, [render_reference(passages[0])])
        self.assertEqual(one_extra[:1], declared)
        self.assertLessEqual(len(one_extra), 2)
        with self.assertRaises(ValueError):
            build_references(passages, used, fill_ranked_limit=-1)


class MemoryGuardTests(unittest.TestCase):
    def test_spill_aborts_with_physical_and_reserved_bytes(self):
        decoder = object.__new__(HFDecoder)
        decoder.alias, decoder.precision, decoder.last_usage = "qwen3-8b", "bf16", {"input_tokens": 100}
        decoder.torch = SimpleNamespace(cuda=SimpleNamespace(
            get_device_properties=lambda index: SimpleNamespace(total_memory=24),
            max_memory_reserved=lambda index: 57))
        with self.assertRaises(DecoderFailure) as caught:
            decoder._reject_memory_spill("generate")
        self.assertEqual(caught.exception.code, "GPU_MEMORY_SPILL")
        self.assertEqual(caught.exception.detail["peak_reserved_vram_bytes"], 57)
        decoder.torch.cuda.max_memory_reserved = lambda index: 23
        decoder._reject_memory_spill("generate")

    def test_batch_preserves_error_and_stops_instead_of_fallback(self):
        class SpillingPipeline:
            def run(self, question):
                raise DecoderFailure("GPU_MEMORY_SPILL", {"peak_reserved_vram_bytes": 57})

        with TemporaryDirectory() as directory:
            run_dir = Path(directory)
            with self.assertRaises(DecoderFailure):
                BatchRunner(SpillingPipeline(), run_dir, retries=2).run(
                    [Question(1, "Pregunta", "semi_open")])
            error = json.loads((run_dir / "errors/1.json").read_text(encoding="utf-8"))
            self.assertEqual(error["attempts"][0]["code"], "GPU_MEMORY_SPILL")
            self.assertFalse((run_dir / "items/1.json").exists())
            self.assertFalse((run_dir / "submissions.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
