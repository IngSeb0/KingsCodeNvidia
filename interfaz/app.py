"""Streamlit UI for single legal questions and JSONL batches.

Run from the repository root after building the corpus:
    streamlit run interfaz/app.py

The live demo uses the measured hybrid profile for brief and open answers; BM25 delivery artifacts remain separate.
Uploaded rows are allowlisted to the public Question contract.
"""
from __future__ import annotations

import hashlib
import gc
import html
import json
import sys
import tempfile
from argparse import ArgumentParser
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from interfaz.batch_io import parse_questions_jsonl, submissions_jsonl  # noqa: E402
from interfaz.judge_verification import (  # noqa: E402
    identity_differences,
    official_score,
    parse_run_identity_json,
    parse_submission_rows_jsonl,
    verify_questions_match_identity,
)
from kingscode.reasoning.batch import BatchRunner, compare_submission_rows, questions_sha256  # noqa: E402
from kingscode.reasoning.contracts import FORMATS, Question  # noqa: E402
from kingscode.reasoning.presentation import debug_trace, view_model  # noqa: E402

st.set_page_config(page_title="KingsCode · Derecho colombiano", page_icon="⚖️", layout="wide")

st.markdown("""<style>
:root {
    --kc-teal: #0e938f;
    --kc-teal-dark: #08716f;
    --kc-ink: #13232c;
    --kc-blue: #245b85;
    --kc-muted: #60737c;
    --kc-paper: #f4f8f8;
}
.stApp { background: var(--kc-paper); }
h1, h2, h3 { color: var(--kc-ink); }
h1 { border-bottom: 3px solid var(--kc-teal); padding-bottom: .35rem; }
[data-testid="stTabs"] button[role="tab"] { font-weight: 650; }
.kc-banner {
    background: var(--kc-ink); color: #fff; padding: .8rem 1rem; border-radius: 9px;
    border-left: 5px solid var(--kc-teal); margin: .7rem 0 1rem; font-size: .92rem;
}
.kc-evidence {
    border-left: 4px solid var(--kc-blue); background: #fff; padding: .6rem .85rem;
    margin: .25rem 0 .7rem; border-radius: 0 8px 8px 0; color: var(--kc-ink);
}
.kc-evidence small { color: var(--kc-muted); }
.kc-header { display: flex; align-items: center; justify-content: space-between; gap: 1.2rem;
    background: #fff; border-radius: 12px; padding: .9rem 1.3rem; border-bottom: 4px solid var(--kc-teal);
    box-shadow: 0 1px 4px rgba(19,35,44,.08); margin-bottom: .4rem; flex-wrap: wrap; }
.kc-title { margin: 0; padding: 0; border: none; font-size: 1.85rem; }
.kc-sub { color: var(--kc-muted); font-size: .95rem; margin-top: .25rem; }
.kc-logo { height: 78px; width: auto; }
.stButton > button[kind="primary"] { background: var(--kc-teal); border-color: var(--kc-teal); }
.stButton > button[kind="primary"]:hover { background: var(--kc-teal-dark); border-color: var(--kc-teal-dark); }
</style>""", unsafe_allow_html=True)

import base64  # noqa: E402

_LOGO = ROOT / "interfaz" / "assets" / "software_colombia_logo.png"
_logo_html = (f'<img src="data:image/png;base64,{base64.b64encode(_LOGO.read_bytes()).decode()}" '
              'alt="Software Colombia" class="kc-logo">' if _LOGO.exists() else "")
st.markdown(f"""<div class="kc-header">
  <div><h1 class="kc-title">KingsCode · Consulta de derecho colombiano</h1>
  <div class="kc-sub">Hackathon 2026 · AI Week · Universidad de los Andes · Patrocina <b>Software Colombia</b></div></div>
  {_logo_html}
</div>""", unsafe_allow_html=True)


RECOMMENDED_ARGS = [
    "--retrieval-mode", "option",
    "--retriever-mode", "bm25",
    "--prompt-version", "v6",   # configuracion entregada (-Recomendada -PromptVersion v6)
    "--citation-fill",
]
CANDIDATE_3746 = {
    "name": "m5 · Qwen3-8B / BM25 · 37,46/50",
    "questions": ROOT / "data" / "sample_50.jsonl",
    "submission_candidates": (
        ROOT / "docs" / "entrega_viernes" / "submissions_sample50.jsonl",
        ROOT / "reports" / "decoder_diagnostic" / "qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_115609"
        / "replay_m5" / "submissions.jsonl",
    ),
    "identity": ROOT / "reports" / "decoder_diagnostic" / "qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_115609"
    / "batch" / "identity.json",
    "evaluation": ROOT / "reports" / "decoder_diagnostic" / "qwen3-8b_bm25_c30_rb2_gb10_pv4_fill_men3_20261002_115609"
    / "replay_m5" / "evaluation_official.json",
    "cite_mentions": 5,
    "score": 37.46,
}


