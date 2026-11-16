"""Authored closed parser-coordinate cases; no native/compiler execution."""
import json
import unittest

import worker_failure as failure


PATH = 'native/core/desk/lib/stead-product-owner.hoon'
REFERENCE = b'/lib/stead-product-owner/hoon'
SOURCES = {PATH: b'ab\ncdef\n'}


class ParserPositionTests(unittest.TestCase):
    def test_scan_position_is_explicit_module_association_not_source_span(self):
        raw = REFERENCE + b'\n{2 4}\nsyntax error\n'
        value = failure.parser_positions(raw, SOURCES)
        self.assertEqual(value['association'], 'sole-referenced-admitted-module')
        self.assertEqual(value['path'], PATH)
        self.assertEqual(value['positions'], [{'line': 2, 'column': 4}])
        self.assertEqual(value['position_patterns'], 1)
        self.assertEqual(value['bounds_rejected'], 0)
        self.assertEqual(failure.source_spans(raw, SOURCES)['locations'], [])

    def test_reversed_wrapped_and_dotted_scan_positions_use_real_bounds(self):
        source = {PATH: b'\n' * 1000 + b'x' * 1001}
        raw = b'syntax error\n{1.001\n\t1.002}\n' + REFERENCE
        self.assertEqual(failure.parser_positions(raw, source)['positions'],
                         [{'line': 1001, 'column': 1002}])
        raw = REFERENCE + b'\n{3 1}\nsyntax error'
        self.assertEqual(failure.parser_positions(raw, SOURCES)['positions'],
                         [{'line': 3, 'column': 1}])

    def test_zero_past_end_columns_and_line_bounds_are_refused(self):
        raw = REFERENCE + b'\nsyntax error\n{0 1} {1 0} {4 1} {1 4} {3 2}'
        value = failure.parser_positions(raw, SOURCES)
        self.assertEqual(value['positions'], [])
        self.assertEqual(value['position_patterns'], 5)
        self.assertEqual(value['bounds_rejected'], 5)

    def test_two_modules_unknown_module_and_absent_source_never_guess_path(self):
        for extra, sources in [(b'\n/lib/another/hoon', SOURCES),
                               (b'\n/app/stead-home/hoon', SOURCES),
                               (b'\n/gen/stead-build-probe/hoon', SOURCES),
                               (b'\n/mar/json/hoon', SOURCES),
                               (b'\n/ted/stead-product-check/hoon', SOURCES),
                               (b'', {}), (b'', None)]:
            with self.subTest(extra=extra, admitted=sources is not None):
                raw = REFERENCE + extra + b'\nsyntax error\n{1 1}'
                value = failure.parser_positions(raw, sources)
                self.assertEqual(value['association'], 'unresolved')
                self.assertIsNone(value['path'])
                self.assertEqual(value['positions'], [])
        raw = REFERENCE.replace(b'owner', b'unknown') + b'\nsyntax error\n{1 1}'
        self.assertIsNone(failure.parser_positions(raw, SOURCES)['path'])

    def test_marker_and_number_lookalikes_do_not_enter_positions(self):
        for text in (b'{1 1}', b'{1 1}\nnot-syntax error', b'{1 1}\nsyntax error-extra'):
            with self.subTest(text=text):
                self.assertEqual(failure.parser_positions(REFERENCE + b'\n' + text, SOURCES)['positions'], [])
        for text in (b'{{1 1}}', b'x{1 1}', b'{1 1}x', b'{1.01 1}', b'{1,1}',
                     b'{1 -1}', b'{1 1.}', b'{1 ' + b' ' * 256 + b'1}'):
            with self.subTest(text=text):
                self.assertEqual(failure.parser_positions(REFERENCE + b'\nsyntax error\n' + text,
                                                         SOURCES)['position_patterns'], 0)

    def test_tail_distinct_positions_and_repeated_module_references_are_bounded(self):
        source = {PATH: b'x' * 100}
        raw = REFERENCE + b'\n' + REFERENCE + b'\nsyntax error\n' + b' '.join(
            ('{1 %d}' % number).encode() for number in [*range(1, 21), 20, 1])
        value = failure.parser_positions(raw, source)
        self.assertTrue(value['truncated'])
        self.assertEqual(len(value['positions']), 16)
        self.assertEqual(value['positions'][-1], {'line': 1, 'column': 1})
        self.assertNotIn({'line': 1, 'column': 2}, value['positions'])

    def test_projection_counts_and_raw_input_bounds_are_closed(self):
        raw = REFERENCE + b'\nsyntax error\n' + b'{1 1} ' * 4097
        value = failure.parser_positions(raw, SOURCES)
        self.assertEqual(value['position_patterns'], 4096)
        self.assertTrue(value['counts_truncated'])
        self.assertEqual(value['positions'], [{'line': 1, 'column': 1}])
        with self.assertRaises(ValueError): failure.parser_positions(b'x' * 262145, SOURCES)
        with self.assertRaises(ValueError): failure.parser_positions(raw, {PATH: b'x' * (4 * 1024**2 + 1)})

    def test_log_and_result_positions_remain_separate_without_raw_text(self):
        secret = b'PRIVATE-NATIVE-TEXT-DO-NOT-EXPORT'
        log = REFERENCE + b'\n{2 3}\nsyntax error\n' + secret
        terminal = (REFERENCE + b'\nsyntax error\n{1 2}\n' + secret).decode()
        native = {'commands': [{'ship': 'zod', 'dojo': '+stead-build-probe', 'result': terminal}],
                  'build_probe_transcripts': [{'ship': 'zod', 'dojo': '+stead-build-probe',
                      'log_offset': 1, 'log_bytes': len(log), 'log_hex': log.hex()}]}
        value = failure.build_probe_observations(native, SOURCES)[0]
        self.assertEqual(value['parser_positions']['positions'], [{'line': 2, 'column': 3}])
        self.assertEqual(value['result_observation']['parser_positions']['positions'],
                         [{'line': 1, 'column': 2}])
        encoded = json.dumps(value)
        self.assertNotIn(secret.decode(), encoded)
        self.assertNotIn(log.hex(), encoded)
        self.assertNotIn(terminal, encoded)


