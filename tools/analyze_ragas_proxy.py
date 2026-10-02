"""Free, local proxy of the RAGAS free-text component (no OpenRouter, no credit).

    python tools/analyze_ragas_proxy.py <run>/batch/submissions.jsonl [<other>.jsonl ...]

Official RAGAS answer_correctness = LLM factual agreement (judge, paid) + semantic similarity
computed by a LOCAL open encoder (intfloat/multilingual-e5-large). This tool reproduces the
free part exactly as the evaluator builds it (same text per format, same reference, abstention
= 0, denominator = all judged items) and adds lexical overlap (token-F1 = ROUGE-1, BLEU-4; the
organizers' baseline is also compared with BERTScore/BLEU/ROUGE-1) and Spanish readability
(Fernández-Huerta) of our answers versus the references.

Use it to RANK variants between GPU runs; spend the real --ragas only on the final candidate.
Calibration point (2026-10-02): run qwen3-8b_bm25_..._20261002_111603 -> official RAGAS 0.4275.
Reads respuesta_esperada from data/sample_50.jsonl for measurement only (allowed for analyze_*).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
ENCODER = "intfloat/multilingual-e5-large"


def ragas_text(sub: dict) -> str:  # identical to scripts/evaluate.py::ragas_text
    if sub.get("formato") == "semi_open":
        return str(sub.get("respuesta") or "")
    return " ".join(str(sub.get(k) or "") for k in ("marco_normativo", "analisis", "jurisprudencia", "conclusion"))


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-záéíóúñü0-9]+", text.lower()) if len(t) > 2]


def token_f1(answer: str, truth: str) -> float:
    a, t = _tokens(answer), _tokens(truth)
    if not a or not t:
        return 0.0
    common = sum(min(a.count(w), t.count(w)) for w in set(a))
    if not common:
        return 0.0
    p, r = common / len(a), common / len(t)
    return 2 * p * r / (p + r)


def bleu(answer: str, truth: str, n_max: int = 4) -> float:
    """Sentence BLEU-4 with add-one smoothing on orders > 1 (lexical overlap, as in the
    organizers' baseline comparison). Deterministic, no external package."""
    import math
    a, t = _tokens(answer), _tokens(truth)
    if not a or not t:
        return 0.0
    logs = []
    for n in range(1, n_max + 1):
        grams_a = [tuple(a[i:i + n]) for i in range(len(a) - n + 1)]
        ref = {}
        for g in (tuple(t[i:i + n]) for i in range(len(t) - n + 1)):
            ref[g] = ref.get(g, 0) + 1
        hit = 0
        for g in grams_a:
            if ref.get(g, 0) > 0:
                hit += 1
                ref[g] -= 1
        smooth = 1 if n > 1 else 0
        if not grams_a or hit + smooth == 0:
            return 0.0
        logs.append(math.log((hit + smooth) / (len(grams_a) + smooth)))
    bp = 1.0 if len(a) > len(t) else math.exp(1 - len(t) / len(a))
    return bp * math.exp(sum(logs) / n_max)


def _syllables(word: str) -> int:
    return max(1, len(re.findall(r"[aeiouáéíóúü]+", word)))


def fernandez_huerta(text: str) -> float | None:
    """Spanish readability (Fernández-Huerta; ~60-70 standard, < 50 difficult/university level)."""
    words = re.findall(r"[a-záéíóúñü]+", text.lower())
    if not words:
        return None
    sentences = max(1, len([s for s in re.split(r"[.!?;]+", text) if s.strip()]))
    return round(206.84 - 60 * sum(map(_syllables, words)) / len(words) - 102 * sentences / len(words), 1)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("submissions", type=Path, nargs="+")
    parser.add_argument("--no-encoder", action="store_true", help="token-F1 only (no model download)")
    args = parser.parse_args(argv)
    key = {}
    for line in (ROOT / "data/sample_50.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            if r["formato"] != "multiple_choice":
                key[int(r["id"])] = r
    model = None
    if not args.no_encoder:
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(ENCODER)
        except Exception as exc:  # missing package/model: degrade visibly
            print(f"[proxy] encoder unavailable ({type(exc).__name__}); token-F1 only", file=sys.stderr)
    for path in args.submissions:
        subs = {int(json.loads(l)["id"]): json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()}
        sims, f1s, bleus, answered = [], [], [], 0
        readability, ref_readability = [], []
        pairs = []
        for qid, k in key.items():
            s = subs.get(qid)
            if not s or s.get("abstencion"):
                sims.append(0.0); f1s.append(0.0); bleus.append(0.0)
                continue
            answered += 1
            pairs.append((len(sims), "query: " + ragas_text(s), "query: " + str(k.get("respuesta_esperada") or "")))
            truth = str(k.get("respuesta_esperada") or "")
            sims.append(None); f1s.append(token_f1(ragas_text(s), truth)); bleus.append(bleu(ragas_text(s), truth))
            for bucket, text in ((readability, ragas_text(s)), (ref_readability, truth)):
                score = fernandez_huerta(text)
                if score is not None:
                    bucket.append(score)
        if model is not None and pairs:
            import numpy as np
            a = model.encode([p[1] for p in pairs], normalize_embeddings=True)
            b = model.encode([p[2] for p in pairs], normalize_embeddings=True)
            for (i, _, _), x, y in zip(pairs, a, b):
                sims[i] = float(np.dot(x, y))
        n = len(key)
        result = {"run": str(path), "judged": n, "answered": answered,
                  "token_f1_mean": round(sum(f1s) / n, 4),  # = ROUGE-1 F1 over content tokens
                  "bleu4_mean": round(sum(bleus) / n, 4),
                  "legibilidad_fh": round(sum(readability) / len(readability), 1) if readability else None,
                  "legibilidad_fh_referencia": round(sum(ref_readability) / len(ref_readability), 1) if ref_readability else None,
                  "semantic_similarity_mean": round(sum(s or 0.0 for s in sims) / n, 4) if model is not None else None}
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
