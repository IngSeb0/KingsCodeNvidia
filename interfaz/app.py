"""Interfaz gráfica (entregable 8, sección 6.2 del enunciado).

Consulta de extremo a extremo sobre el pipeline real de KingsCode: A.retrieve()
-> B.Pipeline (router -> policy -> decoder -> citation_guard). No reimplementa
nada: el pipeline se construye con tools/member_b.py::_pipeline, el mismo código
y la misma configuración de las corridas entregadas (prompt v6, citas verificadas).

Ejecutar desde la raíz del repositorio, con el corpus ya construido:
    streamlit run interfaz/app.py

Rapidez: el corpus, el índice y el decoder se cargan una sola vez por proceso
(st.cache_resource) y una pregunta ya consultada con la misma configuración se
responde al instante desde la sesión (temperatura 0: el resultado es idéntico).
Sin CUDA solo ofrece DummyDecoder (siempre se abstiene) y lo declara; si falla la
carga de un decoder real, detiene la consulta con un error visible.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from time import perf_counter

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))

from kingscode.reasoning.contracts import FORMATS, Question  # noqa: E402
from kingscode.reasoning.presentation import debug_trace, view_model  # noqa: E402

st.set_page_config(page_title="KingsCode · Derecho colombiano", page_icon="⚖", layout="wide")

FORMAT_LABELS = {"multiple_choice": "Selección múltiple", "semi_open": "Respuesta breve", "open_ended": "Caso abierto"}

# Identidad visual de Software Colombia (portada del enunciado): negro, turquesa del logo y las
# franjas diagonales azules; títulos en serif como "Hackathon 2026", cuerpo en Roboto.
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600&family=Roboto:wght@400;500;700&display=swap');
:root {
  --ink: #0B0B0B; --ink-2: #3A4448; --ink-3: #5B676D;
  --teal: #10A9A6; --teal-deep: #0B7E7C; --teal-wash: #E6F5F4;
  --blue: #1E88E5; --blue-light: #90CAF9;
  --paper: #F6F8F8; --card: #FFFFFF; --rule: #D7E1E3; --alert: #B3261E;
}
html, body, .stApp, [class*="css"] { font-family: 'Roboto', system-ui, sans-serif; color: var(--ink); }
.stApp { background: var(--paper); }
::selection { background: var(--teal); color: #fff; }
a { color: var(--teal-deep); text-underline-offset: 3px; }
:focus-visible { outline: 2px solid var(--teal-deep) !important; outline-offset: 2px; }
::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-thumb { background: #B9C8CB; border-radius: 10px; }
::-webkit-scrollbar-track { background: transparent; }
.block-container { padding-top: 1.2rem; max-width: 1320px; }
h1, h2, h3, .kc-serif { font-family: 'Playfair Display', Georgia, serif; letter-spacing: -0.01em; }

/* Cabecera: banda negra con las franjas diagonales de la portada */
.kc-head {
  position: relative; overflow: hidden; background: var(--ink); color: #fff;
  border-radius: 14px; padding: 1.6rem 2rem 1.4rem; margin-bottom: 1.1rem;
  box-shadow: 0 10px 30px -18px rgba(11,11,11,.55);
}
.kc-head::after {
  content: ""; position: absolute; top: -40%; right: -6%; width: 340px; height: 180%;
  background: linear-gradient(90deg, var(--blue-light) 0 34%, var(--blue) 34% 70%, transparent 70%);
  transform: skewX(-28deg); opacity: .95;
}
.kc-head h1 { color: #fff; font-size: 2.15rem; margin: 0; line-height: 1.1; border: 0; padding: 0; }
.kc-head p { color: #CFE3E6; margin: .45rem 0 0; max-width: 62ch; font-size: .98rem; }
.kc-head .kc-mark { color: var(--teal); }

/* Ficha técnica: una sola tira con separadores, no tarjetas iguales */
.kc-spec { display: flex; flex-wrap: wrap; background: var(--card); border: 1px solid var(--rule);
  border-radius: 12px; margin-bottom: 1rem; }
.kc-spec > div { flex: 1 1 150px; padding: .65rem 1rem; border-right: 1px solid var(--rule); min-width: 0; }
.kc-spec > div:last-child { border-right: 0; }
.kc-spec span { display: block; font-size: .72rem; color: var(--ink-3); text-transform: uppercase; letter-spacing: .06em; }
.kc-spec b { font-weight: 600; font-size: .95rem; overflow-wrap: anywhere; font-variant-numeric: tabular-nums; }

/* Controles */
.stButton > button { border-radius: 10px; font-weight: 600; transition: background .2s ease-out, transform .15s ease-out; }
.stButton > button[kind="primary"] { background: var(--teal-deep); border: 0; color: #fff; padding: .55rem 1.4rem; }
.stButton > button[kind="primary"]:hover { background: #096A68; transform: translateY(-1px); }
.stButton > button[kind="primary"]:disabled { background: #9DB7B8; }
.stTextArea textarea, .stTextInput input { border-radius: 10px !important; caret-color: var(--teal-deep); }

/* Respuesta */
.kc-answer { background: var(--card); border: 1px solid var(--rule); border-radius: 14px; padding: 1.3rem 1.5rem;
  box-shadow: 0 6px 22px -16px rgba(11,11,11,.35); }
.kc-answer h3 { margin: 0 0 .6rem; font-size: 1.35rem; }
.kc-answer p { line-height: 1.6; max-width: 72ch; margin: 0 0 .8rem; }
.kc-letter { display: inline-grid; place-items: center; width: 2.4rem; height: 2.4rem; border-radius: 10px;
  background: var(--ink); color: #fff; font-family: 'Playfair Display', serif; font-size: 1.35rem; margin-right: .6rem; }
.kc-field { font-size: .74rem; text-transform: uppercase; letter-spacing: .07em; color: var(--teal-deep); font-weight: 700; margin: 1rem 0 .25rem; }
.kc-discard { color: var(--ink-2); font-size: .92rem; margin: .2rem 0; }
.kc-abst { background: #FFF4E5; border: 1px solid #F1C68B; border-radius: 12px; padding: 1rem 1.2rem; color: #6B3E00; }
.kc-time { color: var(--ink-3); font-size: .82rem; margin-top: .6rem; font-variant-numeric: tabular-nums; }

/* Normas citadas */
.kc-chips { margin-top: .4rem; }
.kc-chip { display: inline-block; border-radius: 999px; padding: .22rem .75rem; margin: .18rem .3rem .18rem 0;
  font-size: .82rem; font-weight: 500; background: var(--teal-wash); color: #064E4C; border: 1px solid #A8DCDA; }
.kc-chip-bad { background: #fff; color: var(--alert); border: 1px dashed var(--alert); }

/* Evidencia */
.kc-ev-title { font-family: 'Playfair Display', serif; font-size: 1.15rem; margin: .2rem 0 .6rem; }
.kc-pas { background: var(--card); border: 1px solid var(--rule); border-radius: 12px; padding: .75rem .95rem;
  margin-bottom: .6rem; font-size: .88rem; line-height: 1.5; }
.kc-pas.cited { border-color: var(--teal); box-shadow: 0 0 0 1px var(--teal) inset; }
.kc-pas-h { display: flex; gap: .5rem; align-items: baseline; flex-wrap: wrap; margin-bottom: .35rem; }
.kc-rank { font-variant-numeric: tabular-nums; font-weight: 700; color: #fff; background: var(--ink);
  border-radius: 6px; padding: 0 .4rem; font-size: .76rem; }
.kc-norm { font-weight: 600; color: var(--ink); }
.kc-tag { font-size: .72rem; color: var(--teal-deep); font-weight: 700; text-transform: uppercase; letter-spacing: .05em; }
.kc-pas p { margin: 0; color: var(--ink-2); }
.kc-foot { color: var(--ink-3); font-size: .8rem; }
</style>""", unsafe_allow_html=True)

