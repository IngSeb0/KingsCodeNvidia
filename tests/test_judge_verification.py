from __future__ import annotations

import json
import unittest

from interfaz.batch_io import parse_questions_jsonl
from interfaz.judge_verification import (
    identity_differences,
    official_score,
    parse_run_identity_json,
    parse_submission_rows_jsonl,
    verify_questions_match_identity,
)
from kingscode.reasoning.batch import questions_sha256
from kingscode.reasoning.contracts import Question
from kingscode.reasoning.decoder import abstention_row


class JudgeVerificationInputTests(unittest.TestCase):
    def setUp(self):
        self.question = Question(513, "¿Cuál es la regla aplicable?", "semi_open")
        self.questions_bytes = (json.dumps(self.question.public_record(), ensure_ascii=False) + "\n").encode()
        self.row = abstention_row(self.question, [], "test")

    def test_submission_reader_checks_schema_and_unique_ids(self):
        encoded = (json.dumps(self.row, ensure_ascii=False) + "\n").encode()
        self.assertEqual(parse_submission_rows_jsonl(encoded), {513: self.row})
        with self.assertRaisesRegex(ValueError, "duplicado"):
            parse_submission_rows_jsonl(encoded + encoded)
        with self.assertRaisesRegex(ValueError, "esquema oficial"):
            parse_submission_rows_jsonl(b'{"id":513}\n')

    def test_identity_is_bound_to_public_question_set(self):
        questions = parse_questions_jsonl(self.questions_bytes)
        identity = {"questions_sha256": questions_sha256(questions)}
        self.assertTrue(verify_questions_match_identity(questions, identity))
        identity["questions_sha256"] = "0" * 64
        self.assertFalse(verify_questions_match_identity(questions, identity))

    def test_profile_comparison_ignores_only_input_question_hash(self):
        expected = {"decoder": ["transformers:qwen3-8b", "rev"], "questions_sha256": "sample"}
        actual = {"decoder": ["transformers:qwen3-8b", "rev"], "questions_sha256": "judge-set"}
        self.assertEqual(identity_differences(expected, actual), [])
        actual["decoder"] = ["transformers:other", "rev"]
        self.assertTrue(any("decoder" in difference for difference in identity_differences(expected, actual)))

    def test_identity_and_score_readers_reject_bad_shapes(self):
        self.assertEqual(parse_run_identity_json(b'{"decoder":"x"}'), {"decoder": "x"})
        with self.assertRaisesRegex(ValueError, "identity.json"):
            parse_run_identity_json(b"[]")
        self.assertEqual(official_score({"total_automatico": {"obtenidos": 37.46}}), 37.46)
        self.assertIsNone(official_score({"total_automatic": {}}))


if __name__ == "__main__":
    unittest.main()
