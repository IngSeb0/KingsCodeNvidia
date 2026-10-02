"""Qwen planner backend: greedy, seeded, locked snapshot, thinking disabled.

Loads through HFDecoder (same model lock, snapshot hash verification, BF16,
deterministic torch settings) and only replaces the final step: it returns the
raw planner text instead of parsing a submission row. Lazy: nothing is imported
or loaded until complete() is first called.
"""
from __future__ import annotations

from time import perf_counter

from ..reasoning.decoder import GENERATION_CONFIG
from .hf_decoder import HFDecoder

PLANNER_MAX_NEW_TOKENS = 384


class QwenPlannerBackend:
    def __init__(self, alias: str = "qwen3-8b", *, precision: str = "bf16", max_new_tokens: int = PLANNER_MAX_NEW_TOKENS,
                 allow_optional: bool = False, torch_module=None, transformers_module=None):
        self.decoder = HFDecoder(alias, precision=precision, allow_optional=allow_optional,
                                 torch_module=torch_module, transformers_module=transformers_module)
        self.max_new_tokens = max_new_tokens

    def identity(self) -> dict:
        d = self.decoder
        env = {}
        if d.torch is not None:
            env["torch"] = getattr(d.torch, "__version__", None)
        if d.transformers is not None:
            env["transformers"] = getattr(d.transformers, "__version__", None)
        return {"model_alias": d.alias, "model_id": d.entry["repo_id"], "model_revision": d.entry["revision"],
                "tokenizer_revision": d.entry["revision"], "precision": d.precision,
                "chat_template_kwargs": dict(d.candidate["chat_template_kwargs"]),
                "generation": {**GENERATION_CONFIG, "max_new_tokens": self.max_new_tokens, "num_beams": 1},
                "environment": env}

    def complete(self, messages: list[dict]) -> tuple[str, dict]:
        d = self.decoder
        d.load()
        started = perf_counter()
        text = d.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True,
                                               **d.candidate["chat_template_kwargs"])
        inputs = d.tokenizer([text], return_tensors="pt", truncation=False, add_special_tokens=False)
        count = int(inputs["input_ids"].shape[-1])
        if count + self.max_new_tokens > d.candidate["max_context_tokens"]:
            return "", {"input_tokens": count, "error": "CONTEXT_LIMIT_EXCEEDED"}
        inputs = inputs.to(d.config["device"])
        # Planner decoding is greedy; sampling-only knobs are intentionally omitted.
        cfg = d.transformers.GenerationConfig(
            do_sample=False, num_beams=1, max_new_tokens=self.max_new_tokens,
            repetition_penalty=1.0, no_repeat_ngram_size=0, use_cache=True,
            eos_token_id=d.model.generation_config.eos_token_id or d.tokenizer.eos_token_id,
            pad_token_id=d.tokenizer.pad_token_id if d.tokenizer.pad_token_id is not None else d.tokenizer.eos_token_id)
        d.torch.manual_seed(GENERATION_CONFIG["seed"])
        with d.torch.inference_mode():
            output = d.model.generate(**inputs, generation_config=cfg)
        tokens = output[0][count:]
        raw = d.tokenizer.decode(tokens, skip_special_tokens=True)
        return raw, {"input_tokens": count, "output_tokens": len(tokens), "generation_ms": (perf_counter() - started) * 1000}

    def close(self):
        self.decoder.close()
