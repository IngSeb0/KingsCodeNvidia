"""Gate 1B unit/regression tests. Fixtures are unchanged official passages.

Mutations are adversarial validation probes only, never training/index material.
"""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from kingscode.common import ROOT, read_json, write_json, write_jsonl
from kingscode.reasoning import Question, DummyDecoder, Pipeline, answer, citation_guard, normalize_query, route_graph, validate_submission, RetrieverGraphRouter
from kingscode.reasoning.contracts import load_questions, public_question
from kingscode.reasoning.decoder import abstention_row
from kingscode.reasoning.evaluation import run_eval
from kingscode.reasoning.experiments import fingerprint, run_experiment, validate_config
from kingscode.reasoning.guards import CitationGuardError, SubmissionValidationError, evidence_record
from kingscode.reasoning.legal import references
from kingscode.reasoning.pipeline import query_variants, rrf_merge
from kingscode.reasoning.policy import assess_evidence

FIXTURES = read_json(ROOT / "tests/fixtures/member_b_official_passages.json")


def evidence():
    return deepcopy(FIXTURES[1])  # Ley 1010 de 2006, Artículo 1.


def cited_row(passages=None, text="Artículo 1 de la Ley 1010 de 2006"):
    passages = [evidence()] if passages is None else passages
    return {"id": 79, "formato": "semi_open", "abstencion": False,
            "respuesta": text, "palabras_clave": ["fuente"], "referencia_legal": "Ley 1010 de 2006",
            "pasajes_recuperados": [evidence_record(p) for p in passages]}


class QueryTests(unittest.TestCase):
    def test_exact_references_negation_and_temporality_survive(self):
        raw = "  ¿NO se derogó el artículo 2.2.1.2 del Decreto 1082 de 2015?\nCGP "
        q = normalize_query(raw)
        self.assertEqual(q.original, raw)
        self.assertIn("NO se derogó", q.normalized)
        self.assertIn("2.2.1.2", q.retrieval_text)
        self.assertIn("Código General del Proceso", q.expansions)
        self.assertIn("repeal", q.signals)
        self.assertEqual(q, normalize_query(raw))

    def test_reference_spans_match_preserved_normalized_text(self):
        q = normalize_query("Artículos 13 y 15 de la Constitución Política y Ley N.º 1010 de 2006")
        for r in q.references:
            self.assertEqual(q.normalized[r.start:r.end], r.raw)
        self.assertEqual([r.article for r in q.references if r.kind == "article"], ["13", "15"])
        self.assertIn(("ley", "1010", "2006"), [r.body for r in q.references])

    def test_case_docket_and_authority(self):
        q = normalize_query("Sentencia SU-455/20 de la Corte Constitucional; radicado 11001-03-15-000-2020-01234-00")
        self.assertIn(("jurisprudencia", "SU-455", "2020"), [r.body for r in q.references])
        self.assertIn(("radicado", "11001031500020200123400", None), [r.body for r in q.references])
        self.assertIn("Corte Constitucional", q.authorities)
        self.assertIn("11001-03-15-000-2020-01234-00", q.normalized)

    def test_wrong_year_never_aliases_to_code(self):
        self.assertEqual(references("Ley 1564 de 2013")[0].body, ("ley", "1564", "2013"))

    def test_ambiguous_abbreviation_not_expanded(self):
        q = normalize_query("C.P. y C.C.")
        self.assertEqual(q.expansions, ())
        self.assertTrue(all(not r.complete for r in q.references))

    def test_dotted_hyphenated_and_letter_article(self):
        for text, number in [("Artículo 2.2.1.2 del Decreto 1082 de 2015", "2.2.1.2"),
                             ("Artículo 134 A del Código Penal", "134a"), ("Artículo 861-1 del Estatuto Tributario", "861-1")]:
            self.assertEqual(next(r.article for r in references(text) if r.kind == "article"), number)

    def test_ordinal_article_link_keeps_article_identity(self):
        for marker in ("º", "°"):
            refs = references(f"Artículo 5{marker} de la Ley 1010 de 2006")
            article = next(r for r in refs if r.kind == "article")
            self.assertEqual(article.article, "5")
            self.assertEqual(article.body, ("ley", "1010", "2006"))

    def test_ranges_and_incomplete_citations_fail_closed(self):
        for text in ["Artículos 13 a 15", "Artículo 13 bis", "Ley 1010", "Sentencia T-999", "T-999", "Artículo XIV", "Leyes 80 y 1150", "Ley número 999"]:
            self.assertTrue(any(not r.complete for r in references(text)), text)

    def test_label_record_is_not_a_query(self):
        with self.assertRaises(TypeError):
            normalize_query({"pregunta": "x", "legal_basis": "secret"})

    def test_public_projection_removes_labels_and_nested_annotations(self):
        public = public_question({"id": 1, "pregunta": "consulta", "formato": "multiple_choice", "opciones": {"A": "opción"},
                                  "expected_answer": "CANARY", "legal_basis": "CANARY", "respuesta_correcta": "D"})
        self.assertNotIn("CANARY", json.dumps(public.public_record()))
        with self.assertRaises(ValueError):
            public_question({"id": 1, "pregunta": "x", "formato": "multiple_choice", "opciones": {"A": {"text": "x", "is_correct": True}}})