def default_corpus() -> Path:
    for name in ("corpus_v01_v02_a1", "corpus_v01_v02", "corpus"):
        if (ROOT / name / "manifest.json").exists():
            return ROOT / name
    return ROOT / "corpus"


@st.cache_resource(show_spinner="Cargando corpus, índice y decoder…")
def load_pipeline(corpus_dir: str, alias: str, precision: str, k: int, graph_policy: str, semantic: bool = False):
    """Build the exact recommended pipeline via tools/member_b.py::_pipeline."""
    from member_b import _pipeline

    try:
        from member_b import build_parser
    except ImportError:
        # Compatibility with the pre-builder CLI in older working checkouts.
        # On main, build_parser() is used and supports the full frozen profile.
        parser = ArgumentParser()
        parser.add_argument("command", choices=["batch"])
        parser.add_argument("--corpus", type=Path)
        parser.add_argument("--k", type=int, default=8)
        parser.add_argument("--graph-policy", choices=["router", "off", "auto", "on"], default="router")
        parser.add_argument("--retrieval-mode", choices=["base", "option", "plan"], default="option")
        parser.add_argument("--retriever-mode", choices=["bm25", "dense", "hybrid"], default="bm25")
        parser.add_argument("--candidate-k", type=int, default=30)
        parser.add_argument("--reranker-batch-size", type=int, default=2)
        parser.add_argument("--graph-budget", type=int, default=10)
        parser.add_argument("--retrieval-text-mode", choices=["literal", "context"], default="literal")
        parser.add_argument("--embedding-instruction-profile", default="baseline")
        parser.add_argument("--reranker-instruction-profile", default="baseline")
        parser.add_argument("--reranker-score-cache", action="store_true")
        parser.add_argument("--option-support", action="store_true")
        parser.add_argument("--constrained-json", action="store_true")
        parser.add_argument("--plan-roles")
        parser.add_argument("--plans", type=Path)
        parser.add_argument("--dense-index-dir", type=Path)
        parser.add_argument("--exact-locator", action="store_true")
        parser.add_argument("--fixture-evidence", action="store_true")
        parser.add_argument("--rerank", action="store_true")
        parser.add_argument("--model")
        parser.add_argument("--precision", choices=["bf16", "int8", "int4"], default="bf16")
        parser.add_argument("--allow-optional", action="store_true")
        parser.add_argument("--prompt-version", choices=["v3", "v4", "v6"], default="v6")
        parser.add_argument("--citation-fill", action="store_true")
        parser.add_argument("--native-option-fusion", action="store_true")
        build_parser = lambda: parser

    parser = build_parser()
    args = ["batch", "--corpus", corpus_dir, "--k", str(k), "--graph-policy", graph_policy]
    args.extend(RECOMMENDED_ARGS)
    if semantic:
        # Misma configuracion que tools/kingscode_mejora.ps1: BM25 + encoder en semiabiertas y abiertas.
        args.extend(["--retriever-mode", "hybrid", "--hybrid-formats", "semi_open,open_ended"])
    available_options = {option for action in parser._actions for option in action.option_strings}
    if "--cite-mentions" in available_options:
        args.extend(["--cite-mentions", "5"])
    if alias != "dummy_abstain":
        args.extend(["--model", alias, "--precision", precision])
    parsed = parser.parse_args(args)
    pipeline, identity = _pipeline(parsed)
    identity["ui_model_precision"] = precision
    if alias == "dummy_abstain":
        note = "DummyDecoder: se abstiene siempre; no genera respuestas jurídicas."
    else:
        pipeline.decoder.load()
        note = f"Decoder local: {alias} · {precision} · temp. 0 · prompt v6 · citas verificadas"
    return pipeline, note, identity


def get_pipeline(corpus_dir: str, alias: str, precision: str, k: int, graph_policy: str, semantic: bool = False):
    """Keep one configured decoder resident instead of caching GPU copies per setting."""
    settings = (str(Path(corpus_dir).resolve()), alias, precision, k, graph_policy, semantic)
    previous = st.session_state.get("_pipeline_settings")
    if previous is not None and previous != settings:
        load_pipeline.clear()
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    st.session_state["_pipeline_settings"] = settings
    return load_pipeline(corpus_dir, alias, precision, k, graph_policy, semantic)


