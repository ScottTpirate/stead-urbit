"""Six inert source/selection/observation boundaries; no Hoon or process runs.

Marker fixtures below are synthetic grammar examples, not recovered historical
logs. The original Hoon bytes are checked independently of those examples.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts/ci')]
import core_conn
import native_units as units
import team_check as coordinator
import worker_failure


class RestoreCheckpointStagesTests(unittest.TestCase):
    def inventory(self):
        return json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_bytes())

    def sources(self):
        return {name: (ROOT / name).read_bytes() for name in units.TRACE_SOURCES}

    def lines(self):
        # sloe iteration order is not presumed; reverse source order proves it.
        lines = []
        for arm in reversed(units.TRACE_ARMS):
            lines.extend([units.TRACE_PREFIX + ' compile-start ' + arm + '\n',
                          units.TRACE_PREFIX + ' compile-end ' + arm + '\n'])
        return lines + [units.TRACE_PREFIX + ' ' + phase + '\n'
                        for phase in ('run-start', *units.TRACE_BODY, 'run-end')]

    def test_exact_sources_reproduce_original_fixture_and_kernel_runner(self):
        sources = self.sources()
        self.assertEqual(units.verify_trace_sources(sources), units.TRACE_SOURCES)
        original = sources['native/core/desk/tests/stead-product-restore.hoon']
        traced = sources['native/core/desk/tests/stead-product-restore-checkpoint-trace.hoon']
        hints = [line for line in traced.splitlines(keepends=True) if units.TRACE_PREFIX.encode() in line]
        self.assertEqual(len(hints), 5)
        self.assertEqual([line.decode().split(units.TRACE_PREFIX + ' ')[1].split('"')[0]
                          for line in hints], list(units.TRACE_BODY))
        self.assertEqual(b''.join(line for line in traced.splitlines(keepends=True)
                                  if units.TRACE_PREFIX.encode() not in line), original)
        names = re.findall(rb'^\+\+  (test-[a-z0-9-]+)$', original, re.M)
        self.assertEqual([name.decode() for name in names], list(units.TRACE_ARMS))
        self.assertEqual(set(names), {name.encode() for name in next(
            row for row in self.inventory()['suites'] if row['path'] == units.RESTORE_PATH)['arms']})
        thread = sources['native/core/desk/ted/stead-restore-checkpoint-trace.hoon']
        guard = (b'?>  ?=(^ fiz)\n?>  ?=(~ t.fiz)\n?>  =(~zod p.beam.i.fiz)\n'
                 b'?>  =(%base q.beam.i.fiz)\n'
                 b'?>  =(/tests/stead-product-restore-checkpoint-trace/hoon s.beam.i.fiz)\n'
                 b'?>  =([~ %test-product-restore-incremental-checkpoint-exposes-no-partial-state] test.i.fiz)\n')
        self.assertEqual(thread.count(guard), 1)
        restored = b''.join(line for line in thread.replace(guard, b'').splitlines(keepends=True)
                            if units.TRACE_PREFIX.encode() not in line)
        self.assertEqual(hashlib.sha256(restored).hexdigest(),
                         '1b158c40c3e58f7ea19ef4aea1ff642a388420585590f3d54e7c6aa1788b765b')
        self.assertEqual(len(self.inventory()['suites']), 48)
        self.assertEqual(sum(len(row['arms']) for row in self.inventory()['suites']), 329)
        for name in sources:
            changed = sources | {name: sources[name] + b'\n'}
            with self.subTest(name=name), self.assertRaises(ValueError):
                units.verify_trace_sources(changed)
        for wrong in ({}, sources | {'caller-path': b''}, sources | {next(iter(sources)): None}):
            with self.assertRaises(ValueError):
                units.verify_trace_sources(wrong)

    def test_ordered_progress_prefixes_and_early_return_are_not_verdicts(self):
        lines = self.lines()
        self.assertEqual(len(lines), 23)
        for size in range(24):
            with self.subTest(prefix=size):
                value = units.trace_progress(''.join(lines[:size]).encode())
                self.assertEqual(value['status'], 'observed')
                self.assertEqual(len(value['markers']), size)
                self.assertEqual(units.validate_trace_progress(value), value)
                self.assertFalse({'passed', 'outcome', 'qualified'} & set(value))
        for body_count in range(6):
            raw = ''.join(lines[:17 + body_count] + [lines[-1]]).encode()
            value = units.trace_progress(raw)
            self.assertEqual(value['status'], 'observed')
            self.assertEqual(value['markers'][-1], {'phase': 'run-end', 'arm': units.RESTORE_ARM})
            entry = units.restore_entries(self.inventory())[1]
            partial = units.partial_log(entry, raw)
            self.assertEqual(partial['registered_arm_observations'], [])
            self.assertFalse(partial['build_observed'])
        # An unfinished final line is not an observation; no reconstructed tail.
        raw = ''.join(lines[:16]).encode() + lines[16].rstrip('\n').encode()
        self.assertEqual(len(units.trace_progress(raw)['markers']), 16)

    def test_closed_grammar_refuses_unknown_reordered_crossed_or_malformed_rows(self):
        lines = self.lines()
        malformed = [lines[1], lines[0] + lines[0], lines[0] + lines[3],
                     lines[16], ''.join(lines[:17]) + lines[18],
                     ''.join(lines) + lines[-1],
                     units.TRACE_PREFIX + ' arbitrary-private-text\n',
                     units.TRACE_PREFIX + ' compile-start test-foreign\n',
                     'prefix ' + lines[0], '\u0085' + lines[0],
                     lines[0].replace('compile-start ', 'compile-start  ')]
        for raw in [value.encode() for value in malformed] + [b'\xff']:
            with self.subTest(raw=raw[:80]):
                value = units.trace_progress(raw)
                self.assertEqual(value['status'], 'malformed')
                self.assertEqual(value['markers'], [])
                self.assertNotIn('arbitrary-private-text', json.dumps(value))
        full = units.trace_progress(''.join(lines).encode())
        for wrong in (full | {'sources': {}}, full | {'status': True}, full | {'markers': ()},
                      full | {'markers': full['markers'] + full['markers'][:1]},
                      full | {'markers': [{'phase': 'compile-start', 'arm': True}]},
                      full | {'status': 'malformed'}, full | {'extra': 'private'}):
            with self.assertRaises(ValueError):
                units.validate_trace_progress(wrong)
        with self.assertRaises(ValueError):
            units.trace_progress(b'x' * 262145)
        with self.assertRaises(ValueError):
            units.trace_completed_output(lines[0].rstrip('\n'))

    def test_accepted_output_requires_complete_stages_and_existing_native_verdict(self):
        lines = self.lines()
        built = 'built   ' + units.TRACE_PATH + '/hoon\n'
        ok = 'OK      ' + units.TRACE_PATH + '/' + units.RESTORE_ARM + '\n'
        terminal = '[32 %avow 0 %noun 0]'
        raw = built + ''.join(lines) + ok + terminal
        cleaned = units.trace_completed_output(raw)
        self.assertEqual(cleaned, built + ok + terminal)
        verified = units.verify_output(cleaned, path=units.TRACE_PATH,
                                       expected=[units.RESTORE_ARM], succeeds=True)
        self.assertEqual(verified['observed'], [units.RESTORE_ARM])
        for missing in range(len(lines)):
            incomplete = built + ''.join(lines[:missing] + lines[missing + 1:]) + ok + terminal
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                units.trace_completed_output(incomplete)
        for plain in (built + terminal, built + ok, built + ok + '[32 %avow 0 %noun 1]'):
            with self.assertRaises(ValueError):
                units.verify_output(units.trace_completed_output(''.join(lines) + plain),
                                    path=units.TRACE_PATH, expected=[units.RESTORE_ARM], succeeds=True)
        # mule returning after a body crash is a valid stage sequence, not a pass.
        failed = (built + ''.join(lines[:19] + [lines[-1]]) +
                  'CRASHED ' + units.TRACE_PATH + '/' + units.RESTORE_ARM + '\n[32 %avow 0 %noun 1]')
        cleaned = units.trace_completed_output(failed)
        with self.assertRaises(ValueError):
            units.verify_output(cleaned, path=units.TRACE_PATH, expected=[units.RESTORE_ARM], succeeds=True)

    def test_fixed_request_uses_only_selected_thread_and_sixty_second_deadline(self):
        beam = '/~zod/base/~2026.1.1'
        selected = units.TRACE_PATH + '/' + units.RESTORE_ARM
        stopped = RuntimeError('inert before any socket or evaluator')
        with patch.object(core_conn, 'evaluate', side_effect=stopped) as encode:
            for path, expected_thread in ((selected, units.TRACE_THREAD), (units.NEGATIVE_PATH, 'test')):
                with self.assertRaises(RuntimeError) as caught:
                    units.run('never-executed', '/inert/socket', beam + path, 60)
                self.assertIs(caught.exception, stopped)
                self.assertIn(('%base %' + expected_thread + ' %noun [%path [').encode(), encode.call_args.args[2])
            self.assertEqual(encode.call_count, 2)
            for path, timeout in ((units.TRACE_PATH, 60), (selected + '/extra', 60),
                                  (units.TRACE_PATH + '/test-foreign', 60), (selected, 60.0),
                                  (selected, 61), (selected, True)):
                with self.subTest(path=path, timeout=timeout), self.assertRaises(ValueError):
                    units.run('never-executed', '/inert/socket', beam + path, timeout)
            self.assertEqual(encode.call_count, 2)
        entry = units.restore_entries(self.inventory())[1]
        with self.assertRaises(ValueError):
            units.restore_request_path(entry | {'timeout_seconds': 60.0})

    def test_failed_frame_binds_source_and_keeps_partial_stages_out_of_verdicts(self):
        inventory, sources = self.inventory(), self.sources()
        entry = units.restore_entries(inventory)[1]
        partial = ''.join(self.lines()[:19]).encode()
        error = TimeoutError('private exception text')
        error.native_interruption = units.interruption_transport('response-header', 60001, b'', 60)
        native = {'diagnostic_scope': units.restore_scope(), 'diagnostic_only': True,
                  'native_unit_transcripts': [{'path': units.NEGATIVE_PATH}],
                  'native_units': [{'path': units.NEGATIVE_PATH}], 'checks': []}
        coordinator.diagnostic_error(native, error, 'suite', units.TRACE_PATH)
        coordinator.diagnostic_unit_progress(native, entry, error, partial, inventory)
        inputs, run_id = {}, '1' * 32
        value = {'format': 'stead.local-ci-worker/1', 'status': 'fail', 'run_id': run_id,
                 'inputs_sha256': hashlib.sha256(worker_failure.canonical(inputs)).hexdigest(),
                 'native': native, 'cleanup': True}
        raw = worker_failure.PREFIX.encode() + worker_failure.canonical(value) + b'\n'
        result = worker_failure.project(raw, inputs, run_id=run_id, inventory=inventory, sources=sources)
        self.assertIs(result['qualifies_phase'], False)
        self.assertEqual(result['native']['suites_recorded'], 1)
        self.assertEqual(result['native']['failed_units'], [])
        progress = result['native']['diagnostic_limits']['unit_progress']
        self.assertEqual(len(progress['log']['stages']['markers']), 19)
        self.assertEqual(progress['log']['registered_arm_observations'], [])
        self.assertIs(progress['transport']['terminal_accepted'], False)
        self.assertNotIn('private exception text', json.dumps(result))
        self.assertNotIn('log_hex', json.dumps(result))
        for wrong in (None, {}, sources | {next(iter(sources)): b'wrong'}):
            with self.assertRaises(ValueError):
                worker_failure.project(raw, inputs, run_id=run_id, inventory=inventory, sources=wrong)
        completed = {'diagnostic_scope': units.restore_scope(), 'diagnostic_only': True,
                     'native_unit_failures': [units.TRACE_PATH],
                     'native_unit_transcripts': [{'path': units.TRACE_PATH, 'log_hex': partial.hex()}]}
        observation = worker_failure.failed_unit_observations(completed, inventory, sources)[0]
        self.assertEqual(len(observation['stages']['markers']), 19)
        self.assertEqual(observation['registered_arm_observations'], [])
        self.assertEqual(observation['log_sha256'], hashlib.sha256(partial).hexdigest())


if __name__ == '__main__':
    unittest.main()
