"""Direct capture transport checks with explicit inert native replies.

These exercise Python custody and refusal behavior. They do not compile Hoon,
authenticate a saved noun, or prove the claimed native digest observations.
"""
import ast
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / 'scripts/ci/home_asset_rehearsal/evidence.py'
SPEC = importlib.util.spec_from_file_location('saved8_direct_evidence', PATH)
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)


class Replies:
    """Closed source-to-reply double; no native process or arbitrary evaluation."""
    def __init__(self, raw):
        self.raw = raw
        self.calls = []
        self.fingerprint = '1' * 64
        self.overrides = {}
        self.seen = {}
        self.rows = {
            **{source: '%.y' for source in E.CONDITIONS.values()},
            E.SUSPENDED: '%.n', E.DESK: '%release-test',
            E.SANITY: '0x73.6176.6564.3868.6578',
            E.ENCODING_CONTROL: '0x73.6176.6564.3868.6578',
            E.FINGERPRINT: '0x' + self.fingerprint,
            E.TOTAL: format(len(raw), ',').replace(',', '.'),
        }
        for index, field in enumerate(E.NOUNS, 1):
            self.rows[E.digest_command(field, self.fingerprint)] = hex(index)
        for offset in range(0, len(raw), E.CHUNK):
            self.rows[E.chunk_command(len(raw), offset, self.fingerprint)] = hex(
                int.from_bytes(raw[offset:offset + E.CHUNK], 'little'))

    def __call__(self, source):
        self.calls.append(source)
        self.seen[source] = self.seen.get(source, 0) + 1
        key = (source, self.seen[source])
        response = self.overrides.get(key, self.rows[source])
        if isinstance(response, BaseException):
            raise response
        return response


