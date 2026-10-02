"""Deterministic citation text built from A's passage metadata (plan B3).

The decoder reasons; the final citation string comes from `canonical_body` and
`article` of a passage it actually received. Every candidate string is verified
before it is returned: citation_guard's own support rule must accept it against
its source passage, and the official extractor must only find bodies that the
evaluator would count as supported by that passage. Unverifiable -> not emitted.
"""
from __future__ import annotations

import re

from .guards import reference_support
from .legal import passage_bodies, references
from .official import citations as official_citation_extractor, official_bodies

CODE_NAMES = {
    "constitucion": "Constitución Política",
    "codigo_civil": "Código Civil",
    "codigo_penal": "Código Penal",
    "codigo_procedimiento_penal": "Código de Procedimiento Penal",
    "codigo_comercio": "Código de Comercio",
    "codigo_sustantivo_trabajo": "Código Sustantivo del Trabajo",
    "codigo_procesal_trabajo": "Código Procesal del Trabajo",
    "codigo_general_proceso": "Código General del Proceso",
    "cpaca": "Código de Procedimiento Administrativo y de lo Contencioso Administrativo",
    "estatuto_tributario": "Estatuto Tributario",
    "estatuto_consumidor": "Estatuto del Consumidor",
    "codigo_infancia": "Código de la Infancia y la Adolescencia",
    "codigo_nacional_policia": "Código Nacional de Seguridad y Convivencia Ciudadana",
    "codigo_disciplinario": "Código General Disciplinario",
}
KIND_NAMES = {"ley": "Ley", "decreto": "Decreto", "acto_legislativo": "Acto Legislativo",
              "resolucion": "Resolución", "circular": "Circular", "acuerdo": "Acuerdo", "decision": "Decisión Andina"}
_ARTICLE = re.compile(r"^\d+(?:[.\-]\d+)*[A-Za-z]?$")


def body_of(passage: dict) -> tuple | None:
    canonical = passage.get("canonical_body")
    if isinstance(canonical, (list, tuple)) and len(canonical) == 3:
        return tuple(None if v is None else str(v) for v in canonical)
    bodies = sorted(passage_bodies(passage), key=str)
    return bodies[0] if bodies else None


def _names(passage: dict) -> list[str]:
    body, names = body_of(passage), []
    if body:
        kind, number, year = body
        if kind in CODE_NAMES:
            names.append(CODE_NAMES[kind])
        elif kind == "jurisprudencia" and number and year:
            names.append(f"Sentencia {number} de {year}")
        elif kind in KIND_NAMES and number and year:
            names.append(f"{KIND_NAMES[kind]} {number} de {year}")
    norm_name = (passage.get("norm_name") or "").strip().rstrip(".")
    if norm_name and norm_name not in names:
        names.append(norm_name)
    return names


def _connector(name: str) -> str:
    return "del" if re.match(r"(?:Código|Estatuto|Decreto|Acto|Acuerdo)\b", name) else "de la"


def verified(candidate: str, passage: dict) -> bool:
    refs = references(candidate)
    if not refs or any(r.kind == "unresolved" or not r.complete for r in refs):
        return False
    if any(not reference_support(r, [passage]) for r in refs):
        return False
    cited = official_bodies(candidate)
    return bool(cited) and cited <= official_bodies(passage.get("text") or "")


def render_reference(passage: dict) -> str | None:
    """Most specific verifiable citation for one passage, or None."""
    names = _names(passage)
    article = str(passage.get("article") or "")
    body = body_of(passage)
    candidates = []
    if _ARTICLE.match(article) and not (body and body[0] == "jurisprudencia"):
        candidates += [f"artículo {article} {_connector(n)} {n}" for n in names]
    candidates += names
    return next((c for c in candidates if verified(c, passage)), None)


NEUTRAL_DISCARD = "No concuerda con la evidencia recuperada."


def attribution_source(attribution: dict | None) -> str:
    if attribution is None or attribution.get("status") == "legacy_fallback":
        return "legacy_fallback"
    return "explicit" if attribution.get("status") == "explicit" else "none"


