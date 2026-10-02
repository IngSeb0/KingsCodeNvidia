"""Regressions from the first real Qwen3-8B run on the RTX 4090 (2026-10-01)."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from kingscode.common import ROOT, read_json
from kingscode.generation.prompts import length_warnings, parse_response, parse_response_v3, sentence_count
from kingscode.reasoning import Pipeline, Question
from kingscode.reasoning.official import official_bodies

FIXTURES = read_json(ROOT / "tests/fixtures/member_b_official_passages.json")
# Literal raw_response of gpu_smoke.py --model qwen3-8b (BF16, temperature 0) on the 4090.
QWEN_4090_RAW = (
    "{\"abstencion\":false,\"respuesta\":\"El objeto del artículo 1 de la Ley 1010 de 2006 es definir, prevenir, corregir y "
    "sancionar las diversas formas de agresión, maltrato, vejámenes, trato desconsiderado y ofensivo, así como todo ultraje "
    "a la dignidad humana que se ejercen sobre quienes realizan sus actividades económicas en el contexto de una relación "
    "laboral privada o pública. Este artículo protege bienes jurídicos como el trabajo en condiciones dignas y justas, la "
    "libertad, la intimidad, la honra y la salud mental de los trabajadores, empleados, la armonía entre quienes comparten "
    "un mismo ambiente laboral y el buen ambiente en la empresa.\",\"palabras_clave\":[\"Ley 1010 de 2006\",\"artículo 1\","
    "\"objeto de la ley\",\"bienes jurídicos\"],\"referencia_legal\":\"ley_1010_de_2006:00000:3a5f84542db4\","
    "\"pasajes_usados\":[\"ley_1010_de_2006:00000:3a5f84542db4\"]}")
Q = Question(1,"¿Cuál es el objeto del artículo 1 de la Ley 1010 de 2006?", "semi_open")


class ReplayDecoder:
    """Returns the recorded 4090 output through the real v3 parser, like HFDecoder."""
    name, version = "qwen3-8b-replay", "b968826"

    def __init__(self):
        self.last_usage = {}

    def generate(self, question, passages, prompt, generation):
        row, meta = parse_response_v3(QWEN_4090_RAW, question, passages)
        self.last_usage = {"model": "qwen3-8b", "prompt_version": "grounded-formats-v3", **meta}
        return row


class QwenSmokeRegressionTests(unittest.TestCase):
    def test_two_sentence_grounded_answer_is_kept_with_a_warning(self):
        row, meta = parse_response_v3(QWEN_4090_RAW, Q, [deepcopy(FIXTURES[1])])
        self.assertFalse(row["abstencion"])
        self.assertEqual(meta["format_warnings"], ["semi_open_sentences_2_outside_3_5"])
        self.assertEqual(meta["attribution"]["status"], "explicit")

    def test_legacy_v1_v2_contract_still_rejects_length(self):
        value = json.loads(QWEN_4090_RAW)
        value.pop("pasajes_usados")
        with self.assertRaises(ValueError):
            parse_response(json.dumps(value, ensure_ascii=False), Q, [deepcopy(FIXTURES[1])])

    def test_pipeline_replaces_passage_id_with_canonical_citation(self):
        pipeline = Pipeline(lambda *a, **k: [deepcopy(FIXTURES[1]), deepcopy(FIXTURES[0])], decoder=ReplayDecoder(),
                            graph_policy="off", retrieval_mode="base")
        row, trace = pipeline.run(Q)
        self.assertFalse(row["abstencion"])
        self.assertNotIn(":", row["referencia_legal"])
        self.assertIn(("ley", "1010", "2006"), {tuple(b) for b in official_bodies(row["referencia_legal"])})
        self.assertEqual(trace["diagnostics"]["format_warnings"], ["semi_open_sentences_2_outside_3_5"])

    def test_deterministic_decoder_failure_is_not_retried(self):
        from kingscode.generation.hf_decoder import DecoderFailure
        from kingscode.reasoning.batch import BatchRunner
        calls = []

        class Failing:
            def run(self, question):
                calls.append(question.id)
                raise DecoderFailure("INVALID_MODEL_OUTPUT", {})

        with tempfile.TemporaryDirectory() as tmp:
            report = BatchRunner(Failing(), Path(tmp), retries=2).run([Q])
        self.assertEqual(calls, [Q.id])
        self.assertEqual(report["counts"]["fallback"], 1)

    def test_long_evidence_drops_lowest_ranked_passages_from_prompt_only(self):
        from unittest.mock import patch
        from kingscode.generation.hf_decoder import ATTN_IMPLEMENTATION, HFDecoder
        from kingscode.reasoning.decoder import GENERATION_CONFIG, PromptSpec
        from test_gpu_preparation import FakeInputs, FakeTokenizer, fake_torch, fake_transformers

        class LengthTokenizer(FakeTokenizer):
            """3000 tokens per passage in the prompt: 8 passages never fit 8192."""
            def __call__(self, text, **kwargs):
                user = json.loads(json.loads(text[0])[1]["content"])
                return FakeInputs(500 + 3000 * len(user["evidencia"]))

        evidence = [dict(deepcopy(FIXTURES[i % 5]), passage_id=f"p{i}") for i in range(8)]
        transformers, model = fake_transformers(LengthTokenizer())
        decoder = HFDecoder("qwen3-8b", torch_module=fake_torch(), transformers_module=transformers)
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={}):
            row = decoder.generate(Q, evidence, PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertEqual(decoder.last_usage["evidence_in_prompt"], 2)        # 500 + 2*3000 + 512 <= 8192
        self.assertEqual(decoder.last_usage["evidence_dropped_for_context"], [f"p{i}" for i in range(2, 8)])
        self.assertEqual(len(row["pasajes_recuperados"]), 8)                  # the official row keeps all
        self.assertEqual(transformers.AutoModelForCausalLM.from_pretrained.call_args.kwargs["attn_implementation"], "sdpa")
        self.assertEqual(ATTN_IMPLEMENTATION, "sdpa")
        model.generate.assert_called_once()

    def test_max_context_override_shows_more_evidence_and_respects_native_limit(self):
        from unittest.mock import patch
        from kingscode.generation.hf_decoder import HFDecoder
        from kingscode.reasoning.decoder import GENERATION_CONFIG, PromptSpec
        from test_gpu_preparation import FakeInputs, FakeTokenizer, fake_torch, fake_transformers

        class LengthTokenizer(FakeTokenizer):
            def __call__(self, text, **kwargs):
                user = json.loads(json.loads(text[0])[1]["content"])
                return FakeInputs(500 + 3000 * len(user["evidencia"]))

        evidence = [dict(deepcopy(FIXTURES[i % 5]), passage_id=f"p{i}") for i in range(8)]
        transformers, model = fake_transformers(LengthTokenizer())
        model.config.max_position_embeddings = 40960  # Qwen3-8B native context
        decoder = HFDecoder("qwen3-8b", torch_module=fake_torch(), transformers_module=transformers, max_context_tokens=16384)
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={}):
            decoder.generate(Q, evidence, PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertEqual(decoder.last_usage["evidence_in_prompt"], 5)        # 500 + 5*3000 + 512 <= 16384
        self.assertEqual(HFDecoder("qwen3-8b").candidate["max_context_tokens"], 8192)  # default unchanged
        for bad in (4096, 65536, "16384"):
            with self.assertRaises(ValueError):
                HFDecoder("qwen3-8b", max_context_tokens=bad)
        transformers, model = fake_transformers(LengthTokenizer())          # native 8192 < 16384
        decoder = HFDecoder("qwen3-8b", torch_module=fake_torch(), transformers_module=transformers, max_context_tokens=16384)
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={}):
            with self.assertRaises(Exception):
                decoder.generate(Q, evidence, PromptSpec("semi_open"), dict(GENERATION_CONFIG))

    def test_missing_abstencion_on_complete_answer_is_an_answer(self):
        value = json.loads(QWEN_4090_RAW)
        value.pop("abstencion")
        row, meta = parse_response_v3(json.dumps(value, ensure_ascii=False), Q, [deepcopy(FIXTURES[1])])
        self.assertFalse(row["abstencion"])
        self.assertIn("inferred_abstencion_false_from_complete_answer", meta["field_coercions"])
        value["abstencion"] = "false"
        row, meta = parse_response_v3(json.dumps(value, ensure_ascii=False), Q, [deepcopy(FIXTURES[1])])
        self.assertEqual(meta["field_coercions"][0], "coerced_string:abstencion")

    def test_incomplete_or_reserved_objects_are_still_rejected(self):
        value = json.loads(QWEN_4090_RAW)
        value.pop("abstencion"); value.pop("palabras_clave")       # incomplete: never inferred
        with self.assertRaises(ValueError):
            parse_response_v3(json.dumps(value, ensure_ascii=False), Q, [deepcopy(FIXTURES[1])])
        value = json.loads(QWEN_4090_RAW); value["pasajes_recuperados"] = []
        with self.assertRaises(ValueError):
            parse_response_v3(json.dumps(value, ensure_ascii=False), Q, [deepcopy(FIXTURES[1])])

    def test_multiple_choice_shape_is_normalized_without_new_content(self):
        q = Question(2, "¿Qué regula la Ley 1010 de 2006?", "multiple_choice", {"A": "Acoso laboral", "B": "Pensiones", "C": "Salud"})
        raw = json.dumps({"respuesta_correcta": "A) Acoso laboral", "justificacion": ["Artículo 1 de la Ley 1010 de 2006.", "Define el acoso."],
                          "descarte_opciones": {"A": "correcta", "B)": "No trata pensiones.", "C": 3, "E": "no existe"},
                          "comentario": "extra"}, ensure_ascii=False)
        row, meta = parse_response_v3(raw, q, [deepcopy(FIXTURES[1])])
        self.assertEqual(row["respuesta_correcta"], "A")
        self.assertEqual(row["descarte_opciones"], {"B": "No trata pensiones.", "C": "3"})
        self.assertEqual(row["justificacion"], "Artículo 1 de la Ley 1010 de 2006. Define el acoso.")
        self.assertNotIn("comentario", row)
        self.assertIn("dropped_extra_key:comentario", meta["field_coercions"])

    def test_over_limit_text_is_cut_at_sentence_boundaries(self):
        long = " ".join(f"Oración número {i} sobre la Ley 1010 de 2006." for i in range(1, 9))
        value = json.loads(QWEN_4090_RAW); value["respuesta"] = long
        row, meta = parse_response_v3(json.dumps(value, ensure_ascii=False), Q, [deepcopy(FIXTURES[1])])
        self.assertEqual(sentence_count(row["respuesta"]), 5)
        self.assertTrue(row["respuesta"].endswith("Oración número 5 sobre la Ley 1010 de 2006."))
        self.assertIn("truncated_to_limit:respuesta", meta["field_coercions"])
        self.assertEqual(meta["format_warnings"], [])

    def test_prompt_v4_is_opt_in_and_versioned(self):
        from kingscode.generation.prompts import PROMPT_V4, build_messages, prompt_sha256, system_prompt
        from kingscode.reasoning.decoder import PromptSpec
        self.assertNotEqual(prompt_sha256(5), prompt_sha256(5, PROMPT_V4))
        v3 = system_prompt("semi_open")
        self.assertNotIn("mínimo 3", v3)                                   # default unchanged
        v4 = build_messages(Q, [deepcopy(FIXTURES[1])], PromptSpec("semi_open"), version=PROMPT_V4)[0]["content"]
        self.assertIn("abstencion (false)", v4)
        self.assertIn("mínimo 3", v4)
        mc = system_prompt("multiple_choice", 5, PROMPT_V4)
        self.assertLess(mc.index("justificacion"), mc.index("respuesta_correcta"))
        with self.assertRaises(ValueError):
            build_messages(Q, [deepcopy(FIXTURES[1])], PromptSpec("semi_open"), version="grounded-formats-v9")

    def test_prompt_v6_reasons_without_hedging_and_keeps_v4_fields(self):
        from kingscode.generation.prompts import PROMPT_V4, PROMPT_V6, build_messages, prompt_sha256, system_prompt
        from kingscode.reasoning.decoder import PromptSpec
        self.assertEqual(PROMPT_V6, "grounded-formats-v6")  # tools/member_b.py builds it from --prompt-version v6
        self.assertNotEqual(prompt_sha256(5, PROMPT_V4), prompt_sha256(5, PROMPT_V6))
        self.assertNotIn("especialidad", system_prompt("semi_open", 5, PROMPT_V4))  # v4 unchanged
        v6 = build_messages(Q, [deepcopy(FIXTURES[1])], PromptSpec("semi_open"), version=PROMPT_V6)[0]["content"]
        for needle in ("la evidencia no menciona", "especialidad", "única que puedes citar", "abstencion (false)", "mínimo 3",
                       "empieza con \"Sí\" o \"No\"", "Tiempo jurídico"):
            self.assertIn(needle, v6)
        mc = system_prompt("multiple_choice", 5, PROMPT_V6)
        self.assertLess(mc.index("justificacion"), mc.index("respuesta_correcta"))
        for fmt in ("multiple_choice", "semi_open", "open_ended"):
            self.assertIn("pasajes_usados", system_prompt(fmt, 5, PROMPT_V6))

    def test_prompt_v7_is_concise_but_preserves_v6_citation_and_reasoning_rules(self):
        from kingscode.generation.prompts import PROMPT_V6, PROMPT_V7, build_messages, prompt_sha256, system_prompt
        from kingscode.reasoning.decoder import PromptSpec
        self.assertNotEqual(prompt_sha256(5, PROMPT_V6), prompt_sha256(5, PROMPT_V7))
        semi = system_prompt("semi_open", 5, PROMPT_V7)
        self.assertIn("exactamente 3 oraciones breves", semi)
        self.assertIn("No repitas", semi)
        self.assertIn("única que puedes citar", semi)
        opened = system_prompt("open_ended", 5, PROMPT_V7)
        self.assertIn("exactamente 5 oraciones", opened)
        self.assertIn("problema jurídico; regla con cita", opened)
        self.assertIn("No hay jurisprudencia aplicable al punto.", opened)
        self.assertEqual(build_messages(Q, [deepcopy(FIXTURES[1])], PromptSpec("semi_open"), version=PROMPT_V7)[0]["role"], "system")

    def test_prompt_v6_adds_authority_from_official_host_only(self):
        import json
        from kingscode.generation.prompts import PROMPT_V4, PROMPT_V6, build_messages, source_authority
        from kingscode.reasoning.decoder import PromptSpec
        self.assertEqual(source_authority("https://www.corteconstitucional.gov.co/relatoria/2025/T-256-25.htm"), "Corte Constitucional")
        self.assertEqual(source_authority("https://cortesuprema.gov.co/x"), "Corte Suprema de Justicia")
        self.assertIsNone(source_authority("https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=1"))
        self.assertIsNone(source_authority(None))
        passage = deepcopy(FIXTURES[1])
        passage["source_url"] = "https://www.corteconstitucional.gov.co/relatoria/2007/C-960-07.htm"
        user = lambda v: json.loads(build_messages(Q, [deepcopy(passage)], PromptSpec("semi_open"), version=v)[1]["content"])
        self.assertEqual(user(PROMPT_V6)["evidencia"][0]["autoridad"], "Corte Constitucional")
        self.assertNotIn("autoridad", user(PROMPT_V4)["evidencia"][0])  # v4 evidence unchanged

    def test_citation_fill_adds_verified_ranked_citations_only_where_ragas_does_not_read(self):
        from kingscode.reasoning.citation_builder import attach_references
        evidence = [deepcopy(FIXTURES[i]) for i in (1, 0, 2, 3, 4)]
        base = {"id": 1, "formato": "semi_open", "abstencion": False, "respuesta": "x", "palabras_clave": ["x"], "referencia_legal": ""}
        attribution = {"status": "explicit", "ids": [FIXTURES[1]["passage_id"]]}
        _, plain = attach_references(dict(base), evidence, attribution, 3)
        _, filled = attach_references(dict(base), evidence, attribution, 5, fill_ranked=True)
        self.assertEqual(len(plain), 1)
        self.assertGreater(len(filled), 1)
        self.assertEqual(filled[0], plain[0])                               # declared passage stays first
        open_row = {"id": 1, "formato": "open_ended", "abstencion": False, "marco_normativo": "", "analisis": "a",
                    "jurisprudencia": "j", "conclusion": "c"}
        _, open_refs = attach_references(open_row, evidence, attribution, 5, fill_ranked=True)
        self.assertEqual(len(open_refs), 1)                                 # RAGAS-read field never filled

    def test_cli_exposes_prompt_and_citation_options(self):
        import subprocess, sys
        from kingscode.common import ROOT
        out = subprocess.run([sys.executable, "tools/member_b.py", "--help"], cwd=ROOT, capture_output=True, text=True).stdout
        self.assertIn("--prompt-version", out)
        self.assertIn("--citation-fill", out)
        self.assertIn("--native-option-fusion", out)
        self.assertIn("--candidate-k", out)
        self.assertIn("--reranker-batch-size", out)
        self.assertIn("--graph-budget", out)

    def test_graph_budget_cli_default_zero_and_upper_bound(self):
        import importlib.util
        from unittest.mock import patch
        from kingscode.common import ROOT
        spec = importlib.util.spec_from_file_location("member_b_graph_budget_parser", ROOT / "tools/member_b.py")
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
        with patch.object(cli, "run_b_command", side_effect=lambda args, parser: args.graph_budget):
            self.assertEqual(cli.main(["batch"]), 10)
            self.assertEqual(cli.main(["batch", "--graph-budget", "0"]), 0)
            self.assertEqual(cli.main(["batch", "--graph-budget", "100"]), 100)
            with self.assertRaises(SystemExit):
                cli.main(["batch", "--graph-budget", "101"])

    def test_graph_budget_is_forwarded_and_changes_run_fingerprint(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        import importlib.util
        from kingscode.common import ROOT
        from kingscode.reasoning.experiments import fingerprint

        spec = importlib.util.spec_from_file_location("member_b_graph_budget_identity", ROOT / "tools/member_b.py")
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)

        class FakeRetriever:
            corpus_hash = "fixture-corpus-sha256"
            def retrieve(self, question, k=8, graph_mode="auto"):
                return []

        def args_for(budget):
            return SimpleNamespace(
                fixture_evidence=False, corpus=None, retriever_mode="bm25", rerank=False,
                graph_policy="router", graph_budget=budget, candidate_k=30, reranker_batch_size=2,
                exact_locator=False, model=None, precision="bf16", allow_optional=False,
                prompt_version="v3", plans=None, retrieval_mode="option", k=8,
                citation_fill=False, native_option_fusion=False,
            )

        identities = []
        for budget in (0, 4):
            with patch("kingscode.Retriever", return_value=FakeRetriever()) as make_retriever:
                _, identity = cli._pipeline(args_for(budget))
            self.assertEqual(make_retriever.call_args.kwargs["graph_budget"], budget)
            self.assertEqual(identity["retriever"]["graph_budget"], budget)
            identities.append(identity)
        self.assertNotEqual(fingerprint(identities[0]), fingerprint(identities[1]))

    def test_diagnostic_script_forwards_and_labels_graph_budget(self):
        from kingscode.common import ROOT
        script = (ROOT / "tools/kingscode_pc_nueva_diagnostico.ps1").read_text(encoding="utf-8")
        self.assertRegex(script, r'\[ValidateRange\(0, 100\)\]\s*\[int\]\$GraphBudget = 10')
        self.assertIn('"--graph-budget", "$GraphBudget"', script)
        self.assertIn("_gb${GraphBudget}", script)
        self.assertIn("graph_budget=$GraphBudget", script)

    def test_rerank_overflow_falls_back_to_pre_rerank_order_deterministically(self):
        import importlib.util, inspect
        from kingscode.common import ROOT
        from kingscode.reasoning.pipeline import supports_query_views
        spec = importlib.util.spec_from_file_location("member_b_cli", ROOT / "tools/member_b.py")
        cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)

        class Inner:
            corpus_hash, reranker, calls = "x", "reranker", []
            def retrieve(self, question, k=8, graph_mode="auto", query_views=None):
                self.calls.append(self.reranker)
                if self.reranker:
                    raise ValueError("Reranker input exceeds max_length; no silent truncation")
                return [{"passage_id": "p1", "retrieval": {"profile": {"candidate_count": 5, "total_ms": 0}}}]

        inner = Inner()
        safe = cli._RerankSafeRetriever(inner)
        out = safe.retrieve("pregunta", 8, "off", query_views=["opcion"])
        self.assertEqual(out[0]["retrieval"]["rerank_skipped"], "input_over_max_length")
        self.assertEqual(out[0]["retrieval"]["profile"]["reranker_status"], "skipped_input_over_max_length")
        self.assertEqual(out[0]["retrieval"]["profile"]["candidate_pairs_when_skipped"], 5)
        self.assertGreaterEqual(out[0]["retrieval"]["profile"]["rerank_skip_recovery_ms"], 0)
        self.assertEqual(inner.calls, ["reranker", None])
        self.assertEqual(inner.reranker, "reranker")                     # restored for the next question
        self.assertTrue(supports_query_views(safe.retrieve))             # pipeline still uses native views

        class Broken(Inner):
            def retrieve(self, *a, **k):
                raise ValueError("other failure")
        with self.assertRaises(ValueError):
            cli._RerankSafeRetriever(Broken()).retrieve("q")             # unrelated errors are not hidden

    def test_dense_build_batches_by_length_and_restores_corpus_order(self):
        import numpy as np
        from types import SimpleNamespace
        from kingscode import neural

        calls = []

        class FakeEncoder:
            config = {"max_length": 4096}
            model = SimpleNamespace(config=SimpleNamespace(hidden_size=2))
            def tokenizer(self, texts, **kwargs):
                return {"input_ids": [[0] * len(t) for t in texts]}
            def encode(self, texts, batch_size=None):
                calls.append([len(t) for t in texts])
                return np.array([[len(t), 0.0] for t in texts], dtype="float32")

        texts = ["x" * n for n in (900, 5, 300, 5, 1200, 40)]
        old = neural.BUILD_TOKEN_BUDGET
        neural.BUILD_TOKEN_BUDGET = 1300
        try:
            vectors = neural.encode_length_sorted(FakeEncoder(), texts)
        finally:
            neural.BUILD_TOKEN_BUDGET = old
        self.assertEqual(vectors[:, 0].tolist(), [900, 5, 300, 5, 1200, 40])     # corpus order restored
        self.assertTrue(all(len(b) * max(b) <= 1300 for b in calls))           # padded batch within budget
        self.assertEqual(calls[0], [5, 5, 40, 300])                             # shortest first, batched together
        with self.assertRaises(ValueError):
            neural.encode_length_sorted(FakeEncoder(), ["x" * 5000])            # over max_length still fails loudly

    def test_length_warnings_cover_words_and_open_ended(self):
        self.assertEqual(length_warnings({"formato": "semi_open", "respuesta": "Uno. Dos. " + "x " * 160 + "."}),
                         ["semi_open_words_163_over_150"])
        self.assertEqual(length_warnings({"formato": "open_ended", "analisis": "Una. Dos."}),
                         ["open_ended_analysis_sentences_2_outside_5_8"])
        self.assertEqual(length_warnings({"formato": "multiple_choice"}), [])

    def test_v4_extracts_one_object_from_prose_v3_stays_strict(self):
        wrapped = "Aquí está la respuesta en formato JSON:\n" + QWEN_4090_RAW + "\nEspero que sea útil."
        with self.assertRaises(ValueError):
            parse_response_v3(wrapped, Q, [deepcopy(FIXTURES[1])])                       # v3 default: strict
        row, meta = parse_response_v3(wrapped, Q, [deepcopy(FIXTURES[1])], extract_embedded=True)
        self.assertFalse(row["abstencion"])
        self.assertEqual(meta["normalization_action"], "extracted_single_object_from_prose")
        self.assertEqual(meta["raw_response"], wrapped)                                  # traceable
        for bad in ["texto " + QWEN_4090_RAW + " otro " + QWEN_4090_RAW,                 # two objects
                    "<think>x</think>" + QWEN_4090_RAW,                                  # hidden reasoning
                    "solo prosa sin objeto", "texto {no es json} fin"]:
            with self.assertRaises(ValueError, msg=bad[:30]):
                parse_response_v3(bad, Q, [deepcopy(FIXTURES[1])], extract_embedded=True)


    def test_cite_mentions_adds_body_level_named_norm_and_guard_accepts_only_opt_in(self):
        from kingscode.reasoning.citation_builder import mentioned_references
        from kingscode.reasoning.guards import CitationGuardError, citation_guard
        from kingscode.reasoning.guards import evidence_record
        passage = deepcopy(FIXTURES[1])                                   # Ley 1010 de 2006, art. 1
        passage["text"] = passage["text"] + " Ver el artículo 113 del Código Civil."
        refs = mentioned_references([passage], [passage["passage_id"]], "", 3)
        self.assertIn("Código Civil", refs)                               # body level, never the article
        self.assertFalse(any("artículo" in r for r in refs))
        row = {"id": 1, "formato": "semi_open", "abstencion": False, "respuesta": "Una. Dos. Tres.",
               "palabras_clave": ["x"], "referencia_legal": "Ley 1010 de 2006; Código Civil",
               "pasajes_recuperados": [evidence_record(passage)]}
        with self.assertRaises(CitationGuardError):
            citation_guard(row, [passage])                                # strict default unchanged
        self.assertTrue(citation_guard(row, [passage], allow_body_mentions=True)["ok"])
        row["referencia_legal"] = "artículo 113 del Código Civil"         # article-level: still strict
        with self.assertRaises(CitationGuardError):
            citation_guard(row, [passage], allow_body_mentions=True)
        row["referencia_legal"] = "Código de Comercio"                     # not named anywhere
        with self.assertRaises(CitationGuardError):
            citation_guard(row, [passage], allow_body_mentions=True)

    def test_cite_mentions_skips_own_body_and_already_cited(self):
        from kingscode.reasoning.citation_builder import mentioned_references
        passage = deepcopy(FIXTURES[1])
        passage["text"] = passage["text"] + " Ley 1010 de 2006 y Código Civil."
        refs = mentioned_references([passage], None, "Código Civil", 3)
        self.assertNotIn("Código Civil", refs)                            # already cited
        self.assertNotIn("Ley 1010 de 2006", refs)                        # own document body


    def test_repair_rewrites_mentioned_norm_instead_of_dropping_only_with_mentions(self):
        from kingscode.reasoning.citation_repair import repair_citations
        passage = deepcopy(FIXTURES[1])
        passage["text"] = passage["text"] + " La Ley 2294 de 2023 modifica esta materia."
        row = {"id": 1, "formato": "semi_open", "abstencion": False,
               "respuesta": "El artículo 32 de la Ley 2294 de 2023 regula el tema. Otra oración.",
               "palabras_clave": ["x"], "referencia_legal": "Ley 1010 de 2006"}
        strict, _ = repair_citations(row, [passage])
        self.assertNotIn("2294", strict["respuesta"])                       # default: sentence dropped
        relaxed, report = repair_citations(row, [passage], allow_body_mentions=True)
        self.assertIn("Ley 2294 de 2023", relaxed["respuesta"])             # kept at body level
        self.assertNotIn("artículo 32", relaxed["respuesta"])
        self.assertIn("rewritten_to_body", [a["action"] for a in report["actions"]])


if __name__ == "__main__":
    unittest.main()