with st.sidebar:
    st.header("Configuración")
    corpus_dir = st.text_input("Directorio del corpus", value=str(default_corpus()))
    try:
        import torch

        cuda_ok = torch.cuda.is_available()
    except Exception:
        cuda_ok = False
    decoder_options = []
    if cuda_ok:
        try:
            from kingscode.generation.config import load_bakeoff

            enabled = [a for a, c in load_bakeoff()["candidates"].items() if c["enabled"]]
            decoder_options += sorted(enabled, key=lambda alias: (alias != "qwen3-8b", alias))
        except Exception as exc:
            st.warning(f"No se pudo leer config/decoder_bakeoff.json: {exc}")
    else:
        st.info("Sin CUDA en esta máquina: solo está disponible DummyDecoder (abstención).")
    decoder_options.append("dummy_abstain")
    decoder_alias = st.selectbox("Decoder", decoder_options)
    precision = st.selectbox("Precisión", ["bf16", "int8", "int4"], disabled=decoder_alias == "dummy_abstain")
    k = st.slider("Pasajes recuperados", 1, 10, 8)
    graph_policy = st.selectbox("Política de grafo", ["router", "off", "auto", "on"], index=0)
    semantic = True
    st.info("Demo oficial: búsqueda híbrida (BM25 + Qwen3-Embedding) en respuesta breve y caso abierto. "
            "Selección múltiple conserva búsqueda por opciones BM25.")
    debug_mode = st.checkbox("Mostrar traza técnica", value=False)

if not (Path(corpus_dir) / "manifest.json").exists():
    st.error(f"No se encontró `manifest.json` en `{corpus_dir}`.")
    st.info("Construya el índice de A con `tools/member_a.py` o corrija la ruta del corpus.")
    st.stop()

dense_index = Path(corpus_dir) / "index" / "dense.npy"
dense_metadata = Path(corpus_dir) / "index" / "dense.meta.json"
if not dense_index.is_file() or not dense_metadata.is_file():
    st.error("La demo híbrida requiere el índice denso completo para este corpus.")
    st.code(f".venv\\Scripts\\python.exe tools\\member_a.py dense --corpus \"{corpus_dir}\"", language="powershell")
    st.stop()

try:
    pipeline, decoder_note, pipeline_identity = get_pipeline(corpus_dir, decoder_alias, precision, k, graph_policy, semantic)
except Exception as exc:
    st.error(f"No se pudo cargar el perfil híbrido de demo ({type(exc).__name__}): {exc}")
    st.stop()

st.markdown(
    f'<div class="kc-banner">{html.escape(decoder_note)} · HÍBRIDO (BM25 + Qwen3-Embedding en breve/abiertas) · corpus: '
    f'<code>{html.escape(Path(corpus_dir).name)}</code></div>',
    unsafe_allow_html=True,
)
st.caption("Perfil de demo en vivo: búsqueda híbrida en respuesta breve y caso abierto, búsqueda BM25 por opciones en selección múltiple, "
           "router de grafo, prompt v6 y citation-fill. La entrega y sus manifiestos conservan la corrida BM25; sus puntajes no son del híbrido.")


FORMAT_LABELS = {
    "multiple_choice": "Selección múltiple",
    "semi_open": "Respuesta breve",
    "open_ended": "Caso abierto",
}


def render_passage(passage: dict, expanded: bool = False) -> None:
    title = html.escape(str(passage.get("norm_name") or "Fuente jurídica"))
    article = passage.get("article")
    article_label = f" · art. {html.escape(str(article))}" if article else ""
    status = "Cita o evidencia atribuida" if passage.get("cited") or passage.get("declared_used") else "Recuperado"
    with st.expander(f"[P{passage['rank']}] {title}{article_label} · {status}", expanded=expanded):
        st.write(passage.get("texto") or "")
        source_url = passage.get("source_url") or ""
        parsed = urlparse(source_url)
        if parsed.scheme in {"https", "http"} and parsed.netloc:
            st.link_button("Abrir fuente", source_url)
        elif source_url:
            st.caption(f"Fuente: {source_url}")
        else:
            st.caption("El pasaje no tiene URL de fuente registrada.")