st.markdown("""<div class="kc-head"><h1>KingsCode<span class="kc-mark"> ·</span> derecho colombiano</h1>
<p>Responde con un modelo abierto de 8B y solo cita normas que aparecen en la evidencia recuperada de fuentes oficiales.
Hackathon 2026 · AI Week · Universidad de los Andes · patrocina Software Colombia.</p></div>""", unsafe_allow_html=True)

# Mismo perfil que la corrida entregada: BM25 + router, consultas por opción, prompt v6,
# citas completadas y hasta 5 menciones verificadas.
RECOMMENDED = ["--retrieval-mode", "option", "--retriever-mode", "bm25", "--citation-fill", "--cite-mentions", "5"]


def default_corpus() -> Path:
    for name in ("corpus_v01_v02_a1", "corpus_v01_v02", "corpus"):
        if (ROOT / name / "manifest.json").exists():
            return ROOT / name
    return ROOT / "corpus"


@st.cache_resource(show_spinner="Cargando corpus, índice y modelo (una sola vez)…")
def load_pipeline(corpus_dir: str, alias: str, precision: str, k: int, graph_policy: str, prompt: str = "v6", fit: bool = False):
    """Builds the pipeline with tools/member_b.py::_pipeline, the exact code of the batch runs."""
    from member_b import _pipeline, build_parser
    argv = ["batch", "--corpus", corpus_dir, "--k", str(k), "--graph-policy", graph_policy, *RECOMMENDED,
            "--prompt-version", prompt] + (["--fit-passages"] if fit else [])
    if alias != "dummy_abstain":
        argv += ["--model", alias, "--precision", precision]
    pipeline, identity = _pipeline(build_parser().parse_args(argv))
    if alias == "dummy_abstain":
        note = "Modo sin GPU: DummyDecoder se abstiene siempre. No hay razonamiento jurídico real."
    else:
        pipeline.decoder.load()
        note = None
    return pipeline, note, identity


