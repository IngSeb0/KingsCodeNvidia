"""B v2: query planner, frozen plan replay, 992 batch robustness, citation builder/repair.

Fixtures are unchanged official passages; decoders/planners are deterministic fakes.
No closed model produces any text here.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from kingscode.common import ROOT, read_json
from kingscode.reasoning import DummyDecoder, Pipeline, Question, citation_guard
from kingscode.reasoning.batch import BatchRunner, atomic_write_text, synthetic_questions, verify_items
from kingscode.reasoning.citation_builder import build_references, render_reference
from kingscode.reasoning.citation_repair import repair_citations, split_sentences
from kingscode.reasoning.contracts import load_questions, public_question
from kingscode.reasoning.evaluation import run_eval
from kingscode.reasoning.guards import CitationGuardError, evidence_record
from kingscode.reasoning.official import citations
from kingscode.reasoning.plan_store import PlanStore, freeze_plans
from kingscode.reasoning.planner import build_planner_messages, plan_from_output

FIXTURES = read_json(ROOT / "tests/fixtures/member_b_official_passages.json")
TMP = ROOT / "tmp/member_b_v2"


def ev(i=1):
    return deepcopy(FIXTURES[i])


def plan_json(facts="", elements="", vocabulary="", **extra):
    base = {"relevant_facts": [], "legal_elements": [], "constraints": [], "requested_information": [],
            "search_queries": {"facts": facts, "elements": elements, "vocabulary": vocabulary}}
    base.update(extra)
    return json.dumps(base, ensure_ascii=False)


class FakePlanner:
    def __init__(self, outputs):
        self.outputs, self.calls, self.messages = outputs, 0, []

    def identity(self):
        return {"model_id": "fake/planner", "model_revision": "0", "tokenizer_revision": "0",
                "generation": {"temperature": 0.0, "do_sample": False, "seed": 0}, "environment": {}}

    def complete(self, messages):
        self.calls += 1
        self.messages.append(messages)
        text = json.loads(messages[-1]["content"])["pregunta"]
        return self.outputs.get(text, plan_json()), {"output_tokens": 1}


class PlannerTests(unittest.TestCase):
    def test_schema_valid_plan_has_at_most_three_views_and_never_q0(self):
        q = "¿Qué pasa si el empleador despide sin justa causa?"
        plan = plan_from_output(1, q, plan_json("despido del trabajador", "terminación unilateral", q))
        self.assertEqual(plan.status, "ok")
        self.assertLessEqual(len(plan.views), 3)
        self.assertEqual(plan.view_roles, ("Q1", "Q2"))  # Q3 identical to Q0 is dropped
        self.assertNotIn(q, plan.views)

    def test_malformed_output_falls_back_to_q0_only(self):
        q = "pregunta"
        for raw in ["no es json", plan_json("a", extra_key="x"), '{"relevant_facts": [], "relevant_facts": []}',
                    plan_json("a", relevant_facts=["x"] * 6), plan_json(elements="b" * 400), "", None]:
            plan = plan_from_output(1, q, raw)
            self.assertEqual((plan.status, plan.views), ("fallback_malformed", ()), msg=str(raw)[:40])
        self.assertEqual(plan_from_output(1, q, "<think>x</think>```json\n" + plan_json("hechos") + "\n```").status, "ok")

    def test_dates_amounts_are_enforced_and_negations_measured(self):
        q = "El trabajador no firmó el contrato el 3 de marzo de 2024 y ganaba 2 salarios mínimos durante 18 meses."
        plan = plan_from_output(1, q, plan_json("trabajador firmó contrato", "contrato realidad"))
        for view in plan.views:
            self.assertIn("3 de marzo de 2024", view)
            self.assertIn("18 meses", view)
        self.assertLess(plan.preservation["rate"], 1.0)
        self.assertIn("no firmó", plan.preservation["lost"])

    def test_generated_reference_is_recorded_as_untrusted(self):
        q = "¿Cuál es el término para contestar la demanda en el proceso verbal?"
        plan = plan_from_output(1, q, plan_json(vocabulary="artículo 369 del Código General del Proceso traslado demanda"))
        self.assertTrue(plan.generated_references)
        own = plan_from_output(1, "artículo 369 del Código General del Proceso", plan_json(vocabulary="artículo 369 del Código General del Proceso traslado"))
        self.assertEqual(own.generated_references, ())

    def test_planner_input_is_question_text_only(self):
        q = public_question({"id": 9, "formato": "semi_open", "pregunta": "texto", "legal_basis": "CANARY",
                             "respuesta_esperada": "CANARY", "opciones": {"A": "CANARY"}})
        self.assertNotIn("CANARY", json.dumps(build_planner_messages(q.text), ensure_ascii=False))
        with self.assertRaises(TypeError):
            build_planner_messages({"pregunta": "x"})


class PlanReplayTests(unittest.TestCase):
    def setUp(self):
        self.root = TMP / "plans"
        shutil.rmtree(self.root, ignore_errors=True)

    def test_freeze_is_resumable_and_replay_is_exact(self):
        items = [(1, "uno"), (2, "dos")]
        backend = FakePlanner({"uno": plan_json("hechos uno")})
        out = freeze_plans(items, backend, root=self.root)
        manifest = read_json(out / "manifest.json")
        for key in ("planner_prompt_version", "planner_prompt_sha256", "question_set_sha256", "backend"):
            self.assertIn(key, manifest["identity"])
        self.assertEqual(backend.calls, 2)
        self.assertEqual(freeze_plans(items, backend, root=self.root), out)
        self.assertEqual(backend.calls, 2)  # nothing regenerated under the same identity
        store = PlanStore(out)
        self.assertEqual(store.get(1, "uno").views, ("hechos uno",))
        with self.assertRaises(ValueError):
            store.get(1, "texto cambiado")
        with self.assertRaises(KeyError):
            store.get(3, "tres")
        (out / "plans.jsonl").write_text((out / "plans.jsonl").read_text(encoding="utf-8").replace("uno", "UNO"), encoding="utf-8")
        with self.assertRaises(ValueError):
            PlanStore(out)


class RetrievalModeTests(unittest.TestCase):
    def _store(self, text, raw):
        root = TMP / "modes"
        shutil.rmtree(root, ignore_errors=True)
        return PlanStore(freeze_plans([(79, text)], FakePlanner({text: raw}), root=root))

    def test_plan_mode_keeps_q0_first_and_denies_locator_to_generated_views(self):
        text = "¿Cuál es el término para contestar la demanda?"
        store = self._store(text, plan_json("demandado notificado", vocabulary="artículo 369 del Código General del Proceso"))
        calls = []

        def retrieve(question, k, graph_mode="off", locator=True):
            calls.append((question, locator))
            return [ev()]
        row, trace = Pipeline(retrieve, retrieval_mode="plan", plans=store, graph_policy="off").run(Question(79, text, "semi_open"))
        self.assertEqual(calls[0], (text, True))
        self.assertTrue(all(loc is False for _, loc in calls[1:]))
        self.assertEqual(len(calls), 3)
        self.assertEqual(trace["locator_control"], "disabled_for_generated_views")
        self.assertTrue(trace["plan"]["generated_references"])

    def test_plan_mode_uses_a_native_query_views_with_q0_as_question(self):
        text = "¿Cuál es el término para contestar la demanda?"
        store = self._store(text, plan_json("demandado notificado", vocabulary="artículo 369 del Código General del Proceso"))
        calls = []

        def retrieve(question, k=8, graph_mode="auto", query_views=None):
            calls.append((question, query_views))
            return [ev()]
        _, trace = Pipeline(retrieve, retrieval_mode="plan", plans=store, graph_policy="off").run(Question(79, text, "semi_open"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], text)  # only Q0 reaches A's locator/router/reranker as the question
        self.assertEqual(calls[0][1], list(store.get(79, text).views))
        self.assertEqual(trace["locator_control"], "a_query_views_locator_on_q0_only")

    def test_retrieve_without_switch_is_reported(self):
        text = "pregunta de prueba"
        store = self._store(text, plan_json("hechos"))
        _, trace = Pipeline(lambda q, k, m: [ev()], retrieval_mode="plan", plans=store, graph_policy="off").run(Question(79, text, "semi_open"))
        self.assertEqual(trace["locator_control"], "retrieve_has_no_locator_switch")

    def test_base_mode_ignores_options_and_plan_option_is_disabled(self):
        calls = []
        Pipeline(lambda q, k, m: calls.append(q) or [ev()], retrieval_mode="base", graph_policy="off").run(
            Question(79, "Ley 1010 de 2006", "multiple_choice", {"A": "x", "B": "y"}))
        self.assertEqual(len(calls), 1)
        for bad in ({"retrieval_mode": "plan_option"}, {"retrieval_mode": "plan"}):
            with self.assertRaises(ValueError):
                Pipeline(lambda *a: [], **bad)

    def test_option_plan_routes_options_to_option_views_and_free_text_to_plan(self):
        text = "¿Cuál es el término para contestar la demanda?"
        store = self._store(text, plan_json("demandado notificado"))
        with self.assertRaises(ValueError):
            Pipeline(lambda *a: [], retrieval_mode="option_plan")
        calls = []

        def retrieve(question, k=8, graph_mode="auto", query_views=None):
            calls.append((question, query_views))
            return [ev()]
        pipe = Pipeline(retrieve, retrieval_mode="option_plan", plans=store, graph_policy="off")
        pipe.run(Question(79, text, "semi_open"))
        self.assertEqual(calls, [(text, list(store.get(79, text).views))])
        calls.clear()
        # Multiple choice never needs (nor reads) a plan: same views as retrieval_mode="option".
        pipe.run(Question(80, "Ley 1010 de 2006", "multiple_choice", {"A": "x", "B": "y"}))
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(views is None for _, views in calls))


class PlannerDiagnosticsTests(unittest.TestCase):
    def test_categories_oracle_fusion_loss_and_unsupported_hypotheses(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        from analyze_query_plans import diagnose

        def p(frag, text="texto"):
            return {"passage_id": frag + ":p", "canonical_fragment_id": frag, "text": text}
        gold = {i: {"fragments": [f"f{i}"], "span_passages": {}} for i in range(4)}
        ranked = [
            {"id": 0, "base": [p("f0")], "plan": [p("f0")], "union": [p("f0")], "generated_references": [], "preservation_rate": 1.0, "plan_status": "ok"},
            {"id": 1, "base": [p("x")], "plan": [p("f1")], "union": [p("f1")], "generated_references": [], "preservation_rate": 0.5, "plan_status": "ok"},
            {"id": 2, "base": [p("f2")], "plan": [p("x")], "union": [p("f2")], "preservation_rate": None, "plan_status": "ok",
             "generated_references": [(("ley", "1010", "2006"), "5")]},
            {"id": 3, "base": [p("x")], "plan": [p("x")], "union": [p("x", "Ley 1010 de 2006")], "preservation_rate": None,
             "plan_status": "fallback_malformed", "generated_references": [(("ley", "1010", "2006"), "5")]},
        ]
        r = diagnose(ranked, gold)
        self.assertEqual(r["categories"], {"BASE_ONLY": 1, "PLAN_ONLY": 1, "BOTH": 1, "NEITHER": 1})
        self.assertEqual((r["oracle_multi_view_recall"], r["planner_miss_rate"], r["fusion_loss"]), (0.75, 0.25, 0.25))
        self.assertEqual(r["unsupported_hypothesis_rate"], 0.5)
        self.assertEqual(r["preservation_rate"], 0.75)


class CitationTests(unittest.TestCase):
    def test_builder_round_trip_on_every_fixture(self):
        mod = citations()
        for passage in FIXTURES:
            ref = render_reference(passage)
            self.assertIsNotNone(ref, passage["passage_id"])
            self.assertTrue(mod.bodies(mod.extract(ref)) & mod.bodies(mod.extract(passage["text"])), ref)
            row = {"id": 1, "formato": "semi_open", "abstencion": False, "respuesta": "Texto sin citas.",
                   "palabras_clave": ["x"], "referencia_legal": ref, "pasajes_recuperados": [evidence_record(passage)]}
            self.assertTrue(citation_guard(row, [passage])["ok"], ref)
        self.assertEqual(len(build_references(FIXTURES, max_refs=3)), 3)
        self.assertEqual(build_references(FIXTURES, used_ids=[FIXTURES[4]["passage_id"]]), [render_reference(FIXTURES[4])])

    def test_three_levels_and_dangerous_abbreviations(self):
        evidence = [ev(0), ev(1)]
        row = {"id": 1, "formato": "semi_open", "abstencion": False, "palabras_clave": ["acoso"],
               "respuesta": ("El artículo 1 de la Ley 1010 de 2006 define el objeto. En el artículo 7 de la Ley 1010 de 2006 hay "
                             "conductas. La Ley 9999 de 2000 lo amplía. Según la C.P. aplica. La CC también."),
               "referencia_legal": "Ley 1010 de 2006", "pasajes_recuperados": [evidence_record(p) for p in evidence]}
        fixed, report = repair_citations(row, evidence)
        actions = [a["action"] for a in report["actions"]]
        self.assertIn("rewritten_to_body", actions)
        self.assertIn("suppressed_sentence", actions)
        self.assertIn("artículo 1 de la Ley 1010 de 2006", fixed["respuesta"])
        self.assertIn("En la Ley 1010 de 2006", fixed["respuesta"])
        for gone in ("9999", "C.P.", "CC"):
            self.assertNotIn(gone, fixed["respuesta"])
        self.assertTrue(citation_guard(fixed, evidence)["ok"])

    def test_constitution_without_year_is_renamed_to_evidence_name(self):
        evidence = [ev(0)]
        row = {"id": 1, "formato": "semi_open", "abstencion": False, "palabras_clave": ["estado"],
               "respuesta": "Según el artículo 1 de la Constitución Política, Colombia es un Estado social de derecho.",
               "referencia_legal": "Constitución Política de Colombia de 1991", "pasajes_recuperados": [evidence_record(evidence[0])]}
        with self.assertRaises(CitationGuardError):
            citation_guard(row, evidence)  # finding for Luis: the guard rejects the undated form
        fixed, _ = repair_citations(row, evidence)
        self.assertIn("artículo 1 de la Constitución Política de Colombia de 1991", fixed["respuesta"])
        self.assertTrue(citation_guard(fixed, evidence)["ok"])

    def test_sentence_split_keeps_citations_whole(self):
        self.assertEqual(len(split_sentences("Ver el Art. 60 del CST. Y el artículo 2.2.1.1 del decreto. Fin.")), 3)


class MixedCitationDecoder:
    """Deterministic fake decoder: good, wrong-article and invented citations mixed."""
    name, version = "unit_mixed_citations", "1"

    def generate(self, question, passages, prompt, generation):
        mixed = ("El artículo 1 de la Ley 1010 de 2006 es pertinente. El artículo 7 de la Ley 1010 de 2006 lo desarrolla. "
                 "La Ley 9999 de 2000 lo amplía. Según la C.P. aplica.")
        row = {"id": question.id, "formato": question.format, "abstencion": False,
               "pasajes_recuperados": [evidence_record(p) for p in passages]}
        if question.format == "multiple_choice":
            letter = sorted(question.options)[0]
            row.update(respuesta_correcta=letter, justificacion="La Ley 8888 de 1999 decide. Ver C.P.",
                       descarte_opciones={k: "La Ley 7777 de 1990 no aplica." for k in sorted(question.options) if k != letter})
        elif question.format == "semi_open":
            row.update(respuesta=mixed, palabras_clave=["acoso laboral", "Ley 5555 de 2001"], referencia_legal="Ley 5555 de 2001")
        else:
            row.update(marco_normativo="El artículo 1 de la Constitución Política y la Ley 1010 de 2006.", analisis=mixed,
                       jurisprudencia="Sentencia C-999 de 2019.", conclusion="Aplica la Ley 1010 de 2006.")
        return row


class OfficialEvaluatorCitationTests(unittest.TestCase):
    def test_fifty_mixed_rows_have_zero_unsupported_rate_and_closed_never_abstain(self):
        questions = load_questions(ROOT / "data/sample_50.jsonl")
        pipeline = Pipeline(lambda *a, **kw: [ev(1), ev(0)], decoder=MixedCitationDecoder(), graph_policy="off")
        rows = []
        for q in questions:
            row, trace = pipeline.run(q)
            self.assertNotIn("citation_guard_fallback", trace)
            if q.format == "multiple_choice":
                self.assertFalse(row["abstencion"])
            rows.append(row)
        path = TMP / "mixed_citations.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
        report = run_eval(path)
        self.assertEqual(report["validacion"]["errores"], 0)
        self.assertEqual(report["citas"]["tasa_sin_respaldo"], 0.0)
        self.assertEqual(report["citas"]["citas_sin_respaldo"], 0)


class FlakyPipeline:
    """Wraps a real Pipeline; fails deterministically on chosen ids."""
    def __init__(self, inner, fail_first=(), fail_always=(), interrupt_at=None):
        self.inner, self.fail_first, self.fail_always, self.interrupt_at = inner, set(fail_first), set(fail_always), interrupt_at
        self.seen = {}

    def run(self, question):
        self.seen[question.id] = self.seen.get(question.id, 0) + 1
        if question.id == self.interrupt_at:
            raise KeyboardInterrupt("simulated crash")
        if question.id in self.fail_always or (question.id in self.fail_first and self.seen[question.id] == 1):
            raise RuntimeError(f"simulated failure {question.id}")
        return self.inner.run(question)


class BatchTests(unittest.TestCase):
    def setUp(self):
        self.root = TMP / "batch"
        shutil.rmtree(self.root, ignore_errors=True)
        self.questions = load_questions(ROOT / "data/sample_50.jsonl")
        self.inner = Pipeline(lambda *a, **kw: [ev(1), ev(0)], decoder=MixedCitationDecoder(), graph_policy="off")

    def run_dir(self, name):
        return self.root / name

    def test_resume_after_crash_is_byte_identical_to_clean_run(self):
        clean = BatchRunner(self.inner, self.run_dir("clean")).run(self.questions)
        crash_id = self.questions[20].id
        with self.assertRaises(KeyboardInterrupt):
            BatchRunner(FlakyPipeline(self.inner, interrupt_at=crash_id), self.run_dir("crash")).run(self.questions)
        self.assertFalse((self.run_dir("crash") / "submissions.jsonl").exists())
        resumed = BatchRunner(self.inner, self.run_dir("crash")).run(self.questions)
        self.assertEqual(resumed["counts"]["resumed"], 20)
        self.assertEqual((self.run_dir("crash") / "submissions.jsonl").read_bytes(),
                         (self.run_dir("clean") / "submissions.jsonl").read_bytes())
        self.assertEqual(resumed["submission_sha256"], clean["submission_sha256"])

    def test_errors_are_isolated_retried_and_fall_back(self):
        ids = [q.id for q in self.questions]
        flaky = FlakyPipeline(self.inner, fail_first=ids[:3], fail_always=ids[3:5])
        report = BatchRunner(flaky, self.run_dir("flaky"), retries=2).run(self.questions)
        self.assertEqual(report["rows"], 50)
        self.assertEqual(report["counts"]["retried_ok"], 3)
        self.assertEqual(sorted(report["fallback_ids"]), sorted(ids[3:5]))
        self.assertEqual(flaky.seen[ids[3]], 3)  # 1 + 2 deterministic retries
        self.assertTrue((self.run_dir("flaky") / "errors" / f"{ids[3]}.json").exists())
        rows = {json.loads(l)["id"]: json.loads(l) for l in (self.run_dir("flaky") / "submissions.jsonl").read_text(encoding="utf-8").splitlines()}
        self.assertTrue(rows[ids[3]]["abstencion"])
        self.assertEqual(run_eval(self.run_dir("flaky") / "submissions.jsonl")["validacion"]["errores"], 0)

    def test_identity_duplicates_and_fresh_are_enforced(self):
        BatchRunner(self.inner, self.run_dir("id"), identity={"decoder": "a"}).run(self.questions)
        with self.assertRaises(ValueError):
            BatchRunner(self.inner, self.run_dir("id"), identity={"decoder": "b"}).run(self.questions)
        with self.assertRaises(FileExistsError):
            BatchRunner(self.inner, self.run_dir("id"), identity={"decoder": "a"}).run(self.questions, resume=False)
        with self.assertRaises(ValueError):
            BatchRunner(self.inner, self.run_dir("dup")).run(self.questions + self.questions[:1])

    def test_atomic_write_never_leaves_a_partial_target(self):
        target = self.root / "atomic.txt"
        with patch("kingscode.reasoning.batch.os.replace", side_effect=OSError("disk")):
            with self.assertRaises(OSError):
                atomic_write_text(target, "x")
        self.assertFalse(target.exists())

    def test_verify_mode_matches_and_detects_divergence(self):
        BatchRunner(self.inner, self.run_dir("verify")).run(self.questions)
        delivered = self.run_dir("verify") / "submissions.jsonl"
        ids = [self.questions[0].id, self.questions[20].id]
        self.assertTrue(verify_items(self.inner, self.questions, delivered, ids)["all_match"])
        other = Pipeline(lambda *a, **kw: [ev(2)], decoder=MixedCitationDecoder(), graph_policy="off")
        self.assertFalse(verify_items(other, self.questions, delivered, ids)["all_match"])

    def test_992_rehearsal_with_dummy_decoder(self):
        questions = synthetic_questions(self.questions, 992)
        self.assertEqual(len({q.id for q in questions}), 992)
        pipeline = Pipeline(lambda *a, **kw: [ev(1), ev(0)], decoder=DummyDecoder(), graph_policy="off")
        report = BatchRunner(pipeline, self.run_dir("992")).run(questions)
        self.assertEqual((report["rows"], report["complete"]), (992, True))
        self.assertLess(report["seconds"], 600)
        print(f"\n[992 rehearsal, fixture retriever, dummy decoder] {report['seconds']:.1f} s")


if __name__ == "__main__":
    unittest.main()