def render_result(question: Question, row: dict, trace: dict) -> None:
    view = view_model(row, trace)
    left, right = st.columns([1.2, 1], gap="large")
    with left:
        st.subheader("Respuesta")
        if view["abstained"]:
            st.warning(
                f"El sistema se abstiene. Motivo: {view['abstention_reason'] or 'sin especificar'} · "
                f"origen: {view['abstention_source'] or 'n/d'}."
            )
        elif question.format == "multiple_choice":
            st.markdown(f"### Opción {row['respuesta_correcta']}")
            st.write(row.get("justificacion") or "")
            for letter, text in (row.get("descarte_opciones") or {}).items():
                st.markdown(f"**{letter}** · {text}")
        elif question.format == "semi_open":
            st.write(row.get("respuesta") or "")
            if row.get("palabras_clave"):
                st.caption("Palabras clave: " + ", ".join(row["palabras_clave"]))
            if row.get("referencia_legal"):
                st.markdown(f"**Referencia legal:** {row['referencia_legal']}")
        else:
            for field, title in (
                ("marco_normativo", "Marco normativo"),
                ("analisis", "Análisis"),
                ("jurisprudencia", "Jurisprudencia"),
                ("conclusion", "Conclusión"),
            ):
                if row.get(field):
                    st.markdown(f"**{title}**")
                    st.write(row[field])

        st.markdown("**Normas citadas**")
        if not view["cited_norms"]:
            st.caption("La respuesta no cita normas.")
        else:
            for norm in view["cited_norms"]:
                label = " · ".join(str(part) for part in norm["body"] if part)
                if norm["supported"]:
                    st.success(f"{label} · presente en la evidencia", icon="✅")
                else:
                    st.warning(f"{label} · sin respaldo en evidencia", icon="⚠️")

        with st.expander("JSON de entrega (schema oficial)"):
            st.json(view["submission"])

    with right:
        st.subheader(f"Evidencia y fuentes · {len(row['pasajes_recuperados'])} pasajes")
        if view["cited_passages"]:
            st.caption("Citas y pasajes atribuidos")
            for passage in view["cited_passages"]:
                render_passage(passage, expanded=True)
        if view["other_passages"]:
            st.caption("Otros pasajes recuperados")
            for passage in view["other_passages"]:
                render_passage(passage)
        if not row["pasajes_recuperados"]:
            st.info("No se recuperó evidencia para esta pregunta.")
        if debug_mode:
            with st.expander("Traza técnica (operador)"):
                st.json(debug_trace(trace))


single_tab, batch_tab, judge_tab = st.tabs(
    ["Consulta individual", "Cargar lote", "Verificar ID del jurado"]
)

@st.cache_data(show_spinner=False)
def _question_bank() -> dict:
    """Public fields of the sample (50) and the blind set (992): the jury's id loads the exact text."""
    bank = {}
    for name in ("sample_50.jsonl", "test_992.jsonl"):
        path = ROOT / "data" / name
        if path.exists():
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    r = json.loads(line)
                    bank[int(r["id"])] = {"pregunta": r["pregunta"], "formato": r["formato"], "opciones": r.get("opciones") or {}}
    return bank


with single_tab:
    st.subheader("Analiza una pregunta")
    id_col, id_btn = st.columns([3, 1], vertical_alignment="bottom")
    load_id = id_col.text_input("ID de la pregunta (muestra o set de 992)", key="single_load_id", placeholder="Ej. 24")
    if id_btn.button("Cargar por ID", key="single_load_btn", disabled=not load_id.strip()):
        record = _question_bank().get(int(load_id)) if load_id.strip().isdigit() else None
        if record:
            st.session_state["single_format"] = record["formato"]
            st.session_state["single_question"] = record["pregunta"]
            for letter in "ABCD":
                st.session_state[f"single_option_{letter}"] = record["opciones"].get(letter, "")
        else:
            st.error(f"No existe la pregunta con ID {load_id} en data/sample_50.jsonl ni en data/test_992.jsonl.")
    formato = st.radio(
        "Formato",
        list(FORMATS),
        horizontal=True,
        format_func=lambda value: FORMAT_LABELS[value],
        key="single_format",
    )
    pregunta = st.text_area(
        "Pregunta",
        height=115,
        placeholder="Escriba la pregunta jurídica…",
        key="single_question",
    )
    opciones: dict[str, str] = {}
    if formato == "multiple_choice":
        st.caption("Complete las cuatro opciones para una pregunta de selección múltiple.")
        option_cols = st.columns(2)
        for index, letter in enumerate("ABCD"):
            opciones[letter] = option_cols[index % 2].text_input(
                f"Opción {letter}", key=f"single_option_{letter}"
            )
    submitted = st.button("Analizar pregunta", type="primary", use_container_width=True, key="single_analyze")

    if submitted:
        if not pregunta.strip():
            st.error("Escriba la pregunta antes de analizarla.")
        elif formato == "multiple_choice" and any(not opciones.get(letter, "").strip() for letter in "ABCD"):
            st.error("Complete las opciones A, B, C y D.")
        else:
            question = Question(0, pregunta.strip(), formato, {key: value.strip() for key, value in opciones.items() if value.strip()})
            # Temperature 0: the same question returns the same answer, so a repeat is served instantly.
            memo = st.session_state.setdefault("single_memo", {})
            memo_key = (question.text, question.format, tuple(sorted(question.options.items())), str(corpus_dir), decoder_alias, k, graph_policy, semantic)
            try:
                if memo_key in memo:
                    row, trace = memo[memo_key]
                else:
                    with st.spinner("Recuperando evidencia y generando respuesta…"):
                        row, trace = pipeline.run(question)
                    memo[memo_key] = (row, trace)
                st.session_state["single_result"] = {"question": question, "row": row, "trace": trace}
            except Exception as exc:
                st.error(f"No se pudo analizar la pregunta: {type(exc).__name__}: {exc}")

    single_result = st.session_state.get("single_result")
    if single_result:
        st.divider()
        render_result(single_result["question"], single_result["row"], single_result["trace"])