@st.cache_data(show_spinner=False)
def question_bank() -> dict[int, dict]:
    """Public fields only (id, pregunta, formato, opciones, area, sub_tarea) of the sample and the
    blind set, so the jury's id loads the exact text, format and options without retyping."""
    out = {}
    for name in ("sample_50.jsonl", "test_992.jsonl"):
        path = ROOT / "data" / name
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            if line.strip():
                r = json.loads(line)
                out[int(r["id"])] = {"id": r["id"], "pregunta": r["pregunta"], "formato": r["formato"],
                                     "opciones": r.get("opciones") or {}, "area": r.get("area"),
                                     "sub_tarea": r.get("sub_tarea"), "origen": name.split("_")[0]}
    return out


def sample_questions() -> list[dict]:
    return [q for q in question_bank().values() if q["origen"] == "sample"]


with st.sidebar:
    st.markdown("### Configuración")
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
            decoder_options += sorted(enabled, key=lambda a: (a != "qwen3-8b", a))
        except Exception as exc:
            st.warning(f"No se pudo leer config/decoder_bakeoff.json: {exc}")
    else:
        st.info("Sin CUDA en esta máquina: solo modo sin GPU (abstención).")
    decoder_options.append("dummy_abstain")
    decoder_alias = st.selectbox("Modelo", decoder_options)
    precision = st.selectbox("Precisión", ["bf16", "int8", "int4"], disabled=decoder_alias == "dummy_abstain")
    prompt_version = st.selectbox("Prompt (igual al de la entrega)", ["v6", "v9"], index=0,
                                  help="v6: razonamiento jurídico. v9: v6 + área y sub-tarea de cada pregunta.")
    fit_passages = st.checkbox("Ver los 8 pasajes completos en el prompt (fit)", value=False)
    k = st.slider("Pasajes recuperados (k)", 1, 10, 8)
    graph_policy = st.selectbox("Grafo normativo", ["router", "off", "auto", "on"], index=0)
    debug_mode = st.checkbox("Mostrar traza técnica", value=False)

if not (Path(corpus_dir) / "manifest.json").exists():
    st.error(f"No hay corpus en {corpus_dir}. Restaure el respaldo (tools/kingscode_snapshot.ps1 -Accion restaurar) "
             "o corrija la ruta en la barra lateral.")
    st.stop()

try:
    pipeline, decoder_note, identity = load_pipeline(corpus_dir, decoder_alias, precision, k, graph_policy, prompt_version, fit_passages)
except Exception as exc:
    st.error(f"No se pudo cargar el modelo «{decoder_alias}». Revise que la GPU esté libre (nvidia-smi) y que los pesos estén descargados.")
    with st.expander("Detalle técnico"):
        st.exception(exc)
    st.stop()
if decoder_note:
    st.warning(decoder_note)

corpus_sha = str(identity.get("retriever", {}).get("corpus_sha256") or "n/d")
spec = [("Modelo", str((identity.get("decoder") or [decoder_alias])[0]).replace("transformers:", "")),
        ("Prompt", str(identity.get("prompt_version") or "n/d").replace("grounded-formats-", "")),
        ("Recuperación", f"{identity.get('retriever', {}).get('mode', 'bm25').upper()} + grafo · k={identity.get('k', k)}"),
        ("Temperatura", "0 · determinista"),
        ("Corpus · SHA-256", corpus_sha[:12])]
