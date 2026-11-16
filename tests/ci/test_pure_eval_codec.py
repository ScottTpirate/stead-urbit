"""Twelve authored byte-only boundaries; none claim evaluator/native execution.

The fixture sources are retained exact reviewed input, not generated fake test
results. Output samples below are explicitly authored parser cases, except the
source-pinned historical compiler control spelling. No process or socket runs.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ci/pure_eval"))
import codec

FIXTURES = ROOT / "fixtures/pure-eval"


class PureEvalCodecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.composition = (FIXTURES / "composition.json").read_bytes()
        cls.document = json.loads(cls.composition)
        cls.files = {path: (FIXTURES / path).read_bytes() for path in cls.document["sources"]}
        cls.files[codec.HELPER_PATH] = (FIXTURES / codec.HELPER_PATH).read_bytes()
        cls.fixed = codec.jobs(cls.files, cls.composition)

    def rows(self, job, counts=None, *, null_tail=False):
        names = job["arms"] or ("failure-control",)
        counts = counts if counts is not None else (0,) * len(names)
        inside = "\n".join(f"[~.{name} ~.{format(count, ',').replace(',', '.')}]" for name, count in zip(names, counts))
        return (("[" + inside + " ~]") if null_tail else ("~[" + inside + "]")).encode()

    def test_exact_fixed_jobs_and_reviewed_composed_sources(self):
        self.assertEqual(tuple(job["label"] for job in self.fixed),
                         ("compiler-control", "failing-tang-control", "catalog", "import", "authority", "store"))
        self.assertEqual(sum(len(job["arms"]) for job in self.fixed), 26)
        self.assertEqual(tuple(job["timeout_seconds"] for job in self.fixed), (15, 15, 85, 85, 85, 85))
        for job, suite in zip(self.fixed[2:], self.document["composition"]["suites"]):
            self.assertEqual(len(job["source"]), suite["composed_source"]["bytes"])
            self.assertEqual(hashlib.sha256(job["source"]).hexdigest(), suite["composed_source"]["sha256"])
            self.assertEqual(job["arms"], tuple(suite["arms"]))
            self.assertLessEqual(len(job["source"]), 1048576)
        self.assertEqual(self.fixed[0]["source"], b"(invalid-unterminated\n")
        self.assertEqual(hashlib.sha256(self.fixed[1]["source"]).hexdigest(),
                         "6ccdf445296a66cac869b95ff3a7d068421309cf7b541e2cf5adbc79589e0639")

    def test_exact_input_inventory_and_every_source_pin(self):
        for path in self.files:
            with self.subTest(path=path):
                changed = dict(self.files)
                changed[path] += b"\n"
                with self.assertRaises(ValueError):
                    codec.jobs(changed, self.composition)
        for changed in (dict(list(self.files.items())[1:]), {**self.files, "other.hoon": b"0"}):
            with self.assertRaises(ValueError):
                codec.jobs(changed, self.composition)
        with self.assertRaises(ValueError):
            codec.jobs({**self.files, codec.HELPER_PATH: "not bytes"}, self.composition)

    def test_composition_closure_order_mapping_and_inventory_are_pinned(self):
        edits = []
        changed = copy.deepcopy(self.document)
        changed["composition"]["suites"][0]["transitive_library_order"].reverse()
        edits.append(changed)
        changed = copy.deepcopy(self.document)
        changed["composition"]["suites"][0]["source_offsets"][1]["source_end_byte"] -= 1
        edits.append(changed)
        changed = copy.deepcopy(self.document)
        changed["composition"]["suites"][0]["arms"].reverse()
        edits.append(changed)
        changed = copy.deepcopy(self.document)
        changed["composition"]["exact_import_headers"]["native/core/desk/lib/stead-actor.hoon"] = ""
        edits.append(changed)
        for changed in edits:
            with self.assertRaises(ValueError):
                codec.jobs(self.files, json.dumps(changed).encode())
        with self.assertRaises(ValueError):
            codec.jobs(self.files, self.composition + b"\n")

    def test_per_suite_closure_has_no_unrelated_library_and_preserves_body(self):
        all_libraries = self.document["composition"]["library_order"]
        for job, suite in zip(self.fixed[2:], self.document["composition"]["suites"]):
            selected = suite["transitive_library_order"]
            for name in all_libraries:
                binding = f"=/  {name}\n".encode()
                self.assertEqual(binding in job["source"], name in selected)
            original = self.files[suite["path"]]
            body = original.replace(suite["import_header"].encode(), b"", 1)
            self.assertIn(body, job["source"])
            self.assertNotIn(suite["import_header"].encode(), job["source"])
        self.assertNotIn(b"=/  stead-code-home\n", self.fixed[2]["source"])
        self.assertIn(b"=/  stead-code-home\n", self.fixed[5]["source"])

    def test_controls_require_all_exact_observations(self):
        compiler, tang = self.fixed[:2]
        observed = codec.observe(compiler, 0, codec.COMPILER_STDOUT.encode(), codec.EXIT_STDERR.encode())
        self.assertEqual((observed["status"], observed["arms"], observed["compiler_failure"]), ("pass", (), False))
        observed = codec.observe(tang, 0, self.rows(tang, (3,)), codec.BOOT.encode())
        self.assertEqual((observed["status"], observed["arms"]), ("pass", ()))
        for out, err in [(codec.COMPILER_STDOUT.encode(), codec.BOOT.encode()),
                         (b"syntax error", codec.EXIT_STDERR.encode()),
                         (b"/eval\n{1 23}\nsyntax error", codec.EXIT_STDERR.encode())]:
            with self.assertRaises(ValueError):
                codec.observe(compiler, 0, out, err)
        for out, err in [(self.rows(tang, (0,)), codec.BOOT.encode()),
                         (self.rows(tang, (3,)), codec.EXIT_STDERR.encode())]:
            with self.assertRaises(ValueError):
                codec.observe(tang, 0, out, err)

    def test_complete_rows_both_forms_and_raw_hashes(self):
        job = self.fixed[2]
        for null_tail in (False, True):
            raw = b"\x1b[32m" + self.rows(job, null_tail=null_tail).replace(b"\n", b"\r\n") + b"\x1b[0m\r\n"
            err = codec.BOOT.replace("\n", "\r\n").encode() + b"\n"
            result = codec.observe(job, 0, raw, err)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(tuple(row["name"] for row in result["arms"]), job["arms"])
            self.assertTrue(all(type(row["tang_length"]) is int and type(row["passed"]) is bool for row in result["arms"]))
            self.assertEqual((result["stdout_bytes"], result["stdout_sha256"]),
                             (len(raw), hashlib.sha256(raw).hexdigest()))
            self.assertEqual((result["stderr_bytes"], result["stderr_sha256"]),
                             (len(err), hashlib.sha256(err).hexdigest()))

    def test_failed_tang_preserves_all_real_arm_rows(self):
        job = self.fixed[4]
        counts = (0, 3, 0, 0, 9, 0, 0, 0)
        result = codec.observe(job, 0, self.rows(job, counts), codec.BOOT.encode())
        self.assertEqual(result["status"], "fail")
        self.assertFalse(result["compiler_failure"])
        self.assertEqual(tuple(row["tang_length"] for row in result["arms"]), counts)
        self.assertEqual(tuple(row["passed"] for row in result["arms"]), tuple(n == 0 for n in counts))

    def test_missing_extra_reordered_duplicate_and_second_noun_refuse(self):
        job = self.fixed[2]
        correct = self.rows(job)
        variants = [correct[:-1], correct + b"\n0", b"diagnostic\n" + correct,
                    correct.replace(job["arms"][0].encode(), job["arms"][1].encode(), 1),
                    correct.replace(b"~.0", b"~.01", 1), correct.replace(b"~.0", b"~.-1", 1)]
        fake = {**job, "arms": tuple(reversed(job["arms"]))}
        variants.append(self.rows(fake))
        for raw in variants:
            with self.subTest(raw=raw[:70]), self.assertRaises(ValueError):
                codec.observe(job, 0, raw, codec.BOOT.encode())

    def test_completed_exit_is_failed_evaluator_not_arm_success(self):
        job = self.fixed[3]
        trace = b"/eval\n{10 20}\nsynthetic completed evaluator trace"
        result = codec.observe(job, 0, trace, codec.EXIT_STDERR.encode())
        self.assertEqual((result["status"], result["arms"], result["compiler_failure"]), ("fail", (), True))
        for err in (b"eval: bail: %exit", (codec.EXIT_STDERR + "\nextra").encode(),
                    codec.EXIT_STDERR.replace("%exit", "%fail").encode(),
                    codec.EXIT_STDERR.replace("4ce68411", "00000000").encode()):
            with self.assertRaises(ValueError):
                codec.observe(job, 0, trace, err)
        with self.assertRaises(ValueError):
            codec.observe(job, 0, b" \n", codec.EXIT_STDERR.encode())
        for control in (b"\x7f", b"\xc2\x80", b"\xc2\x9b", b"\xc2\x9f"):
            with self.subTest(control=control), self.assertRaises(ValueError):
                codec.observe(job, 0, trace + control, codec.EXIT_STDERR.encode())
        with self.assertRaises(ValueError):
            codec.observe(job, 0, trace, codec.BOOT.encode())

    def test_job_identity_exit_types_and_observation_shape(self):
        job = self.fixed[2]
        for code in (False, True, 0.0, "0", 1, -9):
            with self.assertRaises(ValueError):
                codec.observe(job, code, self.rows(job), codec.BOOT.encode())
        for field, value in (("source", job["source"] + b"\n"), ("source_sha256", "0" * 64),
                             ("label", "other"), ("kind", "compiler-control"),
                             ("timeout_seconds", 85.0), ("arms", list(job["arms"]))):
            with self.assertRaises(ValueError):
                codec.observe({**job, field: value}, 0, self.rows(job), codec.BOOT.encode())
        with self.assertRaises(ValueError):
            codec.observe({**job, "passed": True}, 0, self.rows(job), codec.BOOT.encode())
        self.assertEqual(set(codec.observe(job, 0, self.rows(job), codec.BOOT.encode())),
                         {"label", "kind", "status", "exit_code", "arms", "stdout_sha256", "stdout_bytes",
                          "stderr_sha256", "stderr_bytes", "compiler_failure"})

    def test_output_bounds_utf8_and_unknown_terminal_controls(self):
        job = self.fixed[2]
        valid = self.rows(job)
        invalid = (b"", b"\xff", valid + b"\0", valid + b"\r", b"\x1b[2J" + valid,
                   b"\x1b[" + b"1" * 33 + b"m" + valid, b"x" * 1000001)
        for raw in invalid:
            with self.assertRaises(ValueError):
                codec.observe(job, 0, raw, codec.BOOT.encode())
        for err in (b"", b"x" * 1000001, codec.BOOT.encode() + b"\0"):
            with self.assertRaises(ValueError):
                codec.observe(job, 0, valid, err)
        with self.assertRaises(ValueError):
            codec.observe(job, 0, valid.decode(), codec.BOOT.encode())

    def test_tang_count_exact_bound_and_ascii_only_row_whitespace(self):
        job = self.fixed[2]
        for count in (999, 1000, 1000000):
            raw = self.rows(job, (count, 0, 0, 0, 0, 0))
            result = codec.observe(job, 0, raw, codec.BOOT.encode())
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["arms"][0]["tang_length"], count)
        valid = self.rows(job, (1000000, 0, 0, 0, 0, 0))
        for bad in (b"1000", b"01", b"1.00", b"1.000.001", b"1.000.000.000", b"1000000"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                codec.observe(job, 0, valid.replace(b"1.000.000", bad), codec.BOOT.encode())
        with self.assertRaises(ValueError):
            codec.observe(job, 0, valid.replace(b" ~.", "\u00a0~.".encode(), 1), codec.BOOT.encode())
