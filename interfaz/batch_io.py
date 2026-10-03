"""Safe JSONL input and output helpers for the Streamlit interface."""
from __future__ import annotations

import json

from kingscode.reasoning.contracts import Question, public_question
from kingscode.reasoning.guards import validate_submission

MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_QUESTIONS = 2000


def parse_questions_jsonl(payload: bytes) -> list[Question]:
    """Parse a public question JSONL file and discard non-contract fields.

    Projection through ``public_question`` is deliberate: expected answers,
    legal_basis and other extra fields never cross into the generation path.
    """
    if not isinstance(payload, bytes):
        raise TypeError("El archivo debe leerse como bytes")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise ValueError(f"El archivo supera el límite de {MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    try:
        content = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("El archivo debe estar codificado en UTF-8") from exc

    questions: list[Question] = []
    seen_ids: set[int] = set()
    for line_number, line in enumerate(content.splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Línea {line_number}: JSON inválido ({exc.msg})") from exc
        if not isinstance(record, dict):
            raise ValueError(f"Línea {line_number}: cada registro debe ser un objeto JSON")
        try:
            question = public_question(record)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Línea {line_number}: pregunta incompatible con el formato oficial ({exc})") from exc
        if not question.text.strip():
            raise ValueError(f"Línea {line_number}: la pregunta está vacía")
        if question.format == "multiple_choice":
            missing = sorted(set("ABCD") - set(question.options))
            blank = sorted(letter for letter in "ABCD" if not question.options.get(letter, "").strip())
            if missing or blank:
                letters = sorted(set(missing + blank))
                raise ValueError(f"Línea {line_number}: faltan opciones completas para {', '.join(letters)}")
        if question.id in seen_ids:
            raise ValueError(f"Línea {line_number}: el id {question.id} está duplicado")
        seen_ids.add(question.id)
        questions.append(question)
        if len(questions) > MAX_QUESTIONS:
            raise ValueError(f"El lote supera el máximo de {MAX_QUESTIONS} preguntas")

    if not questions:
        raise ValueError("El archivo no contiene preguntas")
    return questions


def submissions_jsonl(rows: list[dict]) -> bytes:
    """Validate, sort and serialize official submission rows deterministically."""
    ids = [row.get("id") for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("La entrega contiene ids duplicados")
    for row in rows:
        validate_submission(row)
    ordered = sorted(rows, key=lambda row: row["id"])
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in ordered)
    return text.encode("utf-8")