st.markdown('<div class="kc-spec">' + "".join(f"<div><span>{html.escape(a)}</span><b>{html.escape(b)}</b></div>" for a, b in spec)
            + "</div>", unsafe_allow_html=True)

# --- Consulta ---------------------------------------------------------------------------------
def load_into_form(q: dict) -> None:
    st.session_state["kc_q"] = q["pregunta"]
    st.session_state["kc_f"] = q["formato"]
    st.session_state["kc_meta"] = {"area": q.get("area"), "sub_tarea": q.get("sub_tarea"), "id": q["id"]}
    for letra in "ABCD":
        st.session_state[f"kc_o_{letra}"] = q["opciones"].get(letra, "")


bank = question_bank()
id_col, btn_col = st.columns([3, 1], vertical_alignment="bottom")
qid = id_col.text_input("Id de la pregunta (muestra o set de 992)", key="kc_id", placeholder="p. ej. 24")
if btn_col.button("Cargar por id", disabled=not qid.strip()):
    q = bank.get(int(qid)) if qid.strip().isdigit() else None
    if q:
        load_into_form(q)
        st.session_state["kc_pick"] = None
    else:
        st.error(f"No existe la pregunta con id {qid} en data/sample_50.jsonl ni en data/test_992.jsonl.")

samples = sample_questions()
if samples:
    pick = st.selectbox("Cargar una pregunta de la muestra (opcional)", ["—"] + [f"{s['id']} · {FORMAT_LABELS[s['formato']]} · {s['pregunta'][:90]}" for s in samples])
    if pick != "—" and st.session_state.get("kc_pick") != pick:
        chosen = samples[[f"{s['id']} · {FORMAT_LABELS[s['formato']]} · {s['pregunta'][:90]}" for s in samples].index(pick)]
        st.session_state["kc_pick"] = pick
        load_into_form(chosen)

formato = st.radio("Formato", list(FORMATS), horizontal=True, format_func=FORMAT_LABELS.get, key="kc_f")
pregunta = st.text_area("Pregunta jurídica", height=110, key="kc_q",
                        placeholder="¿Cuál es el término para contestar la demanda en el proceso verbal sumario?")
opciones = {}
if formato == "multiple_choice":
    cols = st.columns(2)
    for i, letra in enumerate("ABCD"):
        opciones[letra] = cols[i % 2].text_input(f"Opción {letra}", key=f"kc_o_{letra}")
    opciones = {k_: v for k_, v in opciones.items() if v.strip()}

ready = bool(pregunta.strip()) and (formato != "multiple_choice" or len(opciones) >= 2)
cache = st.session_state.setdefault("kc_cache", {})
config_key = (corpus_dir, decoder_alias, precision, k, graph_policy, prompt_version, fit_passages)
if st.button("Responder con evidencia", type="primary", disabled=not ready):
    key = (pregunta.strip(), formato, tuple(sorted(opciones.items())), config_key)
    if key in cache:
        st.session_state["kc_last"] = {**cache[key], "from_cache": True}
    else:
        started = perf_counter()
        with st.spinner("Recuperando evidencia y redactando la respuesta…"):
            try:
                meta = st.session_state.get("kc_meta") or {}
                original = bank.get(int(meta["id"])) if meta.get("id") is not None else None
                same = bool(original) and original["pregunta"] == pregunta.strip() and original["formato"] == formato
                qid_run = int(meta["id"]) if same else 0
                row, trace = pipeline.run(Question(qid_run, pregunta.strip(), formato, opciones,
                                                   area=meta.get("area") if same else None,
                                                   sub_tarea=meta.get("sub_tarea") if same else None))
                result = {"question": pregunta.strip(), "format": formato, "row": row, "trace": trace,
                          "seconds": perf_counter() - started}
                cache[key] = result
                st.session_state["kc_last"] = {**result, "from_cache": False}
            except Exception as exc:
                st.session_state.pop("kc_last", None)
                st.error("La consulta falló y no se generó respuesta. Revise el detalle técnico.")
                with st.expander("Detalle técnico"):
                    st.exception(exc)
elif not ready:
    st.caption("Escriba la pregunta" + (" y al menos dos opciones." if formato == "multiple_choice" else "."))