class RoutingPolicyTests(unittest.TestCase):
    def test_off_for_direct_supported_reference(self):
        self.assertEqual(route_graph("Artículo 1 de la Ley 1010 de 2006", [evidence()]), "off")

    def test_auto_for_missing_reference(self):
        self.assertEqual(route_graph("Artículo 999 de la Ley 1010 de 2006", [evidence()]), "auto")

    def test_on_for_relations_hierarchy_temporality_and_empty_evidence(self):
        for q in ["norma modificada", "norma derogada", "remisión", "reglamentación", "parágrafo", "vigencia", "jerarquía"]:
            self.assertEqual(route_graph(q, [evidence()]), "on", q)
        self.assertEqual(route_graph("consulta directa", []), "on")

    def test_callback_returns_bool_not_truthy_off_string(self):
        adapter = RetrieverGraphRouter()
        self.assertIs(adapter("Artículo 1 de la Ley 1010 de 2006"), False)
        self.assertIs(adapter("¿Fue derogada?"), True)
        for decision in ["off", "auto", "on"]:
            adapter.bind("consulta", decision)
            self.assertIs(adapter("consulta"), decision != "off")

    def test_empty_and_irrelevant_evidence(self):
        self.assertIn("retrieval_empty", assess_evidence("consulta", []).reasons)
        self.assertIn("weak_lexical_evidence", assess_evidence("astronautas telescopios", [evidence()]).reasons)

    def test_conflicting_source_interval_abstains_without_invoking_backend(self):
        a, b = evidence(), evidence()
        b["text"] += " INCOMPATIBLE"
        backend = Mock()
        row = answer("Artículo 1 de la Ley 1010 de 2006", [a, b], "semi_open", decoder=backend)
        self.assertTrue(row["abstencion"])
        self.assertEqual(row["pasajes_recuperados"], [])
        backend.generate.assert_not_called()

    def test_opposite_literal_claims_are_a_conflict(self):
        a, b = evidence(), evidence()
        a.update(text="Podrá proceder.", text_prefix="", passage_id="probe:a")
        b.update(text="No podrá proceder.", text_prefix="", passage_id="probe:b")
        self.assertIn("opposed_literal_claims_same_article", assess_evidence("consulta", [a, b]).conflicts)

    def test_ineligible_evidence_is_not_emitted(self):
        p = evidence(); p["retrieval_eligible"] = False
        row = answer("Artículo 1 de la Ley 1010 de 2006", [p], "semi_open")
        self.assertTrue(row["abstencion"])
        self.assertEqual(row["pasajes_recuperados"], [])

    def test_unverified_currency_and_missing_relation_evidence_abstain(self):
        self.assertIn("currency_not_certified", assess_evidence("Vigencia de la Ley 1010 de 2006", [evidence()]).reasons)
        p = evidence(); p["text"] = "Ley 1010 de 2006. Artículo 1. Objeto."
        self.assertIn("missing_relation_evidence:repeal", assess_evidence("¿Fue derogada la Ley 1010 de 2006?", [p]).reasons)


