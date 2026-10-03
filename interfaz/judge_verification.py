"""Input validation and exact-response comparison for the judge-ID workflow."""
from __future__ import annotations

import json

from kingscode.reasoning.guards import validate_submission

MAX_REFERENCE_BYTES = 64 * 1024 * 1024


def parse_submission_rows_jsonl(payload: bytes) -> dict[int, dict]:
    """Read a frozen official submission, rejecting malformed and duplicate ids."""
    if not isinstance(payload, bytes):
        raise TypeError("El archivo de entrega debe leerse como bytes")
    if len(payload) > MAX_REFERENCE_BYTES:
        raise ValueError("La entrega supera el límite de 64 MB")
    try:
        content = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("La entrega debe estar codificada en UTF-8") from exc

    rows: dict[int, dict] = {}
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Línea {line_number}: JSON inválido ({exc.msg})") from exc
        if not isinstance(row, dict):
            raise ValueError(f"Línea {line_number}: cada registro debe ser un objeto JSON")
        try:
            validate_submission(row)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Línea {line_number}: respuesta incompatible con el esquema oficial ({exc})") from exc
        question_id = row["id"]
        if type(question_id) is not int:
            raise ValueError(f"Línea {line_number}: el id debe ser entero")
        if question_id in rows:
            raise ValueError(f"Línea {line_number}: el id {question_id} está duplicado")
        rows[question_id] = row
    if not rows:
        raise ValueError("La entrega no contiene respuestas")
    return rows


def parse_run_identity_json(payload: bytes) -> dict:
    if not isinstance(payload, bytes):
        raise TypeError("identity.json debe leerse como bytes")
    if len(payload) > 1024 * 1024:
        raise ValueError("identity.json supera el límite de 1 MB")
    try:
        value = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("identity.json no es JSON UTF-8 válido") from exc
    if not isinstance(value, dict):
        raise ValueError("identity.json debe contener un objeto JSON")
    return value


def identity_differences(expected: dict, actual: dict) -> list[str]:
    """Compare recorded pipeline settings, ignoring the input-specific question hash."""
    differences = []

    def visit(path: str, left, right):
        if isinstance(left, dict):
            if not isinstance(right, dict):
                differences.append(f"{path}: falta el objeto de configuración")
                return
            for key, value in left.items():
                if path == "identity" and key == "questions_sha256":
                    continue
                visit(f"{path}.{key}", value, right.get(key, _MISSING))
            return
        if right is _MISSING:
            differences.append(f"{path}: el pipeline actual no registra este ajuste")
        elif left != right:
            differences.append(f"{path}: snapshot={left!r}; actual={right!r}")

    _MISSING = object()
    visit("identity", expected, actual)
    return differences


def verify_questions_match_identity(questions, identity: dict) -> bool:
    """Confirm that identity.json belongs to the uploaded public question set."""
    from kingscode.reasoning.batch import questions_sha256

    expected_hash = identity.get("questions_sha256")
    return bool(expected_hash) and expected_hash == questions_sha256(questions)


def official_score(report: dict) -> float | None:
    """Read the evaluator total across the two report key spellings in the repo."""
    if not isinstance(report, dict):
        return None
    total = report.get("total_automatic") or report.get("total_automatico") or {}
    if not isinstance(total, dict):
        return None
    value = total.get("obtenidos")
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None
