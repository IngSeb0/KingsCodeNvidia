"""Prepared CPU-only mocks. Do not download weights or run real CUDA operations."""
from __future__ import annotations

from contextlib import nullcontext, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from kingscode.common import ROOT, read_json, write_json
from kingscode.generation.config import load_bakeoff, select_decoder
from kingscode.generation.experiments import validate_fallback
from kingscode.generation.hf_decoder import DecoderFailure, HFDecoder
from kingscode.generation.prompts import build_messages, parse_response, sentence_count
from kingscode.gpu_environment import diagnose, environment_plan
from kingscode.model_assets import digest_file, prepare_snapshot, resolve_model, snapshot_path, verify_snapshot
from kingscode.reasoning.contracts import Question
from kingscode.reasoning.decoder import DummyDecoder, GENERATION_CONFIG, PromptSpec, abstention_row
from kingscode.reasoning.guards import citation_guard


class FakeOOM(RuntimeError):
    pass


def fake_torch(available=True):
    cuda = SimpleNamespace(is_available=lambda: available, is_bf16_supported=lambda: True,
                           reset_peak_memory_stats=Mock(), max_memory_allocated=lambda *a: 123,
                           max_memory_reserved=lambda *a: 456, synchronize=Mock(), empty_cache=Mock(),
                           OutOfMemoryError=FakeOOM)
    return SimpleNamespace(cuda=cuda, __version__="unit-mock", version=SimpleNamespace(cuda=None), bfloat16="mock_bf16",
                           manual_seed=Mock(), use_deterministic_algorithms=Mock(), inference_mode=nullcontext,
                           backends=SimpleNamespace(cuda=SimpleNamespace(matmul=SimpleNamespace(allow_tf32=True)),
                                                    cudnn=SimpleNamespace(allow_tf32=True)))


class FakeInputs(dict):
    def __init__(self, count=12):
        super().__init__(input_ids=SimpleNamespace(shape=(1, count)))

    def to(self, device):
        return self


class FakeTokenizer:
    chat_template = "locked mock template"
    pad_token_id, eos_token_id = 0, 3

    def __init__(self, response='{"abstencion":true}', count=12):
        self.response, self.count = response, count
        self.template_kwargs = None

    def apply_chat_template(self, messages, **kwargs):
        self.template_kwargs = kwargs
        return json.dumps(messages)

    def __call__(self, text, **kwargs):
        return FakeInputs(self.count)

    def decode(self, tokens, **kwargs):
        return self.response


def fake_transformers(tokenizer=None):
    model = SimpleNamespace(config=SimpleNamespace(max_position_embeddings=8192),
                            generation_config=SimpleNamespace(eos_token_id=3),
                            generate=Mock(return_value=[list(range(12)) + [1, 2, 3]]))
    model.eval = lambda: model
    module = SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=Mock(return_value=tokenizer or FakeTokenizer())),
                             AutoModelForCausalLM=SimpleNamespace(from_pretrained=Mock(return_value=model)),
                             BitsAndBytesConfig=Mock(), GenerationConfig=lambda **kwargs: SimpleNamespace(**kwargs))
    return module, model


class PrepCase(unittest.TestCase):
    def setUp(self):
        self.temp = ROOT / "tmp/gate2_unit" / uuid4().hex
        self.temp.mkdir(parents=True)
        self.evidence = read_json(ROOT / "tests/fixtures/member_b_official_passages.json")[1]
        self.question = Question(79, "Artículo 1 de la Ley 1010 de 2006", "semi_open")