with batch_tab:
    st.subheader("Carga y analiza varias preguntas")
    source = st.radio(
        "Origen",
        ["Subir archivo JSONL", "Usar sample_50 del repositorio"],
        horizontal=True,
        key="batch_source",
    )
    payload = None
    source_name = ""
    if source == "Subir archivo JSONL":
        uploaded = st.file_uploader("Archivo de preguntas (.jsonl)", type=["jsonl"], key="batch_upload")
        if uploaded is not None:
            payload, source_name = uploaded.getvalue(), uploaded.name
    else:
        sample_path = ROOT / "data" / "sample_50.jsonl"
        if sample_path.exists():
            payload, source_name = sample_path.read_bytes(), sample_path.name
            st.caption(f"Archivo local: `{sample_path.relative_to(ROOT)}`")
        else:
            st.error("No se encontró data/sample_50.jsonl en este checkout.")

    questions: list[Question] = []
    fingerprint = None
    if payload is not None:
        fingerprint = hashlib.sha256(payload).hexdigest()
        if st.session_state.get("batch_fingerprint") != fingerprint:
            for state_key in ("batch_results", "batch_report", "batch_submission", "batch_run_dir", "batch_result_id"):
                st.session_state.pop(state_key, None)
            st.session_state["batch_fingerprint"] = fingerprint
        try:
            questions = parse_questions_jsonl(payload)
        except (TypeError, ValueError) as exc:
            st.error(f"No se pudo cargar `{source_name}`: {exc}")
        else:
            st.success(f"{len(questions)} preguntas válidas · {source_name}")
            saved_results = st.session_state.get("batch_results") or {}
            table = [
                {
                    "ID": question.id,
                    "Formato": FORMAT_LABELS[question.format],
                    "Pregunta": question.text.replace("\n", " ").strip(),
                    "Estado": (
                        "Error · abstención"
                        if saved_results.get(question.id, {}).get("status") == "fallback"
                        else "Abstención"
                        if saved_results.get(question.id, {}).get("row", {}).get("abstencion")
                        else "Lista"
                        if question.id in saved_results
                        else "Pendiente"
                    ),
                }
                for question in questions
            ]
            st.dataframe(table, hide_index=True, use_container_width=True, height=min(410, 44 + len(table) * 36))
            completed_report = st.session_state.get("batch_report")
            if completed_report:
                st.progress(1.0, text=f"Lote completo · {completed_report['rows']}/{len(questions)} preguntas")
                st.caption(
                    f"Tiempo total: {completed_report['seconds']:.1f} s · "
                    f"abstenciones de respaldo: {len(completed_report['fallback_ids'])}"
                )

    if questions:
        question_by_id = {question.id: question for question in questions}
        selected_id = st.selectbox(
            "Pregunta para analizar o revisar",
            list(question_by_id),
            format_func=lambda qid: f"{qid} · {FORMAT_LABELS[question_by_id[qid].format]} · "
            f"{question_by_id[qid].text[:100]}{'…' if len(question_by_id[qid].text) > 100 else ''}",
            key="batch_result_id",
        )
        selected_question = question_by_id[selected_id]
        action_cols = st.columns([1, 1])
        with action_cols[0]:
            analyze_selected = st.button("Analizar seleccionada", key="batch_analyze_one", use_container_width=True)
        with action_cols[1]:
            run_all = st.button("Ejecutar lote completo", type="primary", key="batch_run_all", use_container_width=True)

        if analyze_selected:
            try:
                with st.spinner(f"Analizando pregunta {selected_question.id}…"):
                    row, trace = pipeline.run(selected_question)
                results = dict(st.session_state.get("batch_results") or {})
                results[selected_question.id] = {"row": row, "trace": trace, "status": "ok"}
                st.session_state["batch_results"] = results
                st.rerun()
            except Exception as exc:
                st.error(f"No se pudo analizar la pregunta {selected_question.id}: {type(exc).__name__}: {exc}")

        if run_all:
            identity = {
                "origin": source_name,
                "input_sha256": fingerprint,
                "corpus_dir": str(Path(corpus_dir).resolve()),
                "decoder": decoder_alias,
                "precision": precision,
                "passages_k": k,
                "graph_policy": graph_policy,
                "recommended": RECOMMENDED_ARGS,
            }
            progress = st.progress(0.0, text=f"Preparando lote: 0/{len(questions)}")
            current = st.empty()
            metric_cols = st.columns(4)
            completed_metric, average_metric, failures_metric, retries_metric = [col.empty() for col in metric_cols]

            def update_progress(event: dict) -> None:
                completed = event["completed"]
                total = event["total"]
                progress.progress(completed / total, text=f"Procesando preguntas · {completed}/{total}")
                counts = event["counts"]
                current.markdown(
                    f"**Pregunta actual:** {event['question_id']} · "
                    f"**Estado:** {event['status']} · "
                    f"**Tiempo transcurrido:** {event['elapsed_seconds']:.1f} s"
                )
                completed_metric.metric("Progreso", f"{completed}/{total}")
                avg = event.get("average_seconds")
                average_metric.metric("Promedio", f"{avg:.1f} s/pregunta" if avg is not None else "calculando")
                failures_metric.metric("Fallos finales", counts["fallback"])
                retries_metric.metric("Reintentos exitosos", counts["retried_ok"])

            try:
                # The runner needs disk checkpoints; use a temporary directory so
                # uploaded questions and traces are removed after the session run.
                with tempfile.TemporaryDirectory(prefix="kingscode_ui_batch_") as temporary_run:
                    run_dir = Path(temporary_run)
                    report = BatchRunner(pipeline, run_dir, identity=identity).run(
                        questions,
                        resume=False,
                        progress_callback=update_progress,
                    )
                    if not report.get("complete") or report.get("rows") != len(questions):
                        raise RuntimeError("El lote terminó sin generar todas las filas")
                    run_results = {}
                    for question in questions:
                        item_path = run_dir / "items" / f"{question.id}.json"
                        item = json.loads(item_path.read_text(encoding="utf-8"))
                        run_results[question.id] = {
                            "row": item["row"],
                            "trace": item.get("trace") or {},
                            "status": item.get("status", "ok"),
                        }
                    rows = [run_results[question.id]["row"] for question in questions]
                    submission = submissions_jsonl(rows)
                st.session_state["batch_results"] = run_results
                st.session_state["batch_report"] = report
                st.session_state["batch_submission"] = submission
                st.success(f"Lote completo: {report['rows']}/{len(questions)} · {report['seconds']:.1f} s")
                st.rerun()
            except Exception as exc:
                st.error(f"El lote no pudo completarse: {type(exc).__name__}: {exc}")

        results = st.session_state.get("batch_results") or {}
        if selected_id in results:
            st.divider()
            status = results[selected_id].get("status", "ok")
            st.caption(f"Resultado guardado · estado: {status}")
            render_result(
                selected_question,
                results[selected_id]["row"],
                results[selected_id]["trace"],
            )

        submission = st.session_state.get("batch_submission")
        report = st.session_state.get("batch_report")
        if submission is not None and report is not None:
            st.divider()
            st.subheader("Entrega del lote")
            st.write(f"Filas: {report['rows']} · SHA-256: `{report['submission_sha256']}`")
            st.download_button(
                "Descargar submissions.jsonl",
                data=submission,
                file_name="submissions.jsonl",
                mime="application/x-ndjson",
                type="primary",
                use_container_width=True,
                key="download_batch_submission",
            )


