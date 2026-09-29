"""Host replay of one retained native diagnostic; no native execution here."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/sdk_native'), str(ROOT / 'scripts/urbit')]
SPEC = importlib.util.spec_from_file_location('sdk_consumer_import', ROOT / 'scripts/sdk_native/consumer.py')
CONSUMER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONSUMER)
OBSERVED = json.loads((ROOT / 'docs/urbit/evidence/2026-09-29/phase2-preparation/sdk-import-diagnostic.json').read_text())
RESPONSE = OBSERVED['observed']['generator_response']
TRACE = OBSERVED['observed']['missing_dependency_line'].encode() + b'\r\n'


class SDKImportTests(unittest.TestCase):
    def test_retained_pinned_clay_failure(self):
        CONSUMER.verify_private_import(RESPONSE, TRACE)

    def test_generic_failure_timeout_or_other_generator_cannot_pass(self):
        for response in ('%generator-build-fail\n', 'timeout', '%sdk-import-control-compiled\n',
                         RESPONSE.replace('stead-sdk-private', 'another-generator'),
                         RESPONSE + 'unexpected extra output\n'):
            with self.subTest(response=response), self.assertRaises(ValueError):
                CONSUMER.verify_private_import(response, TRACE)

    def test_absent_wrong_or_only_mentioned_dependency_cannot_pass(self):
        for trace in (b'', b'file-not-found\nstead-core\n',
                      TRACE.replace(b'stead-core', b'stead-codec'),
                      b'quoted: ' + TRACE, TRACE.replace(b'/hoon', b'/hoon-extra')):
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                CONSUMER.verify_private_import(RESPONSE, trace)

    def test_oversized_trace_cannot_pass(self):
        with self.assertRaises(ValueError):
            CONSUMER.verify_private_import(RESPONSE, TRACE + b' ' * 262144)


if __name__ == '__main__':
    unittest.main()