class LockConfigurationTests(PrepCase):
    def test_all_requested_revisions_are_immutable(self):
        for alias in load_bakeoff()["candidates"]:
            self.assertRegex(resolve_model(alias)["revision"], r"^[0-9a-f]{40}$")

    def test_existing_retrieval_locks_are_preserved(self):
        original = json.loads(subprocess.check_output(["git", "show", "254fa3a:config/models.lock.json"], cwd=ROOT))
        current = read_json(ROOT / "config/models.lock.json")
        for name, entry in original.items():
            self.assertEqual(current[name], entry)

    def test_missing_revision_is_an_error(self):
        path = self.temp / "lock.json"
        entry = resolve_model("qwen3-8b"); entry.pop("revision")
        write_json(path, {entry["repo_id"]: entry})
        with self.assertRaises(ValueError): resolve_model("qwen3-8b", path)

    def test_unknown_or_closed_model_rejected(self):
        with self.assertRaises(ValueError): resolve_model("closed-provider/model")

    def test_config_cannot_override_locked_revision(self):
        cfg = load_bakeoff(); cfg["candidates"]["qwen3-8b"]["revision"] = "0" * 40
        path = self.temp / "config.json"; write_json(path, cfg)
        with self.assertRaises(ValueError): load_bakeoff(path)

    def test_config_forbids_remote_code_sampling_and_online_inference(self):
        for key, value in [("trust_remote_code", True), ("local_files_only", False), ("batch_size", 2)]:
            cfg = load_bakeoff(); cfg["candidates"]["qwen3-8b"][key] = value
            path = self.temp / "config.json"; write_json(path, cfg)
            with self.assertRaises(ValueError): load_bakeoff(path)

    def test_optional_control_requires_explicit_selection(self):
        cfg = load_bakeoff()
        with self.assertRaises(ValueError): select_decoder("llama31-8b", cfg)
        self.assertFalse(select_decoder("llama31-8b", cfg, allow_optional=True)["enabled"])

    def test_gated_access_is_not_assumed(self):
        self.assertEqual(resolve_model("salamandra-7b")["gated"], "manual")
        self.assertEqual(resolve_model("llama31-8b")["gated"], "manual")


