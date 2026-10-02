import copy
import unittest
from src.calculator import number, quoted_numbers, validate_and_calculate
from src.data import chunks_from_record, source_document
from src.evaluation import correct, summarize
from src.pipeline import answer
from src.retrieval import bm25, expand_context, retrieve


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.chunks = [{"id": "table_1", "text": "Revenue 2024: 120; Revenue 2023: 100"}]
        self.payload = {"status": "answer", "kind": "percent", "unit": "%",
            "operands": [{"value": "120", "evidence_id": "table_1", "quote": "2024: 120"},
                         {"value": "100", "evidence_id": "table_1", "quote": "2023: 100"}],
            "steps": [{"op": "subtract", "args": ["n0", "n1"]},
                      {"op": "divide", "args": ["s0", "n1"]},
                      {"op": "multiply", "args": ["s1", "const_100"]}]}

    def test_growth_and_percent_scoring(self):
        result = validate_and_calculate(self.payload, self.chunks)
        self.assertEqual(number(result["value"]), 20)
        self.assertTrue(correct(result, {"exe_ans": .2}))
        result["kind"] = "number"
        self.assertFalse(correct(result, {"exe_ans": .2}))

    def test_hallucinated_reference_and_number_rejected(self):
        for field, value in [("evidence_id", "table_999"), ("quote", "made up"), ("value", "999")]:
            payload = copy.deepcopy(self.payload)
            payload["operands"][0][field] = value
            with self.assertRaises(ValueError):
                validate_and_calculate(payload, self.chunks)

    def test_unsafe_operation_and_forward_reference(self):
        for step in [{"op": "exec", "args": ["n0", "n1"]},
                     {"op": "add", "args": ["s0", "n1"]}]:
            payload = copy.deepcopy(self.payload)
            payload["steps"] = [step]
            with self.assertRaises(ValueError):
                validate_and_calculate(payload, self.chunks)

    def test_zero_denominator(self):
        payload = copy.deepcopy(self.payload)
        payload["steps"] = [{"op": "subtract", "args": ["n1", "n1"]},
                            {"op": "divide", "args": ["n0", "s0"]}]
        with self.assertRaisesRegex(ValueError, "zero"):
            validate_and_calculate(payload, self.chunks)

    def test_number_formats_and_nonfinite(self):
        self.assertEqual(number("(1,200)"), -1200)
        self.assertEqual(number("25%"), number("0.25"))
        for bad in ["NaN", "Infinity", True, "__import__('os')"]:
            with self.assertRaises(ValueError):
                number(bad)

    def test_quotes_keep_negative_and_percent_values(self):
        self.assertIn(number("-170"), quoted_numbers("2015 total: $ -170 ( 170 )"))
        self.assertNotIn(number("170"), quoted_numbers("2015 total: $ -170 ( 170 )"))
        self.assertIn(number("2.50%"), quoted_numbers("2018: 2.50% ( 2.50 % )"))
        self.assertIn(number("(1,200)"), quoted_numbers("Prior: (1,200)"))

    def test_context_preserves_separate_citable_ids(self):
        chunks = [
            {"id": "text_0", "text": "related to non-US"},
            {"id": "text_1", "text": "pension plan contributions were 160"},
            {"id": "text_2", "text": "postretirement contributions were 72"},
            {"id": "table_0", "text": "years 2024 and 2023"},
            {"id": "table_1", "text": "cabinets 2024 2467"},
            {"id": "table_2", "text": "plumbing 2024 1720"},
            {"id": "table_3", "text": "doors 2024 503"},
        ]
        evidence, added = expand_context(chunks, [chunks[1], chunks[4]])
        ids = {c["id"] for c in evidence}
        self.assertEqual(ids, {c["id"] for c in chunks})
        self.assertEqual(added["text_0"], "text_1")
        self.assertEqual(added["table_3"], "table_1")

    def test_five_core_chunks_and_fragment_filter(self):
        chunks = [{"id": "text_0", "text": "cabinets."}] + [
            {"id": f"table_{i}", "text": f"cabinets 2024 item {i}"} for i in range(6)]
        found = retrieve("cabinets", chunks, "bm25", 5)
        self.assertEqual(len(found), 5)
        self.assertNotIn("text_0", {c["id"] for c in found})

    def test_no_label_leak_and_stable_ids(self):
        record = {"id": "example", "pre_text": [".", "source sentence"],
                  "post_text": ["last sentence"], "table": [["item", "2024"], ["sales", "10"]],
                  "qa": {"answer": "SECRET", "gold_inds": {"text_1": "SECRET"}},
                  "model_input": "SECRET", "text_retrieved": "SECRET"}
        doc = source_document(record)
        self.assertNotIn("SECRET", str(doc))
        self.assertEqual([c["id"] for c in doc["chunks"]], ["text_1", "text_2", "table_0", "table_1"])
        self.assertIn("2024: 10", doc["chunks"][-1]["text"])

    def test_pipeline_with_stub_is_explicitly_local_test(self):
        def fake(question, evidence):
            return self.payload, {"model": "TEST-STUB", "cost_usd": 0}
        result = answer("growth", {"id": "fixture", "chunks": self.chunks}, "full", generator=fake)
        self.assertEqual(result["status"], "answer")
        self.assertEqual(result["model"], "TEST-STUB")

    def test_missing_evidence_never_calls_model(self):
        def fail(*args):
            self.fail("Model must not be called")
        result = answer("growth", {"id": "fixture", "chunks": []}, "full", generator=fail)
        self.assertEqual(result["status"], "abstain")

    def test_bm25_and_missing_cost(self):
        chunks = self.chunks + [{"id": "text_1", "text": "Employee benefits policy"}]
        self.assertEqual(bm25("revenue", chunks)[0]["id"], "table_1")
        summary = summarize([{"status": "error", "latency_seconds": 1, "correct": False}])
        self.assertEqual(summary["cost_missing_rows"], 1)
        self.assertEqual(summary["accuracy"], 0)


if __name__ == "__main__":
    unittest.main()