def _default_candidate_file(paths: tuple[Path, ...]) -> Path | None:
    return next((path for path in paths if path.is_file()), None)


def _read_candidate_identity() -> dict | None:
    path = CANDIDATE_3746["identity"]
    if not path.is_file():
        return None
    identity = parse_run_identity_json(path.read_bytes())
    # The delivered m5 replay added five evidence-verified norm mentions to
    # the original three-mention batch; the official 37.46 report is for m5.
    identity["cite_mentions"] = CANDIDATE_3746["cite_mentions"]
    # These settings were at their measured defaults in the m5 run; newer
    # identity writers record them explicitly.
    identity.setdefault("doc_cap", 0)
    identity.setdefault("max_context", None)
    return identity


with judge_tab:
    st.subheader("Reproducción del candidato entregado")
    st.markdown(
        "El jurado puede dar un ID. La interfaz recupera la pregunta pública, "
        "regenera una respuesta con el perfil congelado y la compara con la fila "
        "entregada de **37,46/50 (m5)**. Las respuestas esperadas nunca se pasan al modelo."
    )
    score_path = CANDIDATE_3746["evaluation"]
    reference_path = _default_candidate_file(CANDIDATE_3746["submission_candidates"])
    questions_path = CANDIDATE_3746["questions"]
    target_identity = _read_candidate_identity()
    with st.expander("Archivos del candidato de referencia", expanded=reference_path is None or target_identity is None):
        st.caption(
            "Por defecto se usan `data/sample_50.jsonl`, `docs/entrega_viernes/"
            "submissions_sample50.jsonl`, el `identity.json` de la corrida y su `evaluation_official.json`. "
            "Puede sustituirlos con los artefactos de la misma corrida."
        )
        uploaded_questions = st.file_uploader(
            "Preguntas públicas que contienen el ID (.jsonl)", type=["jsonl"], key="judge_questions_upload"
        )
        uploaded_submission = st.file_uploader(
            "Entrega congelada 37,46 (.jsonl)", type=["jsonl"], key="judge_submission_upload"
        )
        uploaded_identity = st.file_uploader(
            "Identidad de la corrida (.json)", type=["json"], key="judge_identity_upload"
        )
        uploaded_evaluation = st.file_uploader(
            "Evaluación oficial del m5 (.json)", type=["json"], key="judge_evaluation_upload"
        )

    if uploaded_evaluation:
        try:
            score_report = json.loads(uploaded_evaluation.getvalue().decode("utf-8-sig"))
            candidate_score = official_score(score_report)
        except (UnicodeDecodeError, json.JSONDecodeError):
            candidate_score = None
    elif score_path.is_file():
        try:
            score_report = json.loads(score_path.read_text(encoding="utf-8-sig"))
            candidate_score = official_score(score_report)
        except (OSError, json.JSONDecodeError):
            candidate_score = None
    else:
        candidate_score = None

    if candidate_score == CANDIDATE_3746["score"]:
        st.success("Snapshot oficial m5 verificado: 37,46/50 · Qwen3-8B · perfil BM25 congelado.")
    elif candidate_score is None:
        st.warning("No está el reporte oficial m5 en este checkout. Cargue la evaluación congelada y su identity.json.")
    else:
        st.error(f"El reporte oficial encontrado marca {candidate_score:.2f}, no 37,46. No se habilitará como candidato m5.")

    question_bytes = uploaded_questions.getvalue() if uploaded_questions else (
        questions_path.read_bytes() if questions_path.is_file() else None
    )
    submission_bytes = uploaded_submission.getvalue() if uploaded_submission else (
        reference_path.read_bytes() if reference_path else None
    )
    identity_bytes = uploaded_identity.getvalue() if uploaded_identity else (
        CANDIDATE_3746["identity"].read_bytes() if CANDIDATE_3746["identity"].is_file() else None
    )
    if reference_path and not uploaded_submission:
        st.caption(f"Entrega de referencia: `{reference_path.relative_to(ROOT)}`")

    judge_id_text = st.text_input("ID entregado por el jurado", key="judge_id_input", placeholder="Ej. 513")
    verify_judge = st.button(
        "Regenerar y comparar con 37,46",
        type="primary",
        use_container_width=True,
        key="judge_verify_button",
    )

    if verify_judge:
        try:
            if not judge_id_text.strip().isdigit():
                raise ValueError("Ingrese un ID entero.")
            if question_bytes is None or submission_bytes is None or identity_bytes is None:
                raise ValueError("Falta el JSONL de preguntas, la entrega congelada o el identity.json del candidato.")
            if candidate_score != CANDIDATE_3746["score"]:
                raise ValueError("No se pudo confirmar que el reporte de referencia corresponde a 37,46/50.")

            judge_id = int(judge_id_text.strip())
            judge_questions = parse_questions_jsonl(question_bytes)
            frozen_rows = parse_submission_rows_jsonl(submission_bytes)
            run_identity = parse_run_identity_json(identity_bytes)
            reference_identity = target_identity
            if reference_identity is None:
                sample_questions = parse_questions_jsonl(questions_path.read_bytes()) if questions_path.is_file() else []
                sample_hash = questions_sha256(sample_questions) if sample_questions else None
                if run_identity.get("questions_sha256") != sample_hash:
                    raise ValueError(
                        "Falta la identidad de referencia m5. El identity.json cargado solo puede reemplazarla "
                        "si corresponde al lote sample_50 congelado."
                    )
                reference_identity = dict(run_identity)
                reference_identity["cite_mentions"] = CANDIDATE_3746["cite_mentions"]
                reference_identity.setdefault("doc_cap", 0)
                reference_identity.setdefault("max_context", None)

            question_ids = {question.id for question in judge_questions}
            if question_ids != set(frozen_rows):
                missing_rows = sorted(question_ids - set(frozen_rows))[:5]
                extra_rows = sorted(set(frozen_rows) - question_ids)[:5]
                raise ValueError(
                    f"Preguntas y entrega no corresponden al mismo lote (sin respuesta: {missing_rows}; "
                    f"IDs extra: {extra_rows})."
                )
            if not verify_questions_match_identity(judge_questions, run_identity):
                raise ValueError("El identity.json no corresponde al JSONL de preguntas cargado.")

            # If a complete 992-item delivery is used, require its recorded
            # settings to match the measured 37.46 profile, ignoring only the
            # dataset hash, which necessarily differs from sample_50.
            custom_identity = bool(uploaded_identity)
            if custom_identity:
                if (
                    run_identity.get("questions_sha256") == reference_identity.get("questions_sha256")
                    and run_identity.get("cite_mentions") == 3
                ):
                    # The stored batch identity predates the deterministic m5
                    # replay; its delivered sample output was post-processed
                    # with five supported mentions and scored 37.46.
                    run_identity["cite_mentions"] = CANDIDATE_3746["cite_mentions"]
                    run_identity.setdefault("doc_cap", 0)
                    run_identity.setdefault("max_context", None)
                profile_diffs = identity_differences(reference_identity, run_identity)
                if profile_diffs:
                    detail = "\n".join(f"• {entry}" for entry in profile_diffs[:8])
                    raise ValueError("La corrida cargada no usa el perfil congelado 37,46:\n" + detail)

            runtime_diffs = identity_differences(reference_identity, pipeline_identity)
            if precision != "bf16":
                runtime_diffs.append(f"precision: snapshot=bf16; actual={precision}")
            if runtime_diffs:
                detail = "\n".join(f"• {entry}" for entry in runtime_diffs[:8])
                raise ValueError(
                    "El pipeline activo no coincide con el perfil m5 de 37,46. "
                    "Revise Qwen3-8B BF16, corpus y configuración:\n" + detail
                )

            by_id = {question.id: question for question in judge_questions}
            if judge_id not in by_id:
                raise ValueError(f"El ID {judge_id} no está en el JSONL de preguntas cargado.")
            question = by_id[judge_id]
            with st.spinner(f"Regenerando ID {judge_id} con Qwen3-8B y el perfil m5…"):
                generated_row, generated_trace = pipeline.run(question)
            frozen_row = frozen_rows[judge_id]
            comparison = compare_submission_rows(generated_row, frozen_row)
            st.session_state["judge_result"] = {
                "question": question,
                "expected": frozen_row,
                "actual": generated_row,
                "trace": generated_trace,
                "comparison": comparison,
                "submission_sha256": hashlib.sha256(submission_bytes).hexdigest(),
                "identity": run_identity,
                "source": "m5 37.46/50",
            }
        except Exception as exc:
            st.error(f"No se pudo verificar el ID: {type(exc).__name__}: {exc}")

    judge_result = st.session_state.get("judge_result")
    if judge_result:
        st.divider()
        comparison = judge_result["comparison"]
        status_cols = st.columns(4)
        if comparison["answer_identical"]:
            status_cols[0].success("Respuesta exacta: coincide")
        else:
            status_cols[0].error("Respuesta exacta: diferente")
        status_cols[1].metric("Citas oficiales", "Iguales" if comparison["citations_equal"] else "Diferentes")
        status_cols[2].metric("Pasajes recuperados", "Iguales" if comparison["passages_equal"] else "Diferentes")
        status_cols[3].metric("Fila JSON completa", "Igual" if comparison["row_identical"] else "Diferente")
        st.caption(
            f"ID {judge_result['question'].id} · Snapshot {judge_result['source']} · "
            f"SHA-256 de la entrega: `{judge_result['submission_sha256']}`"
        )
        if comparison["status"] == "match":
            st.success("La respuesta, sus citas y los pasajes coinciden con la entrega congelada.")
        elif comparison["answer_identical"]:
            st.warning("La respuesta coincide literalmente; las citas oficiales o los pasajes recuperados difieren.")
        else:
            st.error("La respuesta regenerada difiere de la fila entregada para este ID.")

        frozen_tab, regenerated_tab = st.tabs(["Respuesta congelada", "Respuesta regenerada"])
        with frozen_tab:
            render_result(judge_result["question"], judge_result["expected"], {})
        with regenerated_tab:
            render_result(judge_result["question"], judge_result["actual"], judge_result["trace"])