class PromptAndDecoderTests(PrepCase):
    def decoder(self, response='{"abstencion":true}', *, available=True, count=12):
        tokenizer = FakeTokenizer(response, count)
        transformers, model = fake_transformers(tokenizer)
        decoder = HFDecoder("qwen3-8b", torch_module=fake_torch(available), transformers_module=transformers)
        return decoder, transformers, model, tokenizer

    def test_import_is_lazy_in_fresh_process(self):
        code = "import sys; import kingscode.generation.hf_decoder; assert 'torch' not in sys.modules; assert 'transformers' not in sys.modules"
        subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)

    def test_prompt_per_format_contains_only_public_inputs(self):
        for fmt, marker in [("multiple_choice", "descarte_opciones"), ("semi_open", "150"), ("open_ended", "5 a 8")]:
            q = Question(1, "consulta", fmt, {"A": "opción"})
            messages = build_messages(q, [self.evidence], PromptSpec(fmt))
            self.assertIn(marker, messages[0]["content"])
            self.assertIn("No uses conocimiento paramétrico", messages[0]["content"])
            self.assertEqual(set(json.loads(messages[1]["content"])), {"pregunta", "opciones", "evidencia"})

    def test_mock_generation_keeps_revision_and_greedy_settings(self):
        decoder, transformers, model, tokenizer = self.decoder()
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={"verified": True}):
            row = decoder.generate(self.question, [self.evidence], PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertTrue(row["abstencion"])
        self.assertTrue(citation_guard(row, [self.evidence])["ok"])
        kwargs = transformers.AutoModelForCausalLM.from_pretrained.call_args.kwargs
        self.assertEqual(kwargs["revision"], resolve_model("qwen3-8b")["revision"])
        self.assertIs(kwargs["local_files_only"], True)
        self.assertIs(kwargs["trust_remote_code"], False)
        generation = model.generate.call_args.kwargs["generation_config"]
        self.assertFalse(generation.do_sample)
        self.assertEqual(generation.num_beams, 1)
        self.assertFalse(hasattr(generation, "temperature"))
        self.assertFalse(hasattr(generation, "top_k"))
        self.assertEqual(decoder.last_usage["sampling_policy"],
                         {"strategy": "greedy", "do_sample": False, "temperature": 0.0, "seed": 0})
        self.assertNotIn("temperature", decoder.last_usage["effective_generation_config"])
        self.assertNotIn("top_k", decoder.last_usage["effective_generation_config"])
        self.assertFalse(tokenizer.template_kwargs["enable_thinking"])
        self.assertEqual(decoder.last_usage["input_tokens"], 12)

    def test_valid_json_citation_passes_existing_guard(self):
        q = Question(1, self.question.text, "multiple_choice", {"A": "Uno", "B": "Dos"})
        raw = json.dumps({"abstencion": False, "respuesta_correcta": "A", "justificacion": "Artículo 1 de la Ley 1010 de 2006.",
                          "descarte_opciones": {"B": "No sustentada en la evidencia."}})
        row = parse_response(raw, q, [self.evidence])
        self.assertTrue(citation_guard(row, [self.evidence])["ok"])

    def test_invalid_json_is_never_repaired(self):
        for raw in ['```json\n{"abstencion":true}\n```', '{"abstencion":true} texto', '{"abstencion":true,"abstencion":false}', '{"abstencion":NaN}']:
            with self.assertRaises(ValueError): parse_response(raw, self.question, [self.evidence])

    def test_model_cannot_supply_evidence_or_identity(self):
        with self.assertRaises(ValueError):
            parse_response('{"abstencion":true,"pasajes_recuperados":[]}', self.question, [self.evidence])

    def test_format_length_rejected_instead_of_truncated(self):
        raw = json.dumps({"abstencion": False, "respuesta": "Una sola oración.", "palabras_clave": ["objeto"],
                          "referencia_legal": "Artículo 1 de la Ley 1010 de 2006"})
        with self.assertRaises(ValueError): parse_response(raw, self.question, [self.evidence])
        self.assertEqual(sentence_count("Art. 1.2 conserva el número. Otra oración. Tercera oración."), 3)

    def test_cuda_unavailable_stops_before_model_loading(self):
        decoder, transformers, _, _ = self.decoder(available=False)
        with self.assertRaises(DecoderFailure) as caught:
            decoder.generate(self.question, [self.evidence], PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertEqual(caught.exception.code, "CUDA_NOT_AVAILABLE")
        transformers.AutoModelForCausalLM.from_pretrained.assert_not_called()

    def test_oom_has_no_silent_fallback(self):
        decoder, transformers, _, _ = self.decoder()
        transformers.AutoModelForCausalLM.from_pretrained.side_effect = FakeOOM("simulated out of memory")
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={}), self.assertRaises(DecoderFailure) as caught:
            decoder.generate(self.question, [self.evidence], PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertEqual(caught.exception.code, "CUDA_OOM")
        self.assertEqual(caught.exception.detail["context_limit"], 8192)
        self.assertEqual(transformers.AutoModelForCausalLM.from_pretrained.call_count, 1)
        transformers.BitsAndBytesConfig.assert_not_called()

    def test_context_limit_aborts_without_generation(self):
        decoder, _, model, _ = self.decoder(count=8192)
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={}), self.assertRaises(DecoderFailure) as caught:
            decoder.generate(self.question, [self.evidence], PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertEqual(caught.exception.code, "CONTEXT_LIMIT_EXCEEDED")
        model.generate.assert_not_called()

    def test_bad_model_output_is_a_registered_failure_type(self):
        decoder, _, _, _ = self.decoder(response="not JSON")
        with patch("kingscode.generation.hf_decoder.verify_snapshot", return_value={}), self.assertRaises(DecoderFailure) as caught:
            decoder.generate(self.question, [self.evidence], PromptSpec("semi_open"), dict(GENERATION_CONFIG))
        self.assertEqual(caught.exception.code, "INVALID_MODEL_OUTPUT")
        self.assertEqual(decoder.last_usage["raw_response"], "not JSON")

    def test_dummy_is_functionally_identical_for_every_format(self):
        for fmt in ("multiple_choice", "semi_open", "open_ended"):
            q = Question(1, "consulta", fmt)
            row = DummyDecoder().generate(q, [self.evidence], PromptSpec(fmt), dict(GENERATION_CONFIG))
            self.assertEqual(row, abstention_row(q, [self.evidence], "dummy_backend_no_legal_reasoning"))


class AssetsEnvironmentCliTests(PrepCase):
    def test_download_uses_exact_revision_and_checks_hashes(self):
        entry = resolve_model("qwen3-8b")
        snapshot = snapshot_path(entry, self.temp); snapshot.mkdir(parents=True)
        siblings = []
        for name in ["config.json", "tokenizer_config.json", "tokenizer.json", "model.safetensors"]:
            p = snapshot / name; p.write_bytes(b"{}")
            siblings.append(SimpleNamespace(rfilename=name, lfs=None, blob_id=digest_file(p, git_blob=True)))
        api = SimpleNamespace(model_info=Mock(return_value=SimpleNamespace(sha=entry["revision"], siblings=siblings)))
        downloader = Mock(return_value=str(snapshot))
        result = prepare_snapshot(entry, self.temp, api=api, download=downloader)
        self.assertEqual(result["files_verified"], 4)
        self.assertEqual(downloader.call_args.kwargs["revision"], entry["revision"])
        (snapshot / "model.safetensors").write_bytes(b"tampered")
        with self.assertRaises(ValueError): verify_snapshot(entry, self.temp)

    def test_download_rejects_wrong_hub_revision(self):
        api = SimpleNamespace(model_info=Mock(return_value=SimpleNamespace(sha="0" * 40)))
        downloader = Mock()
        with self.assertRaises(ValueError): prepare_snapshot(resolve_model("qwen3-8b"), self.temp, api=api, download=downloader)
        downloader.assert_not_called()

    def test_unprepared_cache_fails_offline(self):
        with self.assertRaises(FileNotFoundError): verify_snapshot(resolve_model("qwen3-8b"), self.temp)

    def test_plan_never_guesses_cuda_or_installs(self):
        report = diagnose(torch_module=fake_torch(False), which=lambda name: None)
        plan = environment_plan(report)
        self.assertIsNone(plan["install_argv"])
        self.assertFalse(plan["gpu_validated"])
        with self.assertRaises(ValueError): environment_plan(report, torch_version="1.2.3", cuda_tag="cu999")

    def test_smoke_without_cuda_records_clear_failure(self):
        from kingscode.generation.gpu_smoke import run_gpu_smoke
        result = run_gpu_smoke(output_root=self.temp, torch_module=fake_torch(False))
        self.assertEqual(result["error"]["code"], "CUDA_NOT_AVAILABLE")
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["project_state_modified"])

    def test_quantization_requires_matching_oom_record(self):
        with self.assertRaises(ValueError): validate_fallback("int4", None, {"context": 8192})
        path = self.temp / "oom.json"
        write_json(path, {"status": "failed", "precision": "bf16", "error": {"code": "CUDA_OOM"}, "comparison": {"context": 8192}})
        validate_fallback("int8", path, {"context": 8192})
        with self.assertRaises(ValueError): validate_fallback("int8", path, {"context": 4096})

    def test_cli_dry_run_selection_never_loads_a_model(self):
        from tools.member_b import main
        with patch("kingscode.generation.hf_decoder.HFDecoder.load") as load:
            for command in [["decoder-smoke", "--model", "qwen3-8b", "--dry-run"],
                            ["sample", "--model", "alia-legal-7b", "--dry-run"], ["bakeoff", "--dry-run"]]:
                with redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(main(command), 0)
                self.assertEqual(json.loads(output.getvalue())["status"], "prepared_not_executed")
            load.assert_not_called()

    def test_old_smoke_cli_still_calls_only_old_runner(self):
        from tools.member_b import main
        result = {"status": "passed", "fingerprint": "same", "paths": {}, "submission_sha256": "same",
                  "metrics": {}, "official_evaluation": {"total_automatico": {}}, "neural_modules_loaded": []}
        with patch("tools.member_b.run_experiment", return_value=result) as run, redirect_stdout(io.StringIO()):
            self.assertEqual(main(["smoke"]), 0)
        self.assertEqual(run.call_args.kwargs["config_path"], ROOT / "config/reasoning.json")


if __name__ == "__main__":
    unittest.main()
