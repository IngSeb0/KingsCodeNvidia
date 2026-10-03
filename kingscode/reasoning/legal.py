"""Conservative reference recognition; no year-blind law/code aliasing.

Used for query analysis and citation identity, not to infer legal validity or
whether a source entails a legal conclusion. Original spans remain available.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
import unicodedata


def fold(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text.lower()) if not unicodedata.combining(c))


# Ambiguous CP/C.P./CC are deliberately not expanded.
CODE_ALIASES = {
    "constitucion": ("Constitución Política", "Constitución Nacional", "Constitución", "Carta Política"),
    "codigo_general_proceso": ("Código General del Proceso", "CGP", "C.G.P."),
    "codigo_sustantivo_trabajo": ("Código Sustantivo del Trabajo", "CST", "C.S.T."),
    "codigo_procedimiento_penal": ("Código de Procedimiento Penal", "CPP", "C.P.P."),
    "codigo_penal": ("Código Penal",),
    "codigo_civil": ("Código Civil",),
    "codigo_comercio": ("Código de Comercio", "Código del Comercio"),
    "cpaca": ("Código de Procedimiento Administrativo y de lo Contencioso Administrativo", "CPACA"),
    "estatuto_tributario": ("Estatuto Tributario", "E.T."),
    "estatuto_consumidor": ("Estatuto del Consumidor", "Estatuto de Protección al Consumidor"),
    "codigo_infancia": ("Código de la Infancia y la Adolescencia",),
    "codigo_nacional_policia": ("Código Nacional de Seguridad y Convivencia Ciudadana", "Código Nacional de Policía"),
    "codigo_disciplinario": ("Código General Disciplinario",),
    "codigo_procesal_trabajo": ("Código Procesal del Trabajo",),
    "decision_andina_486": ("Decisión Andina 486", "Decisión 486"),
}
NORM = re.compile(r"\b(ley|decreto(?:[-\s]+ley| legislativo| reglamentario| unico reglamentario)?|acto legislativo|resolucion|circular(?: externa)?|acuerdo|decision(?: andina)?)\s+(?:(?:n(?:o|ro)?[.°º]*|numero)\s*)?(\d+(?:\.\d{3})*)(?:\s*(?:de|del|/|-)\s*(\d{4}))?\b", re.I)
SENTENCE = re.compile(r"\b(?:sentencia\s+)?(su|stc|stl|sl|sc|sp|c|t|ac|au)\s*[- ]?\s*(\d{1,5})\s*(?:de|del|/|-)\s*(\d{2}|\d{4})\b", re.I)
DOCKET = re.compile(r"\b(?:radicado|radicacion|expediente)\s*(?:(?:n(?:o|ro)?[.°º]?|numero)\s*)?[:.]?\s*([A-Za-z]?[- ]?\d[\d -]{3,}\d)\b", re.I)
NUMBER = r"\d+(?:\.\d+)*(?:-\d+)?(?:[a-z](?!\w)|[ \t]+[a-z](?=\s*[.,:;)]|\s+de\b|\s+del\b|$))?(?:[º°])?"
ARTICLES = re.compile(r"\b(?:arts?\.?|articulos?)\s+(transitorio\s+)?(" + NUMBER + r"(?:\s*(?:,|y|e)\s*" + NUMBER + r")*)(?!\w)", re.I)
ARTICLE_LINK = re.compile(r"^[\s.,:;]*(?:[º°])?\s*(?:(?:del mismo|de esta|de este|de la|del|de)\s+)?$", re.I)


@dataclass(frozen=True)
class Reference:
    kind: str
    body: tuple[str, str | None, str | None] | None
    article: str | None
    raw: str
    start: int
    end: int
    complete: bool = True

    def record(self):
        return asdict(self)


def article_key(value: str | None) -> str | None:
    if value is None:
        return None
    key = re.sub(r"\s+", "", fold(str(value))).rstrip("°º")
    return re.sub(r"(?<=\d)o$", "", key)  # Publisher ordinal 1o., as in A's article IDs.


def references(text: str) -> list[Reference]:
    # NFC keeps Spanish accent folding position-preserving for normal source text.
    text = unicodedata.normalize("NFC", text)
    t = fold(text)
    bodies: list[Reference] = []
    occupied = []
    for m in NORM.finditer(t):
        kind = "decreto" if m[1].startswith("decreto") else "decision" if m[1].startswith("decision") else m[1].replace(" externa", "").replace(" ", "_")
        number = str(int(m[2].replace(".", "")))
        bodies.append(Reference("norm", (kind, number, m[3]), None, text[m.start():m.end()], m.start(), m.end(), m[3] is not None))
        occupied.append(m.span())
    for m in SENTENCE.finditer(t):
        year = m[3]
        if len(year) == 2:
            year = ("20" if int(year) < 50 else "19") + year
        bodies.append(Reference("decision", ("jurisprudencia", f"{m[1].upper()}-{int(m[2])}", year), None, text[m.start():m.end()], m.start(), m.end()))
        occupied.append(m.span())
    for code, variants in CODE_ALIASES.items():
        for alias in sorted(variants, key=len, reverse=True):
            for m in re.finditer(r"(?<!\w)" + re.escape(fold(alias)) + r"(?!\w)", t):
                if any(m.start() < z and m.end() > a for a, z in occupied):
                    continue
                dated = re.match(r"(?:\s+de\s+colombia)?\s+(?:de\s+)?(\d{4})\b", t[m.end():])
                end = m.end() + dated.end() if dated else m.end()
                bodies.append(Reference("code", (code, None, dated[1] if dated else None), None, text[m.start():end], m.start(), end))
                occupied.append((m.start(), end))
    result = list(bodies)
    for m in ARTICLES.finditer(t):
        trailing = re.match(r"\s+(?:(?:a|al|hasta)\s+\d+|bis\b|ter\b|quater\b)", t[m.end():])
        if trailing:
            result.append(Reference("unresolved", None, None, text[m.start():m.end() + trailing.end()],
                                    m.start(), m.end() + trailing.end(), False))
        next_body = next((b for b in sorted(bodies, key=lambda b: b.start) if b.start >= m.end()
                          and b.start - m.end() < 25 and ARTICLE_LINK.fullmatch(t[m.end():b.start])), None)
        previous = next((b for b in sorted(bodies, key=lambda b: -b.end) if b.end <= m.start()
                         and m.start() - b.end < 15 and ARTICLE_LINK.fullmatch(t[b.end:m.start()])), None)
        body = next_body or previous
        for number in re.split(r"\s*(?:,|\by\b|\be\b)\s*", m[2]):
            article = ("transitorio_" if m[1] else "") + article_key(number)
            result.append(Reference("article", body.body if body else None, article,
                                    text[m.start():m.end()], m.start(), m.end(), body.complete if body else True))
    for m in DOCKET.finditer(t):
        result.append(Reference("docket", ("radicado", re.sub(r"[\s-]", "", m[1]).upper(), None), None,
                                text[m.start():m.end()], m.start(), m.end()))
    # Reject obvious citation syntax that the recognizer cannot safely resolve.
    spans = [(r.start, r.end) for r in result]
    marker = r"\b(?:sentencia\s+(?:[a-z]{1,3}[- ]?)?\d+|(?:su|stc|stl|sl|sc|sp|c|t)[- ]?\d+|(?:ley(?:es)?|decreto(?:-ley)?|resolucion|acuerdo|articulos?|arts?\.?|paragrafo|inciso|numeral|radicado|radicacion)\s+(?:(?:n(?:o|ro)?[.°º]*|numero)\s*)?[\divxlcdm]+\b|c\.p\.|c\.c\.)"
    for m in re.finditer(marker, t):
        if not any(a <= m.start() and m.end() <= z for a, z in spans):
            result.append(Reference("unresolved", None, None, text[m.start():m.end()], m.start(), m.end(), False))
    return sorted(result, key=lambda r: (r.start, r.end, r.kind, r.article or ""))


def passage_bodies(passage: dict) -> set[tuple]:
    result = set()
    canonical = passage.get("canonical_body")
    if isinstance(canonical, (tuple, list)) and len(canonical) == 3:
        result.add(tuple(str(v) if v is not None else None for v in canonical))
    # Titles may mention adopting/amending statutes too (Civil Code: Ley 84
    # plus Ley 57). Only the primary norm_number/year can supply a law alias.
    title_refs = [r for r in references(passage.get("norm_name") or "") if r.complete and r.body is not None]
    primary_number, primary_year = passage.get("norm_number"), passage.get("year")
    for ref in title_refs:
        if ref.kind == "norm":
            if primary_number is not None and primary_year is not None:
                if ref.body[1:] == (str(primary_number), str(primary_year)):
                    result.add(ref.body)
            elif not canonical and len({r.body for r in title_refs if r.kind == "norm"}) == 1:
                result.add(ref.body)
        elif ref.kind in {"code", "decision"}:
            if not canonical or ref.body[0] == canonical[0]:
                result.add(ref.body)
    for body in list(result):
        if body[0] in CODE_ALIASES and body[1] is None and primary_year is not None:
            result.add((body[0], None, str(primary_year)))
    return result


def supporting_passages(ref: Reference, passages: list[dict]) -> list[dict]:
    if not ref.complete or ref.kind == "unresolved":
        return []
    if ref.kind == "docket":
        return [p for p in passages if any(r.kind == "docket" and r.body == ref.body for r in references(p["text"]))]
    matched = [p for p in passages if (ref.body is None or ref.body in passage_bodies(p))
               and (ref.article is None or article_key(p.get("article")) == ref.article)]
    if ref.body is None:
        # A bare article cannot borrow the identity of an arbitrary retrieved norm.
        identities = {tuple(p.get("canonical_body") or [p["doc_id"]]) for p in passages}
        if len(identities) != 1:
            return []
    return matched