class GuardSchemaTests(unittest.TestCase):
    def test_valid_citation_has_exact_source_article_trace(self):
        p = evidence(); row = cited_row([p]); before = deepcopy(row)
        report = citation_guard(row, [p])
        self.assertTrue(report["ok"])
        self.assertGreater(report["citation_count"], 0)
        self.assertEqual(report["citations"][0]["support"][0]["passage_id"], p["passage_id"])
        self.assertEqual(report["citations"][0]["support"][0]["source_url"], p["source_url"])
        self.assertEqual(row, before)

    def test_unsupported_article_and_year_rejected(self):
        for text in ["Artículo 999 de la Ley 1010 de 2006", "Ley 1010 de 2007", "Ley 1010", "Sentencia T-999"]:
            with self.assertRaises(CitationGuardError, msg=text):
                citation_guard(cited_row(text=text), [evidence()])

    def test_wrong_year_of_code_alias_rejected(self):
        p = deepcopy(FIXTURES[2])
        row = cited_row([p], "Artículo 1 de la Ley 1564 de 2013")
        row["referencia_legal"] = "Ley 1564 de 2013"
        with self.assertRaises(CitationGuardError): citation_guard(row, [p])

    def test_secondary_law_in_code_title_cannot_borrow_its_articles(self):
        p = deepcopy(FIXTURES[3])  # Official Civil Code primary identity: Ley 84/1873.
        for text, valid in [("Artículo 1 de la Ley 84 de 1873", True), ("Artículo 1 de la Ley 57 de 1887", False)]:
            row = cited_row([p], text); row["referencia_legal"] = text
            if valid: self.assertTrue(citation_guard(row, [p])["ok"])
            else:
                with self.assertRaises(CitationGuardError): citation_guard(row, [p])

    def test_explicit_constitution_and_decision_years_are_checked(self):
        for p, good, bad in [(deepcopy(FIXTURES[0]), "Constitución Política de Colombia de 1991", "Constitución Política de Colombia de 1886"),
                             (deepcopy(FIXTURES[4]), "Decisión Andina 486 de 2000", "Decisión Andina 486 de 2005")]:
            for text, valid in [(good, True), (bad, False)]:
                row = cited_row([p], text); row["referencia_legal"] = text
                if valid: self.assertTrue(citation_guard(row, [p])["ok"])
                else:
                    with self.assertRaises(CitationGuardError): citation_guard(row, [p])

    def test_mentioned_other_law_is_not_own_article(self):
        p = evidence(); p["text"] += " Artículo 1 de la Ley 9999 de 2000."
        row = cited_row([p], "Artículo 1 de la Ley 9999 de 2000")
        with self.assertRaises(CitationGuardError): citation_guard(row, [p])

    def test_reference_must_be_in_emitted_evidence(self):
        p, other = evidence(), deepcopy(FIXTURES[0])
        row = cited_row([other])
        with self.assertRaises(CitationGuardError): citation_guard(row, [p, other])

    def test_fabricated_text_url_and_metadata_rejected(self):
        for key in ["texto", "source_url", "article", "doc_id"]:
            row = cited_row(); row["pasajes_recuperados"][0][key] = "forged"
            with self.assertRaises(CitationGuardError): citation_guard(row, [evidence()])

    def test_hidden_keyword_citation_is_also_checked(self):
        row = cited_row(); row["palabras_clave"].append("Ley 9999 de 2000")
        with self.assertRaises(CitationGuardError): citation_guard(row, [evidence()])

    def test_no_citation_non_abstaining_answer_rejected(self):
        row = cited_row(text="Una afirmación sin referencia."); row["referencia_legal"] = "fuente"
        with self.assertRaises(CitationGuardError): citation_guard(row, [evidence()])

    def test_valid_all_formats_dummy_abstains(self):
        for fmt in ["multiple_choice", "semi_open", "open_ended"]:
            row = answer("Artículo 1 de la Ley 1010 de 2006", [evidence()], fmt, question_id=79)
            validate_submission(row)
            self.assertTrue(row["abstencion"])
            self.assertEqual(row["id"], 79)

    def test_invalid_schema_missing_field_wrong_type_nan(self):
        for change in [lambda r:r.pop("respuesta"), lambda r:r.update(id=True),
                       lambda r:r.update(abstencion="true"), lambda r:r["pasajes_recuperados"][0].update(score=float("nan"))]:
            row = cited_row(); change(row)
            with self.assertRaises(SubmissionValidationError): validate_submission(row)

    def test_official_mc_schema_rejects_null_even_for_abstention(self):
        row = answer("consulta", [], "multiple_choice")
        self.assertEqual(row["respuesta_correcta"], "A")
        self.assertIn("no representa una elección", row["justificacion"])
        row["respuesta_correcta"] = None
        with self.assertRaises(SubmissionValidationError): validate_submission(row)

    def test_more_than_ten_and_no_evidence_are_blocking(self):
        for ps in [[], [evidence_record(evidence())] * 11]:
            row = cited_row(); row["pasajes_recuperados"] = ps
            with self.assertRaises(SubmissionValidationError): validate_submission(row)