# --- Resultado ---------------------------------------------------------------------------------
last = st.session_state.get("kc_last")
if last:
    row, trace, fmt = last["row"], last["trace"], last["format"]
    view = view_model(row, trace)
    if last["question"] != pregunta.strip() or fmt != formato:
        st.info(f"Mostrando la consulta anterior: {last['question'][:140]}")
    esc = lambda s: html.escape(str(s or ""))
    izq, der = st.columns([3, 2], gap="large")
    with izq:
        if view["abstained"]:
            body = (f'<div class="kc-abst"><b>El sistema se abstiene.</b> {esc(view["abstention_reason"] or "Evidencia insuficiente")}'
                    f' · origen: {esc(view["abstention_source"] or "n/d")}</div>')
        elif fmt == "multiple_choice":
            discards = "".join(f'<p class="kc-discard"><b>{esc(l)}</b> — {esc(t)}</p>' for l, t in (row.get("descarte_opciones") or {}).items())
            body = (f'<div class="kc-answer"><h3><span class="kc-letter">{esc(row["respuesta_correcta"])}</span>Opción correcta</h3>'
                    f'<p>{esc(row["justificacion"])}</p><div class="kc-field">Opciones descartadas</div>{discards}</div>')
        elif fmt == "semi_open":
            body = (f'<div class="kc-answer"><h3>Respuesta</h3><p>{esc(row["respuesta"])}</p>'
                    f'<div class="kc-field">Referencia legal</div><p>{esc(row["referencia_legal"])}</p></div>')
        else:
            parts = "".join(f'<div class="kc-field">{t}</div><p>{esc(row[c])}</p>' for c, t in
                            [("marco_normativo", "Marco normativo"), ("analisis", "Análisis"),
                             ("jurisprudencia", "Jurisprudencia"), ("conclusion", "Conclusión")])
            body = f'<div class="kc-answer"><h3>Análisis del caso</h3>{parts}</div>'
        chips = "".join(
            f'<span class="kc-chip{"" if n["supported"] else " kc-chip-bad"}">{esc(" ".join(str(x) for x in n["body"] if x))}'
            f'{"" if n["supported"] else " · sin respaldo"}</span>' for n in view["cited_norms"])
        timing = "respuesta en memoria (consulta repetida)" if last.get("from_cache") else f"{last.get('seconds', 0):.1f} s"
        st.markdown(body + '<div class="kc-field">Normas citadas · verificadas contra la evidencia</div>'
                    + f'<div class="kc-chips">{chips or "<span class=kc-foot>La respuesta no cita normas.</span>"}</div>'
                    + f'<div class="kc-time">{timing} · {len(row["pasajes_recuperados"])} pasajes recuperados</div>',
                    unsafe_allow_html=True)

    def passage(c, cited: bool) -> str:
        tags = (["citado"] if c["cited"] else []) + (["usado por el modelo"] if c["declared_used"] else [])
        art = f" · art. {esc(c['article'])}" if c.get("article") else ""
        text = c["texto"] or ""
        link = f' · <a href="{html.escape(c["source_url"] or "", quote=True)}" target="_blank" rel="noopener">fuente oficial</a>' if c.get("source_url") else ""
        return (f'<div class="kc-pas{" cited" if cited else ""}"><div class="kc-pas-h"><span class="kc-rank">P{c["rank"]}</span>'
                f'<span class="kc-norm">{esc(c["norm_name"])}{art}</span>'
                + "".join(f'<span class="kc-tag">{t}</span>' for t in tags) + f'{link}</div>'
                f'<p>{esc(text[:700])}{"…" if len(text) > 700 else ""}</p></div>')

    with der:
        st.markdown(f'<div class="kc-ev-title">Evidencia citada ({len(view["cited_passages"])})</div>'
                    + "".join(passage(c, True) for c in view["cited_passages"]), unsafe_allow_html=True)
        with st.expander(f"Otros pasajes recuperados ({len(view['other_passages'])})", expanded=not view["cited_passages"]):
            st.markdown("".join(passage(c, False) for c in view["other_passages"]) or "—", unsafe_allow_html=True)
        st.markdown('<p class="kc-foot">Son exactamente los pasajes de <code>pasajes_recuperados</code> de la entrega; '
                    'una norma se marca como respaldada si aparece en alguno de los 10 primeros.</p>', unsafe_allow_html=True)

    with st.expander("JSON de la entrega (esquema oficial)"):
        st.json(view["submission"])
    if debug_mode:
        with st.expander("Traza técnica"):
            st.json(debug_trace(trace))