class ClayParserPositionTests(unittest.TestCase):
    def test_embedded_path_binds_position_without_sole_module_guess(self):
        raw = b'/app/stead-home/hoon\nsyntax error at [2 4] in ' + REFERENCE
        value = failure.clay_parser_locations(raw, SOURCES)
        self.assertEqual(value['locations'], [{'path': PATH, 'line': 2, 'column': 4}])
        self.assertEqual(value['counts'], {'position_patterns': 1,
                         'admitted_position_patterns': 1, 'bounds_rejected': 0})
        self.assertEqual(failure.parser_positions(raw, SOURCES)['association'], 'unresolved')
        wide = {PATH: b'\n' * 1000 + b'x' * 1001}
        wrapped = b'syntax error at\n[ 1.001\t1.002 ]\nin\n' + REFERENCE
        self.assertEqual(failure.clay_parser_locations(wrapped, wide)['locations'],
                         [{'path': PATH, 'line': 1001, 'column': 1002}])

    def test_bad_coordinates_unknown_paths_and_formatter_lookalikes_are_closed(self):
        for position in (b'0 1', b'1 0', b'4 1', b'1 4', b'3 2'):
            with self.subTest(position=position):
                value = failure.clay_parser_locations(b'syntax error at [' + position + b'] in ' + REFERENCE, SOURCES)
                self.assertEqual(value['locations'], [])
                self.assertEqual(value['counts']['bounds_rejected'], 1)
        for raw in (b'not-syntax error at [1 1] in ' + REFERENCE,
                    b'syntax error at [1 1] in ' + REFERENCE + b'-suffix',
                    b'syntax error at {1 1} in ' + REFERENCE,
                    b'syntax error at [1.01 1] in ' + REFERENCE,
                    b'syntax error at [1 1] in/lib/stead-product-owner/hoon',
                    b'syntax error at [1 1] elsewhere ' + REFERENCE):
            with self.subTest(raw=raw):
                self.assertEqual(failure.clay_parser_locations(raw, SOURCES)['counts']['position_patterns'], 0)
        for sources in (None, {}):
            self.assertEqual(failure.clay_parser_locations(b'syntax error at [1 1] in ' + REFERENCE, sources)['locations'], [])
        unknown = b'syntax error at [1 1] in /gen/unadmitted/hoon'
        value = failure.clay_parser_locations(unknown, SOURCES)
        self.assertEqual(value['counts']['position_patterns'], 1)
        self.assertEqual(value['counts']['admitted_position_patterns'], 0)
        self.assertNotIn('unadmitted', json.dumps(value))

    def test_direct_tail_and_count_bounds_never_expand_source_or_output(self):
        source = {PATH: b'x' * 100}
        raw = b'\n'.join(b'syntax error at [1 ' + str(n).encode() + b'] in ' + REFERENCE
                         for n in [*range(1, 21), 20, 1])
        value = failure.clay_parser_locations(raw, source)
        self.assertTrue(value['truncated'])
        self.assertEqual(len(value['locations']), 16)
        self.assertEqual(value['locations'][-1], {'path': PATH, 'line': 1, 'column': 1})
        short = {'native/core/desk/lib/a.hoon': b'x'}
        repeated = b'syntax error at [1 1] in /lib/a/hoon\n' * 4097
        value = failure.clay_parser_locations(repeated, short)
        self.assertEqual(value['counts']['position_patterns'], 4096)
        self.assertTrue(value['counts_truncated'])
        with self.assertRaises(ValueError): failure.clay_parser_locations(b'x' * 262145, SOURCES)
        with self.assertRaises(ValueError): failure.clay_parser_locations(raw, {PATH: b'x' * (4 * 1024**2 + 1)})

    def test_direct_log_and_result_discard_source_caret_and_private_text(self):
        private = b'PRIVATE-SOURCE-LINE-MUST-NOT-LEAVE'
        log = b'syntax error at [2 3] in ' + REFERENCE + b'\n' + private + b'\n--^\n'
        terminal = (b'syntax error at [1 2] in ' + REFERENCE + b'\n' + private + b'\n-^').decode()
        native = {'commands': [{'ship': 'zod', 'dojo': '+stead-build-probe', 'result': terminal}],
                  'build_probe_transcripts': [{'ship': 'zod', 'dojo': '+stead-build-probe',
                    'log_offset': 1, 'log_bytes': len(log), 'log_hex': log.hex()}]}
        value = failure.build_probe_observations(native, SOURCES)[0]
        self.assertEqual(value['clay_parser_locations']['locations'], [{'path': PATH, 'line': 2, 'column': 3}])
        self.assertEqual(value['result_observation']['clay_parser_locations']['locations'],
                         [{'path': PATH, 'line': 1, 'column': 2}])
        encoded = json.dumps(value)
        for text in (private.decode(), '--^', log.hex(), terminal):
            self.assertNotIn(text, encoded)


if __name__ == '__main__':
    unittest.main()
