"""Lazy local Transformers decoder implementing the unchanged Decoder Protocol."""
from __future__ import annotations

from copy import deepcopy
import gc
import hashlib
import json
import os
from collections import OrderedDict
from pathlib import Path
from time import perf_counter

from ..common import ROOT
from ..model_assets import resolve_model, verify_snapshot
from ..reasoning.decoder import GENERATION_CONFIG
from .config import PROMPT_VERSION, load_bakeoff, select_decoder
from .prompts import ACTIVE_PROMPT_VERSIONS, LEGACY_PROMPT_VERSIONS, build_messages, parse_response, parse_response_v3, prompt_sha256


ATTN_IMPLEMENTATION = "sdpa"


class DecoderFailure(RuntimeError):
    def __init__(self, code: str, detail: dict):
        self.code, self.detail = code, detail
        super().__init__(code)


FIT_MIN_CHARS = 700  # never shorten a passage below this (article header + its rule)


def _head(text: str, cap: int) -> str:
    """Deterministic head of a passage for the PROMPT only (the official row keeps the full text)."""
    if len(text) <= cap:
        return text
    cut = text.rfind(" ", 0, cap)
    return text[:cut if cut > cap // 2 else cap].rstrip() + " [...]"


class HFDecoder:
    prompt_version = PROMPT_VERSION

    def __init__(self, alias: str, *, config: dict | None = None, precision: str = "bf16",
                 allow_optional: bool = False, torch_module=None, transformers_module=None,
                 prompt_version: str | None = None, constrained_json: bool = False,
                 max_context_tokens: int | None = None, fit_passages: bool = False):
        self.config = deepcopy(config) if config is not None else load_bakeoff()
        if prompt_version is not None:
            if prompt_version not in ACTIVE_PROMPT_VERSIONS:
                raise ValueError(f"prompt_version must be one of {sorted(ACTIVE_PROMPT_VERSIONS)}")
            self.prompt_version = prompt_version
        self.candidate = select_decoder(alias, self.config, allow_optional=allow_optional)
        if max_context_tokens is not None:
            # Opt-in (--max-context): with the 8192 default, 22/50 sample prompts already drop
            # retrieved passages to fit (2026-10-02). The load() check still rejects any value
            # above the locked model's native context; the official row never changes.
            if type(max_context_tokens) is not int or not 8192 <= max_context_tokens <= 32768:
                raise ValueError("max_context_tokens must be an int in [8192, 32768]")
            self.candidate = {**self.candidate, "max_context_tokens": max_context_tokens}
        self.entry = resolve_model(alias)
        if self.entry["revision"] != self.candidate["revision"]:
            raise ValueError("Decoder revision mismatch")
        if precision not in {"bf16", "int8", "int4"}:
            raise ValueError("Unsupported precision; no automatic fallback")
        self.alias, self.precision = alias, precision
        self.constrained_json = bool(constrained_json)
        # Opt-in (--fit-passages): when the evidence does not fit, shorten the longest passages
        # (head kept, marked) before dropping any, so the model sees all retrieved sources.
        self.fit_passages = bool(fit_passages)
        self.name, self.version = "transformers:" + alias, self.entry["revision"]
        self.torch, self.transformers = torch_module, transformers_module
        self.model = self.tokenizer = None
        self.assets = None
        self.last_usage = {}
        self.load_ms = None
        self._grammar_cache = OrderedDict()

    def _system_version(self) -> str:
        # Legacy v1/v2 contracts keep the system text they always had (the v3 one).
        return self.prompt_version if self.prompt_version in ACTIVE_PROMPT_VERSIONS else PROMPT_VERSION

    def _peak(self):
        try:
            if self.torch is not None and self.torch.cuda.is_available():
                return {"peak_vram_bytes": self.torch.cuda.max_memory_allocated(0),
                        "peak_reserved_vram_bytes": self.torch.cuda.max_memory_reserved(0)}
        except Exception as exc:
            return {"peak_vram_bytes": None, "peak_reserved_vram_bytes": None, "memory_error_type": type(exc).__name__}
        return {"peak_vram_bytes": None, "peak_reserved_vram_bytes": None}

    def _failure(self, exc, phase):
        oom_class = getattr(getattr(self.torch, "cuda", None), "OutOfMemoryError", ())
        oom = isinstance(exc, oom_class) if isinstance(oom_class, type) else False
        oom = oom or "out of memory" in str(exc).lower()
        return DecoderFailure("CUDA_OOM" if oom else "DECODER_ERROR", {
            "phase": phase, "error_type": type(exc).__name__, "model": self.alias,
            "revision": self.version, "precision": self.precision,
            "context_limit": self.candidate["max_context_tokens"],
            "usage": deepcopy(self.last_usage), **self._peak()})

    def load(self):
        if self.model is not None:
            return
        start = perf_counter()
        try:
            os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
            if self.torch is None:
                import torch
                self.torch = torch
            if not self.torch.cuda.is_available():
                raise DecoderFailure("CUDA_NOT_AVAILABLE", {"phase": "load", "model": self.alias})
            if not self.torch.cuda.is_bf16_supported():
                raise DecoderFailure("BF16_NOT_SUPPORTED", {"phase": "load", "model": self.alias})
            self.torch.manual_seed(self.config["generation"]["seed"])
            self.torch.use_deterministic_algorithms(True)
            self.torch.backends.cuda.matmul.allow_tf32 = False
            self.torch.backends.cudnn.allow_tf32 = False
            self.torch.cuda.reset_peak_memory_stats(0)
            cache = ROOT / self.config["cache_dir"]
            self.assets = verify_snapshot(self.entry, cache)
            if self.transformers is None:
                import transformers
                self.transformers = transformers
            kwargs = {"revision": self.version, "cache_dir": str(cache), "local_files_only": True, "trust_remote_code": False}
            self.tokenizer = self.transformers.AutoTokenizer.from_pretrained(self.entry["repo_id"], **kwargs)
            if not self.tokenizer.chat_template:
                raise ValueError("Locked tokenizer has no chat template; no template substitution allowed")
            # SDPA, not eager: eager materializes heads x seq x seq attention per layer; with
            # 6-7k evidence tokens on the 4090 that reserved ~46 GB and Windows silently
            # spilled to system RAM (93 s/question). use_deterministic_algorithms(True)
            # above still rejects any nondeterministic kernel instead of changing outputs.
            load_kwargs = {**kwargs, "dtype": self.torch.bfloat16, "device_map": {"": 0},
                           "attn_implementation": ATTN_IMPLEMENTATION, "use_safetensors": True}
            if self.precision != "bf16":
                load_kwargs["quantization_config"] = self.transformers.BitsAndBytesConfig(
                    load_in_8bit=self.precision == "int8", load_in_4bit=self.precision == "int4",
                    bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=self.torch.bfloat16)
            self.model = self.transformers.AutoModelForCausalLM.from_pretrained(self.entry["repo_id"], **load_kwargs).eval()
            if self.model.config.max_position_embeddings < self.candidate["max_context_tokens"]:
                raise ValueError("Configured context exceeds the locked model's native context")
            self.torch.cuda.synchronize()
            self.load_ms = (perf_counter() - start) * 1000
        except DecoderFailure:
            raise
        except Exception as exc:
            raise self._failure(exc, "load") from exc

    def generate(self, question, passages, prompt, generation):
        if generation != GENERATION_CONFIG or self.config["generation"] != GENERATION_CONFIG:
            raise ValueError("Non-deterministic generation rejected")
        max_used = self.config.get("max_used_passages", 5)
        self.last_usage = {"input_tokens": 0, "output_tokens": 0, "json_valid": False, "model": self.alias,
                           "revision": self.version, "prompt_version": self.prompt_version,
                           "prompt_sha256": prompt_sha256(max_used, self._system_version()),
                           "max_new_tokens": self.config["max_new_tokens"][question.format],
                           "sampling_policy": {"strategy": "greedy", "do_sample": False,
                                               "temperature": generation["temperature"], "seed": generation["seed"]},
                           "constrained_json": self.constrained_json}
        self.load()
        started = perf_counter()
        try:
            budget = self.last_usage["max_new_tokens"]
            # Fit the evidence to the context: drop the lowest-ranked passages from the
            # prompt only (never truncate text, never reorder). The official row still
            # carries every retrieved passage in pasajes_recuperados.
            shown = list(passages)
            cap, trimmed = None, 0
            while True:
                view = shown if cap is None else [dict(p, text=_head(p.get("text") or "", cap)) for p in shown]
                messages = build_messages(question, view, prompt, max_used=max_used, version=self._system_version())
                text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                                          **self.candidate["chat_template_kwargs"])
                inputs = self.tokenizer([text], return_tensors="pt", truncation=False, add_special_tokens=False)
                count = int(inputs["input_ids"].shape[-1])
                if count + budget <= self.candidate["max_context_tokens"] or len(shown) <= 1:
                    break
                longest = max(len(p.get("text") or "") for p in shown)
                if self.fit_passages and (cap or longest) > FIT_MIN_CHARS:
                    # Shrink the longest texts first: one cap for all passages, lowered 15% per step.
                    cap = max(FIT_MIN_CHARS, int((cap or longest) * 0.85))
                    trimmed = sum(len(p.get("text") or "") > cap for p in shown)
                    continue
                cap, trimmed = None, 0
                shown = shown[:-1]
            self.last_usage.update(input_tokens=count, attn_implementation=ATTN_IMPLEMENTATION,
                                   evidence_in_prompt=len(shown), evidence_trimmed_to_chars=cap,
                                   evidence_passages_trimmed=trimmed,
                                   evidence_dropped_for_context=[p.get("passage_id") for p in passages[len(shown):]])
            if count + budget > self.candidate["max_context_tokens"]:
                raise DecoderFailure("CONTEXT_LIMIT_EXCEEDED", {"usage": dict(self.last_usage),
                                      "context_limit": self.candidate["max_context_tokens"]})
            inputs = inputs.to(self.config["device"])
            # Use shared generation settings, not model-specific sampling or
            # repetition defaults. Only native stopping/special-token IDs vary.
            # Greedy decoding is controlled by do_sample=False and num_beams=1.
            # Temperature/top_k do not apply in this mode; passing non-default values
            # makes Transformers warn that they are ignored and misstates runtime telemetry.
            cfg = self.transformers.GenerationConfig(
                do_sample=False, num_beams=1,
                max_new_tokens=budget, repetition_penalty=1.0, no_repeat_ngram_size=0,
                use_cache=True,
                bos_token_id=getattr(self.model.generation_config, "bos_token_id", None),
                eos_token_id=self.model.generation_config.eos_token_id or self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id)
            self.last_usage["effective_generation_config"] = {
                key: getattr(cfg, key) for key in ("do_sample", "num_beams",
                                                  "max_new_tokens", "repetition_penalty", "no_repeat_ngram_size",
                                                  "bos_token_id", "eos_token_id", "pad_token_id")}
            self.torch.manual_seed(generation["seed"])
            generate_kwargs = {}
            if self.constrained_json:
                processor, grammar_identity, xgrammar_version = self._json_logits_processor(question, shown, max_used)
                generate_kwargs["logits_processor"] = [processor]
                self.last_usage.update(json_grammar="xgrammar_json_schema_v1",
                                       json_grammar_sha256=grammar_identity,
                                       xgrammar_version=xgrammar_version)
            with self.torch.inference_mode():
                output = self.model.generate(**inputs, generation_config=cfg, **generate_kwargs)
            self.torch.cuda.synchronize()
            tokens = output[0][count:]
            raw = self.tokenizer.decode(tokens, skip_special_tokens=True)
            self.last_usage.update(output_tokens=len(tokens), raw_response=raw,
                                   generation_ms=(perf_counter() - started) * 1000, **self._peak())
            try:
                if self.prompt_version in LEGACY_PROMPT_VERSIONS:
                    row = parse_response(raw, question, passages)
                else:
                    # v4+: a single JSON object wrapped in prose is extracted (v3 stays strict).
                    row, meta = parse_response_v3(raw, question, passages, max_used=max_used,
                                                  extract_embedded=self.prompt_version not in {PROMPT_VERSION})
                    self.last_usage.update(meta)
            except (ValueError, TypeError) as exc:
                raise DecoderFailure("INVALID_MODEL_OUTPUT", {"error_type": type(exc).__name__, "reason": str(exc)[:200],
                                                              "usage": dict(self.last_usage)}) from exc
            self.last_usage["json_valid"] = True
            # Caller (the original answer/Pipeline) must run citation_guard again.
            return row
        except DecoderFailure:
            raise
        except Exception as exc:
            raise self._failure(exc, "generate") from exc

    def _json_logits_processor(self, question, passages, max_used):
        try:
            import xgrammar as xgr
        except ImportError as exc:
            raise RuntimeError("XGrammar is optional; install requirements-gpu-experiments.txt") from exc
        from .structured_json import response_schema
        schema = response_schema(question.format, question.options,
                                 [p.get("passage_id", "") for p in passages], max_used)
        schema_text = json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        identity = hashlib.sha256(schema_text.encode("utf-8")).hexdigest()
        if identity not in self._grammar_cache:
            vocab_size = getattr(self.model.config, "vocab_size", None)
            tokenizer_info = xgr.TokenizerInfo.from_huggingface(self.tokenizer, vocab_size=vocab_size)
            compiler = xgr.GrammarCompiler(tokenizer_info)
            grammar = compiler.compile_json_schema(schema_text)
            self._grammar_cache[identity] = grammar
            if len(self._grammar_cache) > 8:
                self._grammar_cache.popitem(last=False)
        else:
            self._grammar_cache.move_to_end(identity)
        # XGrammar's HF LogitsProcessor is stateful and single-use: create a new
        # processor for each generate() call while reusing the compiled grammar.
        processor = xgr.contrib.hf.LogitsProcessor(self._grammar_cache[identity])
        return processor, identity, getattr(xgr, "__version__", "unknown")

    def close(self):
        self.model = self.tokenizer = None
        gc.collect()
        if self.torch is not None and self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()
