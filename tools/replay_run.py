"""Replay B's full post-processing on a saved run, without GPU or decoder.

    python tools/replay_run.py <run>/batch                                 # same settings as the run
    python tools/replay_run.py <run>/batch --cite-mentions 3 --citation-fill --prompt-version v4

For every item with a stored raw model output (diagnostics.raw_response, runs from 2026-10-01
on), feeds that exact text through the real v3/v4 parser, citation repair, citation builder and
citation guard over the SAME stored evidence, writes submissions.jsonl and runs the official
evaluator (no RAGAS). Items without raw output (fallbacks of older runs) keep their stored row.

What it measures: any change in parsing, repair, citations, abstention policy or guard.
What it cannot measure: prompt, retrieval or decoder changes (those need a GPU run).
With the run's own settings it must reproduce the run's submission (checked and reported).
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT  # noqa: E402
from kingscode.generation.prompts import PROMPT_V4, parse_response_v3  # noqa: E402
from kingscode.reasoning.contracts import Question  # noqa: E402
from kingscode.reasoning.pipeline import _answer  # noqa: E402


class ReplayDecoder:
    """Returns the stored raw output through the real parser, like HFDecoder does."""
    name = "replay"

    def __init__(self, raw: str, prompt_version: str, base_usage: dict):
        self.raw, self.prompt_version, self.base = raw, prompt_version, base_usage
        self.version = base_usage.get("revision")
        self.last_usage = {}

    def generate(self, question, passages, prompt, generation):
        row, meta = parse_response_v3(self.raw, question, passages,
                                      extract_embedded=self.prompt_version != "grounded-formats-v3")
        self.last_usage = {**self.base, **meta, "prompt_version": self.prompt_version}
        return row


def _passages(row: dict) -> list[dict]:
    out = []
    for record in row["pasajes_recuperados"]:
        p = deepcopy(record)
        p["text"] = p.pop("texto")
        out.append(p)
    return out


def replay(batch: Path, questions_path: Path, prompt_version: str | None, citation_fill: bool | None,
           cite_mentions: int | None, max_refs: int | None = None) -> tuple[list[dict], dict]:
    identity = json.loads((batch / "identity.json").read_text(encoding="utf-8"))
    pv = prompt_version or identity.get("prompt_version") or "grounded-formats-v3"
    pv = PROMPT_V4 if pv in {"v4", PROMPT_V4} else pv if pv.startswith("grounded") else f"grounded-formats-{pv}"
    fill = identity.get("citation_fill", False) if citation_fill is None else citation_fill
    mentions = identity.get("cite_mentions", 0) if cite_mentions is None else cite_mentions
    questions = {}
    for line in questions_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            questions[q["id"]] = Question(q["id"], q["pregunta"], q["formato"], q.get("opciones") or {})
    rows, stats = [], {"replayed": 0, "kept_stored": 0, "identical_to_stored": 0, "errors": 0,
                       "settings": {"prompt_version": pv, "citation_fill": fill, "cite_mentions": mentions}}
    for item_path in sorted((batch / "items").glob("*.json"), key=lambda p: int(p.stem)):
        item = json.loads(item_path.read_text(encoding="utf-8"))
        stored = item["row"]
        d = (item.get("trace") or {}).get("diagnostics") or {}
        raw = d.get("raw_response")
        passages = _passages(stored)
        if not raw or not passages:
            rows.append(stored)
            stats["kept_stored"] += 1
            continue
        decoder = ReplayDecoder(raw, pv, {k: d.get(k) for k in ("model", "revision", "input_tokens", "output_tokens")})
        try:
            row, _ = _answer(questions[stored["id"]], passages, decoder, max_refs=max_refs or (5 if fill else 3),
                             citation_fill=fill, cite_mentions=mentions)
        except Exception as exc:  # parser/guard failure -> same fallback the batch would write
            stats["errors"] += 1
            row = stored
            stats.setdefault("error_ids", []).append([stored["id"], type(exc).__name__])
        stats["replayed"] += 1
        stats["identical_to_stored"] += json.dumps(row, sort_keys=True, ensure_ascii=False) == \
            json.dumps(stored, sort_keys=True, ensure_ascii=False)
        rows.append(row)
    return rows, stats


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("batch", type=Path)
    parser.add_argument("--questions", type=Path, default=ROOT / "data/sample_50.jsonl")
    parser.add_argument("--prompt-version", help="v3/v4 (default: the run's)")
    parser.add_argument("--citation-fill", dest="citation_fill", action="store_true", default=None)
    parser.add_argument("--no-citation-fill", dest="citation_fill", action="store_false")
    parser.add_argument("--cite-mentions", type=int)
    parser.add_argument("--max-refs", type=int, help="citations kept per row (default: 5 with fill, else 3)")
    parser.add_argument("--name", default="replay")
    parser.add_argument("--split", default="sample")
    args = parser.parse_args(argv)
    rows, stats = replay(args.batch, args.questions, args.prompt_version, args.citation_fill, args.cite_mentions, args.max_refs)
    out = args.batch.parent / args.name
    out.mkdir(parents=True, exist_ok=True)
    sub = out / "submissions.jsonl"
    with sub.open("w", encoding="utf-8", newline="\n") as stream:
        for r in rows:
            stream.write(json.dumps(r, ensure_ascii=False) + "\n")
    ev = out / "evaluation_official.json"
    subprocess.run([sys.executable, str(ROOT / "scripts/evaluate.py"), "--submission", str(sub), "--split", args.split,
                    "--out", str(ev)], check=True, capture_output=True, text=True, encoding="utf-8")
    e = json.loads(ev.read_text(encoding="utf-8"))
    print(json.dumps({**stats, "total_sin_ragas": e["total_automatico"]["obtenidos"], "cerradas": e["cerradas"]["puntos"],
                      "citas": e["citas"]["puntos"], "recall": e["citas"]["recall_citas_ponderado"],
                      "sin_respaldo": e["citas"]["tasa_sin_respaldo"], "abstencion": e["abstencion"]["puntos"],
                      "submission_sha256": hashlib.sha256(sub.read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
