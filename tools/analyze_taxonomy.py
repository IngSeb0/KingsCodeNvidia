"""Per-category breakdown of a sample_50 run (measurement only; labels never reach the pipeline).

    python tools/analyze_taxonomy.py <run>/batch/submissions.jsonl [--md out.md]

Groups every item by the official taxonomy fields of data/sample_50.jsonl (area, formato,
complejidad, sub_tarea) and reports, per group:
  cerradas   aciertos / n (multiple_choice)
  norma      items whose answer text contains >= 1 body of the legal_basis (the evaluator's
             abstention criterion for free text), and how many of the missing bodies were not
             even in the first 10 passages (retrieval miss) versus present but not cited
  abst       abstentions
  f1         token-F1 against respuesta_esperada (free proxy of RAGAS, as tools/analyze_ragas_proxy.py)
and lists every failing item with its failure type, so that fixes target a category, not an item.
Reads legal_basis/respuesta_correcta/respuesta_esperada for measurement only (allowed for analyze_*).
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))
import citations  # noqa: E402
from evaluate import answer_text  # noqa: E402
from analyze_ragas_proxy import ragas_text, token_f1  # noqa: E402

FIELDS = ("area", "formato", "complejidad", "sub_tarea")


def item_result(k: dict, s: dict) -> dict:
    out = {"id": k["id"], "abst": bool(s.get("abstencion")), "fail": None}
    if k["formato"] == "multiple_choice":
        out["mc_ok"] = s.get("respuesta_correcta") == k.get("respuesta_correcta")
        if not out["mc_ok"]:
            out["fail"] = f"cerrada: respondio {s.get('respuesta_correcta')} esperada {k.get('respuesta_correcta')}"
    else:
        out["f1"] = 0.0 if out["abst"] else token_f1(ragas_text(s), str(k.get("respuesta_esperada") or ""))
    ref = citations.bodies(citations.extract(k.get("legal_basis") or ""))
    if ref:
        got = citations.bodies(citations.extract(answer_text(s)))
        evidence = set()
        for p in (s.get("pasajes_recuperados") or [])[:10]:
            evidence |= citations.bodies(citations.extract(p.get("texto") or ""))
        missing = ref - got
        out["norm_hit"] = bool(ref & got)
        out["missing_not_retrieved"] = sorted(map(str, missing - evidence))
        out["missing_not_cited"] = sorted(map(str, missing & evidence))
        if not out["norm_hit"] and out["fail"] is None:
            out["fail"] = ("norma fuera de la evidencia (retrieval)" if out["missing_not_retrieved"]
                           else "norma en la evidencia pero no citada")
    if out["abst"] and out["fail"] is None:
        out["fail"] = "abstencion"
    return out


def summarize(rows: list[tuple[dict, dict]]) -> dict:
    mc = [r for k, r in rows if "mc_ok" in r]
    norm = [r for k, r in rows if "norm_hit" in r]
    f1 = [r["f1"] for k, r in rows if "f1" in r]
    return {"n": len(rows),
            "cerradas": f"{sum(r['mc_ok'] for r in mc)}/{len(mc)}" if mc else "-",
            "norma": f"{sum(r['norm_hit'] for r in norm)}/{len(norm)}" if norm else "-",
            "retrieval_miss": sum(bool(r["missing_not_retrieved"]) for r in norm),
            "no_citada": sum(bool(r["missing_not_cited"]) for r in norm),
            "abst": sum(r["abst"] for k, r in rows),
            "f1": round(sum(f1) / len(f1), 3) if f1 else None}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("submissions", type=Path)
    parser.add_argument("--md", type=Path, help="write a Markdown report here")
    args = parser.parse_args(argv)
    key = {int(r["id"]): r for r in (json.loads(l) for l in (ROOT / "data/sample_50.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    subs = {int(json.loads(l)["id"]): json.loads(l) for l in args.submissions.read_text(encoding="utf-8").splitlines() if l.strip()}
    pairs = [(k, item_result(k, subs.get(qid) or {"abstencion": True})) for qid, k in key.items()]
    lines = [f"# Taxonomía de fallas — `{args.submissions}`", ""]
    report = {}
    for field in FIELDS:
        groups = defaultdict(list)
        for k, r in pairs:
            groups[str(k.get(field) or "(sin dato)")].append((k, r))
        report[field] = {g: summarize(v) for g, v in sorted(groups.items())}
        lines += [f"## Por {field}", "", "| grupo | n | cerradas | norma citada | fuera de evidencia | en evidencia sin citar | abst | token-F1 |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for g, s in report[field].items():
            lines.append(f"| {g} | {s['n']} | {s['cerradas']} | {s['norma']} | {s['retrieval_miss']} | {s['no_citada']} | {s['abst']} | {s['f1'] if s['f1'] is not None else '-'} |")
        lines.append("")
    fails = [(k, r) for k, r in pairs if r["fail"]]
    lines += ["## Ítems con falla", "", "| id | área | formato | sub_tarea | complejidad | falla |", "|---:|---|---|---|---|---|"]
    for k, r in sorted(fails, key=lambda x: (x[0]["area"], x[0]["id"])):
        lines.append(f"| {k['id']} | {k['area']} | {k['formato']} | {k.get('sub_tarea') or '-'} | {k.get('complejidad') or '-'} | {r['fail']} |")
    weakest = sorted(((k, r) for k, r in pairs if "f1" in r), key=lambda x: x[1]["f1"])[:8]
    lines += ["", "## Texto libre con menor token-F1 (candidatos a mejorar RAGAS)", "", "| id | área | sub_tarea | token-F1 |", "|---:|---|---|---:|"]
    for k, r in weakest:
        lines.append(f"| {k['id']} | {k['area']} | {k.get('sub_tarea') or '-'} | {r['f1']:.3f} |")
    text = "\n".join(lines) + "\n"
    if args.md:
        args.md.write_text(text, encoding="utf-8", newline="\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