class Saved8DirectTests(unittest.TestCase):
    def test_independent_controls_fail_before_saved_projection(self):
        for target, position in ((E.SANITY, 3), (E.ENCODING_CONTROL, 4)):
            for output in ('0x0', '0x1 trailing', '', 'compiler refused', 'x' * 65):
                replies = Replies(b'\x01')
                replies.overrides[target, 1] = output
                with self.subTest(target=target, output=output), self.assertRaises(ValueError):
                    E.collect(replies, 'seed8')
                self.assertEqual(len(replies.calls), position)
                self.assertNotIn(E.FINGERPRINT, replies.calls)
                self.assertFalse(any('%gv' in command for command in replies.calls))
        self.assertEqual(E.SANITY, '0x73.6176.6564.3868.6578')
        self.assertNotIn('%gv', E.ENCODING_CONTROL)
        self.assertNotIn('/+', E.ENCODING_CONTROL)
        self.assertNotEqual(E.SANITY, E.ENCODING_CONTROL)

    def test_full_bytes_zero_padding_and_boundary_chunk_are_retained(self):
        # First chunk ends in zero bytes; the final nonzero byte keeps this a
        # valid minimal-width atom. A minimal-width per-chunk decoder loses data.
        for raw in (b'\x01' + b'\0' * 16383 + b'\x02',
                    b'\0' * (262144 - 1) + b'\x01'):
            replies = Replies(raw)
            actual = E.collect(replies, 'seed8')
            self.assertEqual(actual['data'], raw)
            self.assertEqual(actual['artifact_bytes'], len(raw))
            self.assertEqual(actual['artifact_sha256'], hashlib.sha256(raw).hexdigest())
            self.assertEqual(actual['capture_pin'], hashlib.sha256(
                b'stead.saved8-capture/1\0' + raw.hex().encode()).hexdigest())
            self.assertEqual(actual['vase_fingerprint'], replies.fingerprint)
            self.assertEqual(replies.calls[-3:], [E.SUSPENDED, E.DESK, E.FINGERPRINT])
            self.assertEqual(sum('(cut 3 [' in call for call in replies.calls),
                             (len(raw) + 16383) // 16384)
            self.assertNotIn('data', E.metadata(actual))
        self.assertEqual(E.chunk_bytes(1, 5, 0), b'\x01\0\0\0\0')
        self.assertEqual(E.chunk_bytes(0, 16385, 16384), b'\0')
        self.assertEqual(E.chunk_bytes(256, 16387, 16384), b'\0\x01\0')

    def test_total_digest_chunk_and_final_scope_fail_closed(self):
        raw = b'\x01\0\x02'
        pristine = Replies(raw)
        chunk = E.chunk_command(3, 0, pristine.fingerprint)
        digest_command = E.digest_command('type_pin', pristine.fingerprint)
        mutations = [
            (E.TOTAL, 1, value) for value in
            ('0', '01', '1000', '1.00', '262.145', '-1', '3 trailing', '')
        ] + [
            (digest_command, 1, '0x1' + '0' * 64),
            (digest_command, 1, 'compiler refused'),
            (chunk, 1, '0x1000000'), (chunk, 1, '0x2 trailing'),
            (chunk, 1, '0x0'),  # Whole final zero violates atom byte custody.
            (E.SUSPENDED, 2, '%.y'), (E.DESK, 2, '%base'),
            (E.FINGERPRINT, 2, '0x2'),
        ]
        for command, occurrence, response in mutations:
            replies = Replies(raw)
            replies.overrides[command, occurrence] = response
            with self.subTest(command=command, response=response), self.assertRaises(ValueError):
                E.collect(replies, 'seed8')
        replies = Replies(raw)
        original = TimeoutError('inert partial request')
        replies.overrides[chunk, 1] = original
        with self.assertRaises(TimeoutError) as raised:
            E.collect(replies, 'seed8')
        self.assertIs(raised.exception, original)
        self.assertEqual(replies.calls[-1], chunk)
        with self.assertRaises(ValueError):
            E.collect(replies, 'arbitrary-stage')
        for args in ((True, 1, 0), (0, True, 0), (0, 1, True),
                     (-1, 1, 0), (256, 1, 0), (0, 262145, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                E.chunk_bytes(*args)

    def test_source_domains_and_cold_vs_durable_equality_remain_distinct(self):
        self.assertEqual(E.NOUNS, {
            'type_pin': ('stead.saved8-type/1', 'p.saved'),
            'payload_pin': ('stead.saved8-payload/1', 'q.saved'),
            'durable_pin': ('stead.saved8-durable/1', '[db.team.stored code.stored handoff.stored retired.stored packs.stored external.stored]'),
            **{name + '_pin': ('stead.saved8-tail/1', ('db.team' if name == 'db' else name) + '.stored')
               for name in ('db', 'code', 'handoff', 'retired', 'packs', 'external')},
        })
        # Pins and numeric literals belong to fixed source, not caller Hoon.
        self.assertEqual(E.CONDITIONS['ship'], '=(~zod our)')
        self.assertEqual(E.SUSPENDED, '.^(? %gu /=stead-home=/$)')
        self.assertEqual(E.DESK, '.^(desk %gd /=stead-home=/$)')
        self.assertNotIn('stored', E.FINGERPRINT)
        replies = Replies(b'x')
        replies.overrides[E.CONDITIONS['handoff'], 1] = '%.n'
        replies.overrides[E.CONDITIONS['packs'], 1] = 'syntax error'
        with self.assertRaises(ValueError) as error:
            E.collect(replies, 'seed8')
        self.assertEqual(error.exception.projection_results['handoff'], 'no')
        self.assertEqual(error.exception.projection_results['packs'], 'native-error')
        self.assertEqual(error.exception.projection_results['external'], 'yes')
        self.assertNotIn('!<', E.PREFIX)
        self.assertNotIn('/+', E.PREFIX)
        self.assertEqual(E.grouped(262144), '262.144')
        self.assertEqual(E.grouped(0x123456789, 16), '1.2345.6789')
        fingerprint = '0123456789abcdef' * 4
        for field, (domain, noun) in E.NOUNS.items():
            command = E.digest_command(field, fingerprint)
            self.assertIn('(jam ' + noun + ')', command)
            self.assertIn("=/  domain=@t  '" + domain + "'", command)
            self.assertIn('(mix domain (lsh [3 prefix] text))', command)
            self.assertIn('(sha-256l:sha [length (rev 3 length data)])', command)
            self.assertIn('?>  =(0x123.4567.89ab.cdef.0123.4567.89ab.cdef.0123.4567.89ab.cdef.0123.4567.89ab.cdef (shax packed))', command)
        for field in ('capture_pin', '__import__', '', None):
            with self.assertRaises(ValueError):
                E.digest_command(field, fingerprint)
        before = E.collect(Replies(b'\x01'), 'seed8')
        after = E.collect(Replies(b'\x02'), 'a0-loaded')
        # Claimed equal durable pins are explicit doubles, not native proof.
        self.assertTrue(E.preserved(before, after, complete=False))
        with self.assertRaises(ValueError):
            E.preserved(before, after, complete=True)
        changed = copy.deepcopy(after)
        changed['db_pin'] = 'f' * 64
        with self.assertRaises(ValueError):
            E.preserved(before, changed, complete=False)
        # Inspect exact production source without executing Hoon or decoding a
        # saved vase. This also prevents a future test-only copied source seam.
        tree = ast.parse(PATH.read_bytes())
        collect = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'collect')
        calls = [node for node in ast.walk(collect) if isinstance(node, ast.Call)]
        self.assertFalse(any(isinstance(node.func, ast.Name) and node.func.id in ('command', 'chunk') for node in calls))


if __name__ == '__main__':
    unittest.main()