class PipelineTests(unittest.TestCase):
    def test_context_dropped_passages_are_removed_from_submission_and_guard(self):
        p0, p1 = deepcopy(FIXTURES[0]), deepcopy(FIXTURES[1])

        class ContextTrimmingBackend:
            name, version = "unit_context_trim", "1"
            last_usage = {"evidence_dropped_for_context": [p1["passage_id"]]}
            def generate(self, question, passages, prompt, generation):
                return {"id": question.id, "formato": question.format, "abstencion": False,
                        "respuesta": "La Ley 1010 de 2006 regula el acoso laboral.",
                        "palabras_clave": ["acoso laboral"], "referencia_legal": "",
                        "pasajes_recuperados": [evidence_record(p) for p in passages]}

        retrieve = Mock(side_effect=lambda *args: [deepcopy(p0), deepcopy(p1)])
        row, trace = Pipeline(retrieve, decoder=ContextTrimmingBackend(), graph_policy="off",
                              retrieval_mode="base").run(Question(79, "¿Qué regula el acoso laboral?", "semi_open"))
        delivered = {p["passage_id"] for p in row["pasajes_recuperados"]}
        self.assertEqual(delivered, {p0["passage_id"]})
        self.assertEqual(trace["diagnostics"]["evidence_dropped_for_context"], [p1["passage_id"]])
        dropped = trace["diagnostics"]["evidence_dropped_bodies"]
        self.assertIn(["ley", "1010", "2006"], [body for item in dropped for body in item["bodies"]])
        self.assertEqual(trace["citation_guard"]["unsupported_count"], 0)

    def test_batch_show_answers_prints_question_and_generated_fields(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from kingscode.reasoning.batch import _print_answer
        question = Question(51, "¿Cuál opción aplica?", "multiple_choice", {"A": "primera", "B": "segunda"})
        row = {"respuesta_correcta": "B", "justificacion": "Aplica por la regla indicada.",
               "descarte_opciones": {"A": "No corresponde."}, "abstencion": False}
        output = StringIO()
        with redirect_stderr(output):
            _print_answer(question, row)
        rendered = output.getvalue()
        self.assertIn("id=51 formato=multiple_choice", rendered)
        self.assertIn("¿Cuál opción aplica?", rendered)
        self.assertIn("B) segunda", rendered)
        self.assertIn('respuesta_correcta: "B"', rendered)

    def test_batch_runner_streams_answer_when_show_answers_enabled(self):
        from contextlib import redirect_stderr
        from io import StringIO
        from kingscode.reasoning.batch import BatchRunner

        class AnsweringBackend:
            name, version = "unit_show_answer", "1"
            def generate(self, question, passages, prompt, generation):
                return {"id": question.id, "formato": question.format, "abstencion": False,
                        "respuesta": "La Ley 1010 de 2006 regula el acoso laboral.",
                        "palabras_clave": ["acoso laboral"], "referencia_legal": "",
                        "pasajes_recuperados": [evidence_record(p) for p in passages]}

        question = Question(79, "¿Qué regula el acoso laboral?", "semi_open")
        pipeline = Pipeline(lambda *args: [evidence()], decoder=AnsweringBackend(),
                            graph_policy="off", retrieval_mode="base")
        output = StringIO()
        with tempfile.TemporaryDirectory() as temp, redirect_stderr(output):
            report = BatchRunner(pipeline, Path(temp), retries=0, show_answers=True).run([question])
        self.assertTrue(report["complete"])
        self.assertIn("¿Qué regula el acoso laboral?", output.getvalue())
        self.assertIn("respuesta: \"La Ley 1010 de 2006 regula el acoso laboral.\"", output.getvalue())

    def test_public_retrieval_two_passes_and_modes(self):
        for query, decision, modes in [("Artículo 1 de la Ley 1010 de 2006", "off", ["off"]),
                                       ("Artículo 999 de la Ley 1010 de 2006", "auto", ["off", "auto"]),
                                       ("Vigencia de la Ley 1010 de 2006", "on", ["off", "on"])]:
            retrieve = Mock(side_effect=lambda *args: [evidence()])
            row, trace = Pipeline(retrieve, adapter=RetrieverGraphRouter()).run(Question(1, query, "semi_open"))
            self.assertTrue(row["abstencion"])
            self.assertEqual(trace["graph_decision"], decision)
            self.assertEqual([c.args[2] for c in retrieve.call_args_list], modes)

    def test_no_adapter_auto_uses_explicit_on(self):
        retrieve = Mock(side_effect=lambda *args: [evidence()])
        _, trace = Pipeline(retrieve).run(Question(1, "Artículo 999 de la Ley 1010 de 2006", "semi_open"))
        self.assertEqual((trace["graph_decision"], trace["graph_execution"]), ("auto", "on"))

    def test_unsupported_citation_is_suppressed_not_abstained(self):
        # Enunciado B.5 / plan B2: correct or suppress the citation; do not throw
        # away the item (RAGAS and closed-question accuracy would be lost).
        class FabricatingBackend:
            name, version = "unit_probe_fabricator", "1"
            def generate(self, question, passages, prompt, generation):
                return cited_row(passages, text="El acoso laboral tiene regulación propia. La Ley 9999 de 2000 lo amplía.")
        retrieve = Mock(side_effect=lambda *args: [evidence()])
        row, trace = Pipeline(retrieve, decoder=FabricatingBackend()).run(Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open"))
        self.assertFalse(row["abstencion"])
        self.assertNotIn("9999", row["respuesta"])
        self.assertEqual(trace["citation_guard"]["unsupported_count"], 0)
        validate_submission(row)

    def test_guard_failure_that_repair_cannot_fix_still_downgrades_only_that_item(self):
        # Tampered evidence is not repairable: the batch safety net abstains on
        # this item instead of aborting the other 991 (answer() still raises).
        class TamperingBackend:
            name, version = "unit_probe_tamper", "1"
            def generate(self, question, passages, prompt, generation):
                passages[0]["text"] += " Ley 9999 de 2000."
                return cited_row(passages)
        retrieve = Mock(side_effect=lambda *args: [evidence()])
        row, trace = Pipeline(retrieve, decoder=TamperingBackend()).run(Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open"))
        self.assertTrue(row["abstencion"])
        self.assertEqual(trace["abstention_reason"], "citation_guard_rejected")
        self.assertTrue(trace["citation_guard_fallback"]["evidence_issues"])
        validate_submission(row)

    def test_multiple_choice_never_pre_blocks_on_soft_evidence_reasons(self):
        # Enunciado 6.1: guessing among the given options beats abstention even
        # at random accuracy, so a soft reason (missing_explicit_reference) must
        # never withhold the attempt for multiple_choice, only for free text.
        class ChoosingBackend:
            name, version = "unit_probe_mc", "1"
            def generate(self, question, passages, prompt, generation):
                return {"id": question.id, "formato": "multiple_choice", "abstencion": False,
                        "respuesta_correcta": "A", "justificacion": "Ley 1010 de 2006.",
                        "descarte_opciones": {"B": "no aplica la evidencia"},
                        "pasajes_recuperados": [evidence_record(p) for p in passages]}
        retrieve = Mock(side_effect=lambda *args: [evidence()])
        q = Question(79, "Artículo 999 de la Ley 1010 de 2006", "multiple_choice", {"A": "x", "B": "y"})
        row, trace = Pipeline(retrieve, decoder=ChoosingBackend()).run(q)
        self.assertFalse(row["abstencion"])
        self.assertEqual(row["respuesta_correcta"], "A")
        self.assertIn("missing_explicit_reference", trace["warnings"])

    def test_free_text_still_hard_blocks_on_empty_retrieval(self):
        retrieve = Mock(side_effect=lambda *args: [])
        row, trace = Pipeline(retrieve).run(Question(79, "pregunta sin pasajes disponibles", "semi_open"))
        self.assertTrue(row["abstencion"])
        self.assertIn("retrieval_empty", trace["abstention_reason"])

    def test_query_variants_one_per_option_sorted_else_base_only(self):
        q = normalize_query("Constitución Política")
        self.assertEqual(query_variants(Question(1, "x", "semi_open"), q), (q.retrieval_text,))
        mc = Question(1, "x", "multiple_choice", {"B": "segunda", "A": "primera"})
        self.assertEqual(query_variants(mc, q), (q.retrieval_text, f"{q.retrieval_text} primera", f"{q.retrieval_text} segunda"))

    def test_rrf_merge_boosts_passages_ranked_in_more_lists(self):
        p0, p1, p2 = FIXTURES[0], FIXTURES[1], FIXTURES[2]
        merged = rrf_merge([[p0, p1], [p1, p2]], k=8)
        self.assertEqual([p["passage_id"] for p in merged][0], p1["passage_id"])  # ranked in both lists
        self.assertEqual({p["passage_id"] for p in merged}, {p0["passage_id"], p1["passage_id"], p2["passage_id"]})

    def test_multiple_choice_fans_out_one_retrieve_per_option_and_fuses_rrf(self):
        p0, p1 = FIXTURES[0], FIXTURES[1]

        def fake_retrieve(query_text, k, mode):
            return [deepcopy(p1), deepcopy(p0)] if "opcion_b" in query_text else [deepcopy(p0)]

        retrieve = Mock(side_effect=fake_retrieve)
        q = Question(79, "Constitución Política", "multiple_choice", {"A": "opcion_a", "B": "opcion_b"})
        row, trace = Pipeline(retrieve, decoder=DummyDecoder(), graph_policy="off").run(q)
        self.assertEqual(retrieve.call_count, 3)  # base + opción A + opción B, no graph expansion
        queries = [c.args[0] for c in retrieve.call_args_list]
        self.assertTrue(queries[1].endswith("opcion_a"))
        self.assertTrue(queries[2].endswith("opcion_b"))
        ids = {p["passage_id"] for p in row["pasajes_recuperados"]}
        self.assertEqual(ids, {p0["passage_id"], p1["passage_id"]})

    def test_legacy_three_view_fanout_aggregates_all_retrieval_profiles(self):
        calls = []
        per_call = [
            {"mode": "hybrid", "candidate_k": 30, "query_view_count": 1,
             "dense_encoded_queries": 1, "dense_encode_batches": 1, "candidate_count": 3,
             "reranker_pairs": 3, "reranker_batch_size": 2, "reranker_batches": 2,
             "bm25_ms": 1.0, "dense_ms": 10.0, "fusion_ms": 0.5, "locator_ms": 0.0,
             "graph_ms": 0.0, "reranker_ms": 4.0, "total_ms": 16.0},
            {"mode": "hybrid", "candidate_k": 30, "query_view_count": 1,
             "dense_encoded_queries": 1, "dense_encode_batches": 1, "candidate_count": 4,
             "reranker_pairs": 4, "reranker_batch_size": 2, "reranker_batches": 2,
             "bm25_ms": 2.0, "dense_ms": 20.0, "fusion_ms": 1.0, "locator_ms": 0.0,
             "graph_ms": 0.0, "reranker_ms": 5.0, "total_ms": 28.0},
            {"mode": "hybrid", "candidate_k": 30, "query_view_count": 1,
             "dense_encoded_queries": 1, "dense_encode_batches": 1, "candidate_count": 5,
             "reranker_pairs": 5, "reranker_batch_size": 2, "reranker_batches": 3,
             "bm25_ms": 3.0, "dense_ms": 30.0, "fusion_ms": 1.5, "locator_ms": 0.0,
             "graph_ms": 0.0, "reranker_ms": 6.0, "total_ms": 40.0},
        ]

        def fake_retrieve(query, k, mode):
            profile = per_call[len(calls)]
            calls.append(query)
            passage = evidence()
            passage["retrieval"] = {"profile": profile}
            return [passage]

        q = Question(79, "Constitución Política", "multiple_choice",
                     {"A": "opcion_a", "B": "opcion_b"})
        row, trace = Pipeline(fake_retrieve, decoder=DummyDecoder(), graph_policy="off").run(q)

        self.assertEqual(len(calls), 3)  # Q0 plus two options
        self.assertEqual([p["passage_id"] for p in row["pasajes_recuperados"]], [evidence()["passage_id"]])
        self.assertEqual(len(trace["retrieval_profiles"]), 1)  # one profile per retrieval pass
        aggregate = trace["retrieval_profiles"][0]
        self.assertEqual(aggregate["query_view_count"], 3)
        self.assertEqual(aggregate["candidate_count"], 12)
        self.assertEqual(aggregate["reranker_pairs"], 12)
        self.assertEqual(aggregate["reranker_batches"], 7)
        self.assertEqual(aggregate["dense_encoded_queries"], 3)
        self.assertEqual(aggregate["dense_encode_batches"], 3)
        self.assertEqual(aggregate["bm25_ms"], 6.0)
        self.assertEqual(aggregate["dense_ms"], 60.0)
        self.assertEqual(aggregate["fusion_ms"], 3.0)
        self.assertEqual(aggregate["reranker_ms"], 15.0)
        self.assertEqual(aggregate["total_ms"], 84.0)

    def test_single_and_native_retrieval_keep_profile_values(self):
        profile = {"mode": "hybrid", "query_view_count": 3, "candidate_count": 9,
                   "reranker_pairs": 9, "reranker_batches": 5, "reranker_ms": 12.5, "total_ms": 20.0}

        def native_retrieve(question, k=8, graph_mode="auto", query_views=None):
            passage = evidence()
            passage["retrieval"] = {"profile": dict(profile)}
            return [passage]

        q = Question(79, "Constitución Política", "multiple_choice", {"A": "x", "B": "y"})
        _, native_trace = Pipeline(native_retrieve, graph_policy="off", native_option_fusion=True).run(q)
        self.assertEqual(native_trace["retrieval_profiles"], [profile])

        single_profile = {**profile, "query_view_count": 1}

        def single_retrieve(question, k=8, graph_mode="auto", query_views=None):
            passage = evidence()
            passage["retrieval"] = {"profile": dict(single_profile)}
            return [passage]

        _, single_trace = Pipeline(single_retrieve, graph_policy="off").run(
            Question(80, "Consulta directa", "semi_open"))
        self.assertEqual(single_trace["retrieval_profiles"], [single_profile])

    def test_native_option_fusion_is_opt_in_and_keeps_q0_as_retriever_question(self):
        calls = []
        def retrieve(question, k=8, graph_mode="auto", query_views=None):
            calls.append((question, k, graph_mode, query_views))
            return [evidence()]
        q = Question(79, "Constitución Política", "multiple_choice", {"B": "opcion_b", "A": "opcion_a"})
        _, trace = Pipeline(retrieve, graph_policy="off", native_option_fusion=True).run(q)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], trace["query"]["retrieval_text"])
        self.assertEqual(calls[0][3], [f"{calls[0][0]} opcion_a", f"{calls[0][0]} opcion_b"])
        self.assertEqual(trace["locator_control"], "a_query_views_locator_on_q0_only")
        self.assertTrue(trace["native_option_fusion"])

    def test_only_question_text_reaches_retrieval(self):
        q = public_question({"id": 79, "formato": "semi_open", "pregunta": "Artículo 1 de la Ley 1010 de 2006", "legal_basis": "DO_NOT_LEAK", "expected_answer": "DO_NOT_LEAK"})
        retrieve = Mock(side_effect=lambda *args: [evidence()])
        row, trace = Pipeline(retrieve).run(q)
        self.assertNotIn("DO_NOT_LEAK", repr(retrieve.call_args_list) + json.dumps(trace) + json.dumps(row))

    def test_invalid_backend_output_blocks_pipeline(self):
        backend = Mock(); backend.generate.return_value = {"id": 79, "formato": "semi_open"}
        with self.assertRaises(SubmissionValidationError):
            answer(Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open"), [evidence()], "semi_open", decoder=backend)

    def test_decoder_cannot_mutate_evidence_to_create_support(self):
        class BadBackend:
            def generate(self, question, passages, prompt, generation):
                passages[0]["text"] += " Ley 9999 de 2000."
                return cited_row(passages)
        p = evidence(); before = deepcopy(p)
        with self.assertRaises(CitationGuardError):
            answer(Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open"), [p], "semi_open", decoder=BadBackend())
        self.assertEqual(p, before)

    def test_config_rejects_real_decoder_gpu_and_ragas(self):
        for key, value in [("decoder_backend", "Qwen"), ("generation", {"temperature": 1}), ("evaluation", {"split": "sample", "ragas": True})]:
            config = read_json(ROOT / "config/reasoning.json"); config[key] = value
            with self.assertRaises(ValueError): validate_config(config)
        config = read_json(ROOT / "config/reasoning.json"); config["retrieval"]["mode"] = "dense"
        with self.assertRaises(ValueError): validate_config(config)


class EvaluationRegistryTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "tmp/member_b_unit"
        self.root.mkdir(parents=True, exist_ok=True)

    def test_official_evaluator_runs_without_models_and_keeps_file(self):
        questions = load_questions(ROOT / "data/sample_50.jsonl")
        path = self.root / "submissions.jsonl"
        write_jsonl(path, [abstention_row(q, [], "unit_smoke") for q in questions])
        before = path.read_bytes(); report = run_eval(path)
        self.assertEqual(report["validacion"]["errores"], 0)
        self.assertEqual(report["total_automatico"]["obtenidos"], 5.0)
        self.assertIsNone(report["correccion_ragas"]["puntos"])
        self.assertEqual(path.read_bytes(), before)

    def test_eval_rejects_duplicate_ids_and_json_keys(self):
        q = Question(79, "consulta", "semi_open"); row = abstention_row(q, [], "test")
        path = self.root / "duplicate.jsonl"; write_jsonl(path, [row, row])
        with self.assertRaises(ValueError): run_eval(path)
        path.write_text('{"id":79,"id":80}', encoding="utf-8")
        with self.assertRaises(ValueError): run_eval(path)

    def test_failed_run_is_registered_without_final_submission(self):
        # Full source snapshot is only needed for the experiment's identity.
        if not (ROOT / "corpus/manifest.json").exists(): self.skipTest("A snapshot required for registry integration")
        path = self.root / "questions.jsonl"
        write_jsonl(path, [Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open").public_record()])
        class BadBackend:
            name, version = "invalid_unit_probe", "1"
            def generate(self, *args): return {"id": 79, "formato": "semi_open"}
        with patch("kingscode.reasoning.experiments.run_eval") as evaluator:
            with self.assertRaises(RuntimeError):
                run_experiment(output_root=self.root / "failed", questions_path=path, retrieve=lambda *args:[evidence()], decoder=BadBackend())
            evaluator.assert_not_called()
        record = read_json(sorted((self.root / "failed").glob("*/experiment.json"))[-1])
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["metrics"]["schema_rejections"], 1)
        self.assertFalse(Path(record["paths"]["submission"]).exists())

    def test_stable_fingerprint_ignores_mapping_insertion_order(self):
        self.assertEqual(fingerprint({"a": 1, "b": 2}), fingerprint({"b": 2, "a": 1}))

    def test_poisoned_labels_leave_inputs_and_outputs_identical(self):
        if not (ROOT / "corpus/manifest.json").exists(): self.skipTest("A snapshot required for registry integration")
        public = [q.public_record() for q in load_questions(ROOT / "data/sample_50.jsonl")]
        changed = [{**r, "expected_answer": "CANARY", "legal_basis": "CANARY", "respuesta_correcta": "CANARY"} for r in public]
        paths = [self.root / "public.jsonl", self.root / "poisoned.jsonl"]
        results = []
        for path, rows in zip(paths, [public, changed]):
            write_jsonl(path, rows)
            results.append(run_experiment(output_root=self.root / "label_probe", questions_path=path, retrieve=lambda *args:[evidence()]))
        self.assertEqual(results[0]["fingerprint"], results[1]["fingerprint"])
        self.assertEqual(results[0]["submission_sha256"], results[1]["submission_sha256"])
        self.assertNotIn("CANARY", Path(results[1]["paths"]["submission"]).read_text(encoding="utf-8"))


@unittest.skipUnless((ROOT / "corpus/manifest.json").exists(), "A snapshot required for real integration")
class RealRetrievalIntegrationTests(unittest.TestCase):
    def test_adapter_controls_actual_a_retriever_without_changing_internals(self):
        from kingscode import Retriever, retrieve
        self.assertTrue(callable(retrieve))
        adapter = RetrieverGraphRouter()
        retriever = Retriever(graph_router=adapter)
        for decision in ["off", "auto", "on"]:
            adapter.bind("contrato laboral", decision)
            passages = retriever.retrieve("contrato laboral", 3, "auto")
            self.assertTrue(passages)
            self.assertTrue(all(p["retrieval"]["graph_active"] is (decision != "off") for p in passages))


if __name__ == "__main__":
    unittest.main()
