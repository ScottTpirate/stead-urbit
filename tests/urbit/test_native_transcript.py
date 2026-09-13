"""Real temporary-file evidence bounds; no native runtime."""
import gzip
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/urbit'))
from native_transcript import Transcript, RuntimeLogs


class TranscriptTests(unittest.TestCase):
    def test_exact_record_and_final_hashes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'raw.jsonl.gz'
            transcript = Transcript(path)
            source = {'unicode': '雪', 'raw': 'x' * 70000, 'native': {'status': 'rejected'}}
            first = transcript.append(source)
            final = transcript.close()
            raw = gzip.decompress(path.read_bytes())
            self.assertEqual(source, json.loads(raw))
            self.assertEqual(first['record_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(final['uncompressed_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(final['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertEqual(final, transcript.close())
            with self.assertRaises(ValueError):
                transcript.append({})

    def test_maximum_bounded_failed_exchange_is_retained(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'raw.gz'
            transcript = Transcript(path)
            record = {'received_frame_hex': 'ab' * 1_000_005,
                      'encoded_frame_hex': 'cd' * 1_000_000,
                      'decoded_hex': 'ef' * 1_000_000,
                      'encode_stderr': '\0' * 1_000_000,
                      'decode_stderr': '\0' * 1_000_000}
            reference = transcript.append(record)
            self.assertGreater(reference['record_bytes'], 16 * 1024 * 1024)
            self.assertEqual(transcript.close()['records'], 1)
            self.assertEqual(json.loads(gzip.decompress(path.read_bytes())), record)

    def test_limit_failure_preserves_preceding_evidence(self):
        for limits in ({'line_limit': 4}, {'total_limit': 4}):
            with self.subTest(limits=limits), tempfile.TemporaryDirectory() as root:
                path = Path(root) / 'raw.jsonl.gz'
                transcript = Transcript(path, **limits)
                transcript.append({})
                with self.assertRaises(ValueError):
                    transcript.append({'too': 'large'})
                self.assertEqual(transcript.close()['records'], 1)
                self.assertEqual(gzip.decompress(path.read_bytes()), b'{}\n')

    def test_cannot_overwrite_previous_run(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'raw.jsonl.gz'
            path.write_bytes(b'previous evidence')
            with self.assertRaises(FileExistsError):
                Transcript(path)
            self.assertEqual(path.read_bytes(), b'previous evidence')

    def test_actual_log_delta_retains_mark_error(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'bus.log'
            path.write_bytes(b'old ignored diagnostic\n')
            transcript = Transcript(Path(root) / 'raw.gz')
            reader = RuntimeLogs(root, transcript, ships=('bus',))
            cursor = reader()['cursor']
            with path.open('ab') as log:
                log.write(b'normal\nneed-mark stead-result-2\n')
            result = reader(cursor)
            self.assertEqual(len(result['errors']), 1)
            self.assertIn('need-mark', result['errors'][0]['text'])
            self.assertEqual(result['segments'][0]['sha256'], hashlib.sha256(b'normal\nneed-mark stead-result-2\n').hexdigest())
            self.assertEqual(transcript.close()['records'], 1)

    def test_missing_or_truncated_log_cannot_mean_zero_errors(self):
        with tempfile.TemporaryDirectory() as root:
            transcript = Transcript(Path(root) / 'raw.gz')
            reader = RuntimeLogs(root, transcript, ships=('bus',))
            with self.assertRaises(FileNotFoundError):
                reader()
            path = Path(root) / 'bus.log'
            path.write_bytes(b'prior')
            cursor = reader()['cursor']
            path.write_bytes(b'')
            with self.assertRaises(ValueError):
                reader(cursor)
            transcript.close()

    def test_split_diagnostic_and_copy_truncate_regrow(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'bus.log'
            path.write_bytes(b'previous\n')
            transcript = Transcript(Path(root) / 'raw.gz')
            reader = RuntimeLogs(root, transcript, ships=('bus',))
            cursor = reader()['cursor']
            with path.open('ab') as log:
                log.write(b'need-')
            first = reader(cursor)
            with path.open('ab') as log:
                log.write(b'mark stead-result-2\n')
            second = reader(first['cursor'])
            self.assertEqual(len(second['errors']), 1)
            path.write_bytes(b'a different prefix' + b'x' * path.stat().st_size)
            with self.assertRaisesRegex(ValueError, 'prefix changed'):
                reader(second['cursor'])
            transcript.close()
