"""Build the final result document of one run (sample_50 or the blind 992), without GPU or credit.

    python tools/final_document.py reports/decoder_diagnostic/<run>          # writes <run>/DOCUMENTO_FINAL.md

Reads only what the run wrote (RESUMEN.json, evaluation_official.json, batch/batch_report.json,
batch/submissions.jsonl, verify_live.json) and, for sample_50 only, the measurement tools
(proxy RAGAS without encoder, citation alignment, taxonomy). Labels are read by those analyze_*
tools for measurement only, never by the pipeline. For the blind set it documents the delivery:
row count, sha256, abstentions, fallbacks, time and the live-verification replay.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
BASE = {"total": 37.46, "token_f1": 0.275, "bleu4": 0.087, "pct_mas_del_doble": 0.229,
        "tasa_alineadas": 0.689, "tasa_debiles": 0.109}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else None


def main(argv=None) -> int:
    run = Path((argv or sys.argv[1:])[0])
    resumen = read(run / "RESUMEN.json") or {}
    ev = read(run / "evaluation_official.json")
    batch = read(run / "batch" / "batch_report.json") or {}
    sub = run / "batch" / "submissions.jsonl"
    rows = [json.loads(l) for l in sub.read_text(encoding="utf-8").splitlines() if l.strip()] if sub.exists() else []
    sha = hashlib.sha256(sub.read_bytes()).hexdigest() if sub.exists() else None
    formats = {}
    for r in rows:
        f = formats.setdefault(r.get("formato"), [0, 0])
        f[0] += 1
        f[1] += bool(r.get("abstencion"))
    verify = resumen.get("verificacion_en_vivo") or {}
    lines = [f"# Documento final — corrida `{run.name}`", "",
             "| Dato | Valor |", "|---|---|",
             f"| Commit | `{resumen.get('main_sha', '?')}` |",
             f"| Modelo | {resumen.get('model', '?')} ({resumen.get('gpu', '?')}, torch {resumen.get('torch', '?')}) |",
             f"| Recuperación | {resumen.get('retrieval', '?')} |",
             f"| Prompt / citas | {resumen.get('prompt_version', '?')} · citation_fill={resumen.get('citation_fill')} · menciones={resumen.get('cite_mentions')} |",
             f"| Corpus | {resumen.get('corpus', '?')} ({resumen.get('corpus_origin', '?')}) |",
             f"| Filas entregadas | {len(rows)} · sha256 `{sha}` |",
             f"| Por formato (n / abstenciones) | " + " · ".join(f"{k}: {v[0]}/{v[1]}" for k, v in sorted(formats.items(), key=lambda x: str(x[0]))) + " |",
             f"| Fallbacks del pipeline | {len((batch.get('fallback_ids') or []))} {batch.get('fallback_ids') or ''} |",
             f"| Tiempo | {resumen.get('segundos_por_pregunta', '?')} s/pregunta · proyección 992 = {resumen.get('proyeccion_992_horas', '?')} h (ventana 6 h; margen exigido ≤ 5 h) |",
             f"| Verificación en vivo simulada | ids {verify.get('ids')} · coincide = {verify.get('all_match')} |", ""]
    if ev:
        total = ev["total_automatico"]["obtenidos"]
        lines += ["## Puntaje oficial (sample_50, sin RAGAS)", "",
                  "| Componente | Puntos | Detalle |", "|---|---:|---|",
                  f"| Cerradas | {ev['cerradas']['puntos']} / 20 | {ev['cerradas']['aciertos']}/{ev['cerradas']['n']} |",
                  f"| Citas | {ev['citas']['puntos']} / 20 | recall {ev['citas']['recall_citas_ponderado']} · sin respaldo {ev['citas']['tasa_sin_respaldo']} |",
                  f"| Abstención | {ev['abstencion']['puntos']} / 10 | bien {ev['abstencion']['respondio_bien']}, mal {ev['abstencion']['respondio_mal']}, abstuvo {ev['abstencion']['abstuvo_bien'] + ev['abstencion']['abstuvo_de_mas']} |",
                  f"| **Total sin RAGAS** | **{total} / 50** | base 37,46 → Δ {round(total - BASE['total'], 2):+} |"]
        ragas = (ev.get("correccion_ragas") or {}).get("puntos")
        if ragas is not None:
            lines.append(f"| RAGAS (juez oficial) | {ragas} / 30 | correctness {ev['correccion_ragas'].get('correctness')} |")
        lines.append("")
        from analyze_ragas_proxy import main as proxy_main  # noqa: F401  (import check)
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            proxy_main([str(sub), "--no-encoder"])
        proxy = json.loads(buf.getvalue().strip().splitlines()[-1])
        from analyze_citation_alignment import analyze
        align = analyze(sub)
        align.pop("examples", None)
        lines += ["## Calidad del texto libre y de las citas (sin crédito)", "",
                  "| Métrica | Esta corrida | Base 37,46 | Mejor si |", "|---|---:|---:|---|",
                  f"| ROUGE-1 (token-F1) vs respuesta esperada | {proxy['token_f1_mean']} | {BASE['token_f1']} | sube |",
                  f"| BLEU-4 | {proxy['bleu4_mean']} | {BASE['bleu4']} | sube |",
                  f"| Respuestas > 2× la referencia | {proxy['pct_mas_del_doble']} | {BASE['pct_mas_del_doble']} | baja |",
                  f"| Respuestas < 0,5× la referencia | {proxy['pct_menos_de_la_mitad']} | 0.114 | no sube |",
                  f"| Legibilidad (Fernández-Huerta) | {proxy['legibilidad_fh']} | 70.2 (ref. {proxy['legibilidad_fh_referencia']}) | cerca de la referencia |",
                  f"| Citas alineadas con su afirmación | {align['tasa_alineadas']} | {BASE['tasa_alineadas']} | sube |",
                  f"| Citas débiles (norma real que no sostiene) | {align['tasa_debiles']} | {BASE['tasa_debiles']} | baja |", ""]
        from analyze_taxonomy import main as taxonomy_main
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            taxonomy_main([str(sub), "--md", str(run / "taxonomia.md")])
        lines += ["## Taxonomía de fallas", "", f"Detalle por área, formato, complejidad y sub-tarea en `{run.name}/taxonomia.md`.", ""]
        adopt = (total > BASE["total"] and ev["cerradas"]["puntos"] >= 12.0 and ev["citas"]["tasa_sin_respaldo"] == 0
                 and (resumen.get("proyeccion_992_horas") or 99) <= 5)
        lines += ["## Decisión", "",
                  ("**Se adopta**: supera 37,46, no baja cerradas, 0 citas sin respaldo y cabe en ≤ 5 h."
                   if adopt else "**No se adopta todavía**: no cumple todos los criterios (total > 37,46, cerradas ≥ 12, 0 sin respaldo, ≤ 5 h)."),
                  "Si cambia el texto que lee el juez (prompt), confirmar con UNA medición RAGAS (5,46 USD) antes de usarla el sábado.", ""]
    else:
        lines += ["## Entrega (set ciego)", "",
                  f"`submissions.jsonl` con {len(rows)} filas, sha256 `{sha}`. Sin etiquetas: no hay puntaje local.",
                  "Conservar esta carpeta y el corpus/modelo intactos hasta terminar la verificación en vivo.", ""]
    out = run / "DOCUMENTO_FINAL.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(out)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
