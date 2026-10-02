"""Generate the official technical report from one completed sample-50 run.

Usage:
    python tools/generate_informe_tecnico.py --run-dir reports/decoder_diagnostic/RUN

Requires reportlab and pypdf. The report records measured results only; it
does not score the blind 992-question set or publish the final submission.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

from pypdf import PdfReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageTemplate, Paragraph, Spacer, Table,
    TableStyle,
)


def read_json(path: Path) -> dict:
    if not path.is_file():
        raise ValueError(f"Falta el reporte obligatorio: {path}")
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"El reporte no es un objeto JSON: {path}")
    return value


def number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Falta el valor numerico {label}")
    return float(value)


def validate(run_dir: Path, summary_path: Path, official_path: Path, ragas_path: Path) -> tuple[dict, dict, dict]:
    summary = read_json(summary_path)
    official = read_json(official_path)
    ragas = read_json(ragas_path)
    submission = run_dir / "batch" / "submissions.jsonl"
    if not submission.is_file():
        submission = run_dir / "submissions.jsonl"
    if not submission.is_file():
        raise ValueError("Falta submissions.jsonl de la misma corrida")
    rows = [json.loads(line) for line in submission.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
    ids = [row.get("id") for row in rows]
    if len(rows) != 50 or len(set(ids)) != 50:
        raise ValueError("La entrega debe tener exactamente 50 identificadores unicos")
    if summary.get("filas") != 50 or summary.get("completo") is not True:
        raise ValueError("RESUMEN.json no confirma una corrida completa de 50")
    if not summary.get("main_sha") or not summary.get("passages_sha256"):
        raise ValueError("Falta identidad del commit o del corpus en RESUMEN.json")
    for label, report, possible in (("oficial", official, 50), ("RAGAS", ragas, 80)):
        if report.get("split") != "sample":
            raise ValueError(f"{label}: solo se acepta el split sample")
        if report.get("validacion", {}).get("errores") != 0:
            raise ValueError(f"{label}: la entrega no paso la validacion oficial del esquema")
        if number(report.get("total_automatico", {}).get("posibles"), f"{label}.posibles") != possible:
            raise ValueError(f"{label}: total posible distinto de {possible}")
    for key in ("cerradas", "citas", "abstencion"):
        a = number(official.get(key, {}).get("puntos"), f"oficial.{key}")
        b = number(ragas.get(key, {}).get("puntos"), f"RAGAS.{key}")
        if a != b:
            raise ValueError(f"{key}: los dos reportes no corresponden a la misma puntuacion")
    score_50 = sum(number(official[k]["puntos"], k) for k in ("cerradas", "citas", "abstencion"))
    score_80 = score_50 + number(ragas.get("correccion_ragas", {}).get("puntos"), "RAGAS.puntos")
    if abs(score_50 - number(official["total_automatico"]["obtenidos"], "oficial.obtenidos")) > 0.011:
        raise ValueError("La suma del puntaje oficial no coincide")
    if abs(score_80 - number(ragas["total_automatico"]["obtenidos"], "RAGAS.obtenidos")) > 0.011:
        raise ValueError("La suma del puntaje RAGAS no coincide")
    judged = ragas["correccion_ragas"]
    if judged.get("n_fallidos") != 0 or number(judged.get("n_respondidos"), "RAGAS.n_respondidos") <= 0:
        raise ValueError("RAGAS no produjo veredictos validos para todos los items respondidos")
    if number(judged.get("n_juzgados"), "RAGAS.n_juzgados") != 35:
        raise ValueError("RAGAS no evaluo el subconjunto oficial de 35 preguntas de texto libre")
    if number(summary.get("segundos_por_pregunta"), "segundos_por_pregunta") <= 0:
        raise ValueError("Falta latencia medida")
    return summary, official, ragas


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D8DEE8"))
    canvas.line(1.7 * cm, 1.45 * cm, 19.3 * cm, 1.45 * cm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#53627A"))
    canvas.drawString(1.7 * cm, 1.1 * cm, "KingsCode | Informe tecnico | Sample de 50 preguntas")
    canvas.drawRightString(19.3 * cm, 1.1 * cm, f"Pagina {doc.page}")
    canvas.restoreState()


def make_pdf(summary: dict, official: dict, ragas: dict, output: Path, run_dir: Path, candidate_accepted: str | None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="KCtitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=colors.HexColor("#193157"), spaceAfter=9))
    styles.add(ParagraphStyle(name="KChead", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=14, textColor=colors.HexColor("#174B7A"), spaceBefore=9, spaceAfter=4))
    styles.add(ParagraphStyle(name="KCbody", parent=styles["BodyText"], fontSize=8.8, leading=12.5, spaceAfter=5))
    styles.add(ParagraphStyle(name="KCsmall", parent=styles["BodyText"], fontSize=7.7, leading=10.5, textColor=colors.HexColor("#4A5568"), spaceAfter=4))
    styles.add(ParagraphStyle(name="KCcenter", parent=styles["BodyText"], alignment=TA_CENTER, fontSize=8.2, leading=11))
    doc = BaseDocTemplate(str(output), pagesize=(21 * cm, 29.7 * cm), leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=1.6 * cm, bottomMargin=1.8 * cm)
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=page_footer))

    def p(value: object, style: str = "KCbody"):
        return Paragraph(escape(str(value)), styles[style])

    def section(title: str, body: object):
        return KeepTogether([p(title, "KChead"), p(body)])

    score = ragas["correccion_ragas"]
    info = [
        ["Componente", "Puntos", "Posibles"],
        ["Exactitud en cerradas", f"{official['cerradas']['puntos']:.2f}", "20"],
        ["Correccion de texto libre (RAGAS)", f"{score['puntos']:.2f}", "30"],
        ["Calidad de citacion", f"{official['citas']['puntos']:.2f}", "20"],
        ["Abstencion calibrada", f"{official['abstencion']['puntos']:.2f}", "10"],
        ["TOTAL AUTOMATICO", f"{ragas['total_automatico']['obtenidos']:.2f}", "80"],
    ]
    table = Table([[p(cell, "KCcenter") for cell in row] for row in info], colWidths=[10.5 * cm, 3.2 * cm, 3.2 * cm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E7EFF8")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E7EFF8")),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#A5B7CA")),
        ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#A5B7CA")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    seconds = number(summary["segundos_por_pregunta"], "segundos_por_pregunta")
    hours = number(summary.get("proyeccion_992_horas"), "proyeccion_992_horas")
    diagnostics = summary.get("diagnostics") or {}
    story = [
        p("Informe tecnico - KingsCode", "KCtitle"),
        p("Hackathon 2026 | Universidad de los Andes | Medicion: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "KCsmall"),
        p(f"Corrida: {run_dir.name} | Commit: {summary['main_sha']} | SHA-256 de pasajes: {summary['passages_sha256']}", "KCsmall"),
        *([p(f"Candidato experimental paso los gates de la comparacion: {candidate_accepted}. Freeze competitivo pendiente de revision cruzada.", "KCsmall")] if candidate_accepted is not None else []),
        section("1. Arquitectura del sistema", "El sistema procesa cada pregunta mediante recuperacion de pasajes juridicos, generacion con un decoder abierto y validacion de respuesta/citas. La configuracion concreta de esta corrida se consigna abajo; los resultados corresponden al sample oficial de 50 preguntas."),
        section("2. Seleccion de modelos", f"Decoder ejecutado: {summary.get('model', 'no registrado')}. Prompt: {summary.get('prompt_version', 'no registrado')}. GPU: {summary.get('gpu', 'no registrada')}. PyTorch: {summary.get('torch', 'no registrado')}. La corrida no contiene una comparacion controlada de modelos; no se declaran alternativas descartadas."),
        section("3. Estrategia de recuperacion", f"Configuracion registrada: {summary.get('retrieval', 'no registrada')}. Corpus: {summary.get('corpus', 'no registrado')}. La identidad de pasajes figura en el SHA-256 superior; este informe no certifica cobertura juridica ni vigencia normativa fuera de los reportes de corpus."),
        section("4. Citas y abstencion", f"El evaluador oficial asigno {official['citas']['puntos']:.2f}/20 a citacion y {official['abstencion']['puntos']:.2f}/10 a abstencion. Citas sin respaldo detectadas: {official.get('citas', {}).get('citas_sin_respaldo', 'no informado')}. Estos puntos miden el sample; no garantizan alineacion semantica de cada afirmacion con su cita."),
        p("5. Resultados sobre las preguntas de muestra", "KChead"),
        table,
        Spacer(1, 6),
        p(f"Automatico sin RAGAS: {official['total_automatico']['obtenidos']:.2f}/50. Juez RAGAS: {score.get('modelo_juez', 'no registrado')}; encoder del juez: {score.get('encoder', 'no registrado')}; texto libre juzgado: {score['n_juzgados']}; respondido: {score['n_respondidos']}; veredictos fallidos: 0.", "KCsmall"),
        section("6. Analisis de errores medidos", f"Cerradas no acertadas: {official['cerradas']['n'] - official['cerradas']['aciertos']} de {official['cerradas']['n']}. Citas clasificadas como incorrectas por el evaluador: {official['citas'].get('incorrectas', 'no informado')}. Abstenciones excesivas: {official['abstencion'].get('abstuvo_de_mas', 'no informado')}. Fallbacks del pipeline: {summary.get('fallbacks_pipeline_error', 'no informado')}. Son conteos del sample y no identifican por si solos la causa juridica de cada fallo."),
        section("7. Rendimiento y limitaciones", f"Latencia observada: {seconds:.1f} s/pregunta; proyeccion lineal para 992: {hours:.2f} h. VRAM pico reservada: {diagnostics.get('peak_reserved_vram_gb', 'no informada')} GB. La proyeccion es una extrapolacion del sample, no una medicion del set ciego. El puntaje del sabado y los 20 puntos de interfaz, bitacora, video y reproducibilidad no se estiman aqui."),
        p("Fuentes de cifras: RESUMEN.json, evaluation_official.json y evaluation_ragas.json de la corrida indicada. Submissions: 50 filas unicas; validacion oficial: 0 errores.", "KCsmall"),
    ]
    doc.build(story)
    reader = PdfReader(str(output))
    if not 1 <= len(reader.pages) <= 3:
        output.unlink(missing_ok=True)
        raise ValueError(f"El informe excede 3 paginas ({len(reader.pages)})")
    all_text = "\n".join(page.extract_text() or "" for page in reader.pages).casefold()
    for marker in ("Arquitectura del sistema", "Resultados sobre las preguntas", "TOTAL AUTOMATICO", "Limitaciones"):
        if marker.casefold() not in all_text:
            output.unlink(missing_ok=True)
            raise ValueError(f"El PDF no contiene la seccion esperada: {marker}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, help="Carpeta con RESUMEN.json y evaluaciones")
    parser.add_argument("--summary", type=Path)
    parser.add_argument("--official", type=Path)
    parser.add_argument("--ragas", type=Path)
    parser.add_argument("--output", "--out", dest="output", type=Path, default=Path("informe/INFORME_TECNICO.pdf"))
    parser.add_argument("--candidate-accepted", choices=("True", "False", "true", "false"))
    args = parser.parse_args()
    if args.run_dir is None and args.summary is None:
        parser.error("indique --run-dir o --summary")
    run_dir = args.run_dir or args.summary.parent
    summary_path = args.summary or run_dir / "RESUMEN.json"
    official_path = args.official or run_dir / "evaluation_official.json"
    ragas_path = args.ragas or run_dir / "evaluation_ragas.json"
    summary, official, ragas = validate(run_dir, summary_path, official_path, ragas_path)
    make_pdf(summary, official, ragas, args.output, run_dir, args.candidate_accepted)
    print(f"Informe valido: {args.output} ({len(PdfReader(str(args.output)).pages)} paginas)")


if __name__ == "__main__":
    main()
