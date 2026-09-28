"""Pinned observed diagnostic grammar; these parser checks do not run Hoon."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/ci'),str(ROOT/'scripts/urbit')]
import negative


class CompilerDiagnosticTests(unittest.TestCase):
    def test_actual_pinned_compiler_log_requires_named_failure_and_exact_build_path(self):
        observed=(ROOT/'tests/ci/fixtures/compiler-control-20260928.txt').read_text()
        self.assertTrue(negative.compiler_diagnostic(observed))
        for altered in ('', 'find-fork stead-ci-deliberately-undefined\n',
                observed.replace('-find.stead-ci-deliberately-undefined','-find.unrelated-name'),
                observed.replace('FAILED  /controls/stead-ci-compiler/hoon (build)','FAILED  /controls/other/hoon (build)'),
                observed.replace('FAILED  /controls/stead-ci-compiler/hoon (build)','OK      /controls/stead-ci-compiler/test-ci-compiler'),
                'x'*262145):
            with self.subTest(length=len(altered)):
                self.assertFalse(negative.compiler_diagnostic(altered))
