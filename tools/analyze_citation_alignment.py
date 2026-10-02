"""Does each citation support the sentence it is in? (diagnostic only; never changes a row)

    python tools/analyze_citation_alignment.py <run>/batch/submissions.jsonl [<other>.jsonl ...] [--show 10]

The official evaluator checks that a cited body appears in the first 10 passages, not that the
cited passage says what the sentence claims. Human reviewers and LLM judges do check it. For every
sentence of the answer fields that carries a citation, this tool finds the passage(s) of the cited
norm/article in the delivered evidence and measures how much of the sentence's content vocabulary
appears in that passage text (support = share of the sentence's content tokens found in it).

    aligned   support >= 0.35   the passage plausibly states the claim
    weak      support <  0.35   real, retrieved norm that probably does not sustain the sentence
    orphan    cited body/article has no passage of its own in the evidence (mention or name only)

Lexical, deterministic and conservative: use it to compare prompts/configurations (v4 vs v6),
not as a verdict on a single sentence. Labels are not read.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from kingscode.reasoning.legal import article_key, passage_bodies, references  # noqa: E402

FIELDS = ("respuesta", "justificacion", "marco_normativo", "analisis", "jurisprudencia", "conclusion")
STOP = set("""de la el los las del en que por con para una uno como sus su se lo al es son ser este esta
estos estas ese esa dicho dicha cual cuales debe deben puede pueden segun sobre entre tambien cuando donde
mas sin ante bajo desde hasta hacia ley decreto articulo articulos sentencia corte norma numeral literal
paragrafo inciso codigo constitucion politica colombia colombiano colombiana""".split())
THRESHOLD = 0.35


def fold(text: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if unicodedata.category(c) != "Mn")


def content(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", fold(text)) if len(w) > 3 and w not in STOP and not w.isdigit()}


def sentences(text: str) -> list[str]:
    shielded = re.sub(r"\b(art|arts|núm|num|no|lit|num)\.", r"\1<dot>", text, flags=re.I)
    return [s.replace("<dot>", ".").strip() for s in re.split(r"(?<=[.;])\s+", shielded) if s.strip()]


def classify(sentence: str, ref, passages: list[dict]) -> tuple[str, float]:
    own = [p for p in passages if ref.body in passage_bodies(p)]
    if ref.article is not None:
        own = [p for p in own if article_key(p.get("article")) == article_key(ref.article)]
    if not own:
        return "orphan", 0.0
    words = content(sentence.replace(ref.raw, " "))
    if not words:
        return "aligned", 1.0
    support = max(len(words & content(p.get("texto") or p.get("text") or "")) / len(words) for p in own)
    return ("aligned" if support >= THRESHOLD else "weak"), round(support, 3)


def analyze(path: Path) -> dict:
    counts = {"aligned": 0, "weak": 0, "orphan": 0}
    examples = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("abstencion"):
            continue
        passages = (row.get("pasajes_recuperados") or [])[:10]
        for field in FIELDS:
            # The system-appended list ("Fundamento normativo: A; B.", citation_builder) names supported
            # bodies, it makes no claim: only the model's own argumentative citations are measured.
            text = str(row.get(field) or "").split("Fundamento normativo:")[0]
            for sentence in sentences(text):
                for ref in references(sentence):
                    if not ref.complete or ref.body is None:
                        continue
                    label, support = classify(sentence, ref, passages)
                    counts[label] += 1
                    if label != "aligned":
                        examples.append({"id": row["id"], "campo": field, "tipo": label, "soporte": support,
                                         "cita": ref.raw, "oracion": sentence[:220]})
    total = sum(counts.values())
    return {"run": str(path), "citas_en_oraciones": total, **counts,
            "tasa_alineadas": round(counts["aligned"] / total, 3) if total else None,
            "tasa_debiles": round(counts["weak"] / total, 3) if total else None,
            "examples": examples}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("submissions", type=Path, nargs="+")
    parser.add_argument("--show", type=int, default=0, help="print N weak/orphan examples per run")
    args = parser.parse_args(argv)
    for path in args.submissions:
        result = analyze(path)
        examples = result.pop("examples")
        print(json.dumps(result, ensure_ascii=False))
        for e in examples[:args.show]:
            print("   ", json.dumps(e, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
