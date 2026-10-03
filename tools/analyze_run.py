"""Export one batch run question by question for human review (offline; never feeds the pipeline).

    python tools/analyze_run.py <run>/batch                 # public review
    python tools/analyze_run.py <run>/batch --labels        # + sample_50 labels, measurement only

Writes next to the run:
  revision.jsonl  one object per question: question, final answer fields, the model's exact text
                  (raw_response: from the trace for answered items, from errors/<id>.json for
                  fallbacks), parser coercions, citation repair, evidence with rank/norm/article,
                  declared passages, tokens and timings.
  revision.md     the same, readable.
--labels reads data/sample_50.jsonl (expected letter and legal_basis) only to mark MC right/wrong
and whether the reference norm was retrieved and cited. Allowed here: the team rules let tools/analyze_*
read labels for measurement. Runs before 2026-10-01 have no raw_response for answered items.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kingscode.common import ROOT  # noqa: E402
from kingscode.reasoning.contracts import ANSWER_FIELDS  # noqa: E402
from kingscode.reasoning.official import official_bodies  # noqa: E402

CITE_FIELDS = {"multiple_choice": ("justificacion",), "semi_open": ("respuesta", "referencia_legal"),
               "open_ended": ANSWER_FIELDS["open_ended"]}


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _questions(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            out[q["id"]] = q
    return out


def export(batch: Path, labels: bool, questions_path: Path) -> list[dict]:
    questions = _questions(questions_path) if questions_path.exists() else {}
    records = []
    for item_path in sorted((batch / "items").glob("*.json"), key=lambda p: int(p.stem)):
        item = _read(item_path)
        row, trace = item["row"], item.get("trace") or {}
        d = trace.get("diagnostics") or {}
        qid = row["id"]
        error = batch / "errors" / f"{qid}.json"
        error_info = None
        raw = d.get("raw_response")
        if error.exists():
            attempt = _read(error)["attempts"][0]
            detail = attempt.get("detail") or {}
            error_info = {"code": attempt.get("code"), "reason": detail.get("reason") or attempt.get("message")}
            raw = raw or (detail.get("usage") or {}).get("raw_response")
        q = questions.get(qid, {})
        evidence = [{"rank": i, "passage_id": p.get("passage_id"), "doc_id": p.get("doc_id"),
                     "norm_name": p.get("norm_name"), "article": p.get("article"),
                     "texto_inicio": (p.get("texto") or "")[:200]}
                    for i, p in enumerate(row.get("pasajes_recuperados") or [], 1)]
        record = {
            "id": qid, "formato": row["formato"], "pregunta": q.get("pregunta"), "opciones": q.get("opciones"),
            "estado": item.get("status"), "abstencion": row["abstencion"],
            "fuente_abstencion": trace.get("abstention_source"), "motivo_abstencion": trace.get("abstention_reason"),
            "error": error_info,
            "respuesta_final": {k: row.get(k) for k in ANSWER_FIELDS[row["formato"]]},
            "salida_cruda_del_modelo": raw,
            "normalizacion": d.get("normalization_action"), "correcciones_parser": d.get("field_coercions"),
            "avisos_extension": d.get("format_warnings"), "reparacion_citas": d.get("repair_actions"),
            "citas_antes_reparacion": d.get("citations_before_repair"), "citas_despues": d.get("citations_after_repair"),
            "referencias_construidas": trace.get("built_references"),
            "pasajes_declarados_por_el_modelo": d.get("evidence_ids_used"),
            "pasajes_en_prompt": d.get("evidence_in_prompt"), "pasajes_omitidos_por_contexto": d.get("evidence_dropped_for_context"),
            "evidencia": evidence, "decision_grafo": trace.get("graph_decision"),
            "tokens_entrada": d.get("input_tokens"), "tokens_salida": d.get("output_tokens"),
            "generacion_ms": d.get("generation_ms"), "retrieval_ms": trace.get("retrieval_ms"),
        }
        if labels and q:
            cited = official_bodies(" ".join(str(row.get(k) or "") for k in CITE_FIELDS[row["formato"]]))
            basis = q.get("legal_basis")
            basis_text = " ; ".join(basis) if isinstance(basis, list) else str(basis or "")
            ref = official_bodies(basis_text)
            in_evidence = set()
            for p in (row.get("pasajes_recuperados") or [])[:10]:
                in_evidence |= official_bodies(p.get("texto") or "")
            record["medicion"] = {
                "respuesta_esperada_letra": q.get("respuesta_correcta"),
                "cerrada_correcta": (row.get("respuesta_correcta") == q.get("respuesta_correcta"))
                if row["formato"] == "multiple_choice" and not row["abstencion"] else None,
                "legal_basis": basis,
                "norma_ref_recuperada": bool(ref & in_evidence) if ref else None,
                "norma_ref_citada": bool(ref & cited) if ref else None,
                "diagnostico_cita": ("sin_ref_parseable" if not ref else "cita_ok" if ref & cited
                                     else "ref_en_evidencia_no_citada" if ref & in_evidence else "ref_fuera_de_evidencia"),
                "area": q.get("area"), "complejidad": q.get("complejidad"), "sub_tarea": q.get("sub_tarea"),
            }
        records.append(record)
    return records


def markdown(records: list[dict]) -> str:
    lines = ["# Revisión por pregunta", ""]
    for r in records:
        m = r.get("medicion") or {}
        head = f"## {r['id']} · {r['formato']}"
        if r["abstencion"]:
            head += f" · ABSTENCIÓN ({r['fuente_abstencion']})"
        if m.get("cerrada_correcta") is not None:
            head += " · ✔ correcta" if m["cerrada_correcta"] else f" · ✘ esperada {m['respuesta_esperada_letra']}"
        lines += [head, "", f"**Pregunta:** {r['pregunta']}", ""]
        if r.get("opciones"):
            lines += [f"- {k}: {v}" for k, v in r["opciones"].items()] + [""]
        if r["error"]:
            lines += [f"**Error:** {r['error']['code']}: {r['error']['reason']}", ""]
        if m:
            lines += [f"**Medición:** cita={m['diagnostico_cita']} · legal_basis={m['legal_basis']}", ""]
        lines += ["**Respuesta final:**", "```json", json.dumps(r["respuesta_final"], ensure_ascii=False, indent=2), "```"]
        if r["salida_cruda_del_modelo"]:
            lines += ["**Salida cruda del modelo:**", "```", r["salida_cruda_del_modelo"], "```"]
        lines += [f"**Parser:** {r['normalizacion']} · correcciones {r['correcciones_parser']} · avisos {r['avisos_extension']}",
                  f"**Citas:** antes {r['citas_antes_reparacion']} → después {r['citas_despues']} · reparación {r['reparacion_citas']} "
                  f"· construidas {r['referencias_construidas']}",
                  f"**Pasajes declarados por el modelo:** {r['pasajes_declarados_por_el_modelo']}",
                  "**Evidencia:**"]
        lines += [f"{e['rank']}. `{e['passage_id']}` — {e['norm_name']} art. {e['article']}" for e in r["evidencia"]]
        lines += [f"*Tokens {r['tokens_entrada']}→{r['tokens_salida']} · generación {r['generacion_ms']} ms · "
                  f"retrieval {r['retrieval_ms']} ms · grafo {r['decision_grafo']}*", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("batch", type=Path, help="run batch directory (contains items/)")
    parser.add_argument("--labels", action="store_true", help="add sample_50 measurement (expected letter, legal_basis)")
    parser.add_argument("--questions", type=Path, default=ROOT / "data/sample_50.jsonl")
    args = parser.parse_args(argv)
    records = export(args.batch, args.labels, args.questions)
    with (args.batch / "revision.jsonl").open("w", encoding="utf-8", newline="\n") as stream:
        for r in records:
            stream.write(json.dumps(r, ensure_ascii=False) + "\n")
    (args.batch / "revision.md").write_text(markdown(records), encoding="utf-8", newline="\n")
    print(json.dumps({"preguntas": len(records), "con_salida_cruda": sum(bool(r["salida_cruda_del_modelo"]) for r in records),
                      "revision_jsonl": str(args.batch / "revision.jsonl"), "revision_md": str(args.batch / "revision.md")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
