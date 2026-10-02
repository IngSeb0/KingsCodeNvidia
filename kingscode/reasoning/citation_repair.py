"""Repair decoder citations before citation_guard (plan B2). Never raises on content.

Per cited reference in any answer string:
  supported (citation_guard's own rule)           -> keep
  body supported, article not                      -> rewrite to body level (drop the article)
  body unsupported / unresolvable / abbreviation   -> drop the sentence; an emptied
                                                      semi/open required field triggers abstention
Then the official extractor must find, in the kept text, only bodies the evaluator
counts as supported by the first 10 passages; any other sentence is dropped too.

"Body supported" deliberately uses citation_guard's identity rule, not the
evaluator's looser any-mention rule: a body that is only *mentioned* inside
another passage would pass here and then be rejected by the final guard. Relaxing
the guard to the evaluator's rule is T1b and requires Luis's review.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import re

from .citation_builder import _names, body_of, verified
from .guards import reference_support
from .legal import fold, references
from .official import evidence_bodies, official_bodies

SKIP_KEYS = {"id", "formato", "abstencion", "latencia_ms", "pasajes_recuperados", "respuesta_correcta"}
_ABBREVIATIONS = r"(?:arts?|núm|num|no|nro|inc|lit|par|num|sr|sra|dr|dra|c\.p|c\.c|e\.t|c\.n|c\.co|c\.s\.t|c\.g\.p|c\.p\.p)"
_SHIELD = "\x00"


def split_sentences(text: str) -> list[str]:
    """Sentence split that does not cut 'Art. 90', 'C.P.' or '2.2.1.1'."""
    shielded = re.sub(r"(?<=\d)\.(?=\d)", _SHIELD, text)
    shielded = re.sub(r"(?i)\b(" + _ABBREVIATIONS + r")\.", lambda m: m.group(1) + _SHIELD, shielded)
    return [s.replace(_SHIELD, ".") for s in re.split(r"(?<=[.!?])\s+", shielded.strip()) if s.strip()]


def _supported(ref, emitted) -> bool:
    return ref.complete and ref.kind != "unresolved" and bool(reference_support(ref, emitted))


_DETERMINER = {"de la": {"el": "la", "del": "de la", "al": "a la"}, "del": {}, "de": {}}


def _drop_span(text: str, start: int, end: int) -> str:
    """Remove an article span together with the connector that links it to its body.

    'en el artículo 2 de la Ley 1010' -> 'en la Ley 1010'; 'Ley 1010, artículo 2' -> 'Ley 1010'.
    """
    after = re.match(r"\s*(de la|del|de)\s+", text[end:], re.I)
    if after:
        head, tail = text[:start], text[end + after.end():]
        det = re.search(r"\b(el|del|al)\s+$", head, re.I)
        swap = _DETERMINER[after.group(1).lower()].get(det.group(1).lower()) if det else None
        if swap:
            head = head[:det.start()] + swap + " "
        return head + tail
    before = re.search(r"[\s,;:]*$", text[:start])
    return text[:before.start()] + text[end:]


def _rename_to_evidence(sentence: str, refs: list, ref, emitted: list[dict]) -> str | None:
    """Undated code the guard cannot see literally ('Constitución Política') -> the
    name the retrieved passage itself uses, only if that name verifies."""
    if ref.kind not in {"code", "article"} or not ref.body or ref.body[1] is not None:
        return None
    code = ref if ref.kind == "code" else next(
        (r for r in refs if r.kind == "code" and r.body and r.body[0] == ref.body[0]), None)
    if code is None:
        return None
    for passage in emitted:
        if (body_of(passage) or (None,))[0] != ref.body[0]:
            continue
        for name in _names(passage):
            if fold(name) != fold(code.raw) and verified(name, passage):
                renamed = sentence[:code.start] + name + sentence[code.end:]
                revised = references(renamed)
                repaired_target = any(
                    r.kind == ref.kind and r.body and r.body[0] == ref.body[0]
                    and (ref.kind != "article" or r.article == ref.article)
                    and _supported(r, emitted) for r in revised)
                if renamed != sentence and repaired_target:
                    return renamed
    return None


def _repair_sentence(sentence: str, emitted: list[dict], actions: list, field: str) -> str | None:
    for _ in range(20):
        refs = references(sentence)
        pending = [r for r in refs if not _supported(r, emitted)]
        if not pending:
            return sentence
        ref = pending[0]
        renamed = _rename_to_evidence(sentence, refs, ref, emitted)
        if renamed is not None:
            actions.append({"field": field, "action": "renamed_to_evidence_name", "reference": ref.raw})
            sentence = renamed
            continue
        body_ref = replace(ref, kind="norm", article=None) if ref.kind == "article" and ref.body else None
        if body_ref is not None and _supported(body_ref, emitted):
            actions.append({"field": field, "action": "rewritten_to_body", "reference": ref.raw})
            sentence = _drop_span(sentence, ref.start, ref.end)
            continue
        actions.append({"field": field, "action": "suppressed_sentence", "reference": ref.raw})
        return None
    return None


def repair_text(text: str, emitted: list[dict], supported: set, actions: list, field: str) -> str:
    if not text.strip():
        return text
    kept = []
    for sentence in split_sentences(text):
        fixed = _repair_sentence(sentence, emitted, actions, field)
        if fixed is not None and not official_bodies(fixed) <= supported:
            actions.append({"field": field, "action": "suppressed_sentence", "reference": "official_extractor"})
            fixed = None
        if fixed is not None:
            kept.append(re.sub(r"\s{2,}", " ", fixed).strip())
    repaired = " ".join(s for s in kept if s)
    if not repaired:
        # Removing a cited norm from the only sentence can invert or mutilate its
        # legal claim (for example "El Código Civil establece" -> "El establece").
        # Leave the field empty so required fields trigger a controlled abstention.
        actions.append({"field": field, "action": "emptied_after_unsupported_citation"})
        return ""
    return repaired


def count_citations(row: dict) -> int:
    """References in answer strings, counted like citation_guard counts claims."""
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for v in value.values():
                yield from strings(v)
        elif isinstance(value, list):
            for v in value:
                yield from strings(v)
    return sum(len(references(s)) for k, v in row.items() if k not in SKIP_KEYS for s in strings(v))


def repair_citations(row: dict, evidence: list[dict]) -> tuple[dict, dict]:
    """Return a repaired copy of row and a report. Touches only answer strings."""
    fixed = deepcopy(row)
    emitted = evidence[:10]
    supported = evidence_bodies(emitted)
    actions: list[dict] = []
    for key, value in list(fixed.items()):
        if key in SKIP_KEYS:
            continue
        if isinstance(value, str):
            fixed[key] = repair_text(value, emitted, supported, actions, key)
        elif isinstance(value, list):
            fixed[key] = [v for v in (repair_text(x, emitted, supported, actions, key) if isinstance(x, str) else x
                                      for x in value) if v != ""]
        elif isinstance(value, dict):
            fixed[key] = {k: repair_text(v, emitted, supported, actions, f"{key}.{k}") if isinstance(v, str) else v
                          for k, v in value.items()}
    return fixed, {"actions": actions, "changed": fixed != row}