def attach_references(row: dict, evidence: list[dict], attribution: dict | None = None, max_refs: int = 3,
                      *, fill_ranked: bool = False, mentions: int = 0) -> tuple[dict, list[str]]:
    """Write builder citations into the format's citation slot (mutates and returns row).

    attribution None/legacy_fallback (dummy, v1/v2 prompts): first passages, as before.
    attribution explicit: only the passages the decoder declared it used.
    attribution malformed/not_applicable: nothing is added (attribution is never invented).
    semi_open: referencia_legal is replaced (the juez RAGAS never reads it).
    multiple_choice: appended to justificacion unless its bodies are already cited.
    open_ended: append any missing declared-source citations to marco_normativo
    (max 3; RAGAS reads it), without duplicating citations already present in any
    of the four fields read by the judge.
    """
    fmt = row.get("formato")
    source = attribution_source(attribution)
    if source == "none":
        return row, []
    used = attribution["ids"] if source == "explicit" else None
    # fill_ranked (opt-in): after the declared passages, complete up to max_refs with the
    # next-ranked evidence. Only for fields RAGAS does not read (semi_open referencia_legal,
    # multiple_choice justificacion): a supported citation outside the reference basis
    # scores 0 without penalty, a supported match raises recall. open_ended never fills.
    fill = fill_ranked and fmt in {"semi_open", "multiple_choice"}
    refs = build_references(evidence, used, 3 if fmt == "open_ended" else max_refs,
                            allow_fallback=source == "legacy_fallback", fill_ranked=fill)
    if mentions and fmt in {"semi_open", "multiple_choice"}:
        current = " ".join([*refs, row.get("justificacion") or "", row.get("respuesta") or ""])
        refs += mentioned_references(evidence, used, current, mentions)
    if not refs:
        return row, refs
    if fmt == "semi_open":
        row["referencia_legal"] = "; ".join(refs)
    elif fmt == "multiple_choice":
        just = (row.get("justificacion") or "").strip()
        new = [r for r in refs if not official_bodies(r) <= official_bodies(just)]
        if new:
            row["justificacion"] = (just + " " if just else "") + "Fundamento normativo: " + "; ".join(new) + "."
        row["descarte_opciones"] = {k: (v if isinstance(v, str) and v.strip() else NEUTRAL_DISCARD)
                                    for k, v in (row.get("descarte_opciones") or {}).items()}
    elif fmt == "open_ended":
        marco = (row.get("marco_normativo") or "").strip()
        # RAGAS scores all four open-ended fields concatenated. Keep the cited legal
        # basis complete, but don't repeat a citation already present in analysis,
        # jurisprudencia or conclusion merely because marco_normativo is citation-free.
        extractor = official_citation_extractor()
        represented = set()
        for field in ("marco_normativo", "analisis", "jurisprudencia", "conclusion"):
            represented |= extractor.extract(row.get(field) or "")
        missing = []
        for ref in refs:
            normalized = extractor.extract(ref)
            if normalized and normalized <= represented:
                continue
            missing.append(ref)
            represented |= normalized
        if missing:
            row["marco_normativo"] = (marco + " " if marco else "") + "Normas aplicables: " + "; ".join(missing) + "."
    return row, refs


def body_name(body: tuple) -> str | None:
    """Body-level citation text (no article) for a canonical (kind, number, year) body."""
    kind, number, year = body
    if kind in CODE_NAMES:
        return CODE_NAMES[kind]
    if kind == "jurisprudencia" and number and year:
        return f"Sentencia {number} de {year}"
    if kind in KIND_NAMES and number and year:
        return f"{KIND_NAMES[kind]} {number} de {year}"
    return None


def mentioned_references(passages: list[dict], used_ids: list[str] | None, already_cited: str,
                         limit: int) -> list[str]:
    """Bodies NAMED inside the text of retrieved passages (not their own document), cited
    at body level only. Opt-in (--cite-mentions). This is exactly the official support rule:
    a cited norm is backed when it appears in the text of one of the first 10 passages.
    Declared passages are scanned first, then the remaining top-10 in rank order."""
    top = passages[:10]
    order = [p for p in top if used_ids and p["passage_id"] in used_ids] + \
            [p for p in top if not (used_ids and p["passage_id"] in used_ids)]
    cited = official_bodies(already_cited or "")
    out: list[str] = []
    for passage in order:
        own = passage_bodies(passage)
        text_bodies = official_bodies(passage.get("text") or "")
        for ref in references(passage.get("text") or ""):
            if not ref.complete or ref.kind == "unresolved" or ref.body is None or ref.body in own:
                continue
            name = body_name(ref.body)
            if not name or name in out:
                continue
            bodies = official_bodies(name)
            if not bodies or not bodies <= text_bodies or bodies <= cited:
                continue
            if any(r.body != ref.body for r in references(name)):
                continue
            out.append(name)
            cited |= bodies
            if len(out) >= limit:
                return out
    return out


def build_references(passages: list[dict], used_ids: list[str] | None = None, max_refs: int = 3, *,
                     allow_fallback: bool = True, fill_ranked: bool = False) -> list[str]:
    """Citations for the passages the decoder declared it used; the first max_refs
    only when fallback is allowed (legacy contracts without attribution). fill_ranked
    appends the remaining top-10 evidence in rank order after the declared passages."""
    by_id = {p["passage_id"]: p for p in passages[:10]}
    if used_ids:
        chosen = [by_id[i] for i in used_ids if i in by_id]
        if fill_ranked:
            chosen += [p for p in passages[:10] if p["passage_id"] not in used_ids]
    else:
        chosen = passages[:max_refs] if allow_fallback else []
    refs: list[str] = []
    for passage in chosen:
        ref = render_reference(passage)
        if ref and ref not in refs:
            refs.append(ref)
        if len(refs) >= max_refs:
            break
    return refs
