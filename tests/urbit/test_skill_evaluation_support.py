"""Host-only admission/bounds regressions. No Hoon process is launched.

The shaped receipt below is deliberately authored, not native evidence. Its
purpose is to test that incomplete records cannot pass structural admission.
Actual source/guard binding and reference execution are separately required.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/urbit'), str(Path(__file__).parent)]
import skill_evaluation_support as S
from gall_schedule_proof import _jam

PACKAGE = ROOT / 'tests/urbit/skill_evaluation'
# Exact ANSI-stripped streams from retained failed prequal03 T02 starter,
# 20260926T134510Z. This is observed output reused as a host parser fixture,
# not a native rerun or a replacement for that attempt's failed final status.
T02_ACTUAL_STDOUT = '-need.u(@ud)\r\n-have.@ud\r\nnest-fail'
T02_ACTUAL_STDERR = ('loom: mapped 512MB\r\nlite: arvo formula 4ce68411\r\n'
                     'lite: core 641296f\r\nlite: final state 641296f\r\n'
                     'eval (run):\n\r\neval: bail: %exit')


def authored_receipt(content, oracles):
    inventory = S.prequalification_inventory(content, oracles)
    references = {task: S.hashes(value) for task, value in S.select_inputs(content, None, True).items()}

    def observed(label):
        return {'label': label, 'actual_jam_hex': '02', 'actual_jam_sha256': S.digest(b'\x02'),
                'actual_noun': 'AUTHORED HOST SHAPE, NOT NATIVE EVIDENCE', 'decode_stderr': ''}

    control = observed('deliberate-false-native-expectation')
    control.update(actual_jam_hex='29', actual_jam_sha256=S.digest(b'\x29'), actual_noun='[0 0]')
    initial_raw = _jam((1, (0, 0)))  # Authored host noun, never native evidence.
    initial = observed('T03-initial-save-probe')
    initial.update(actual_jam_hex=initial_raw.hex(), actual_jam_sha256=S.digest(initial_raw),
                   actual_noun='[1 0 0]')
    rows, observations = [], [control]
    for name, wanted in inventory.items():
        results = ([{'label': wanted['labels'][0], 'actual_noun': '42'}] if name == 'T06'
                   else [observed(label) for label in wanted['labels']])
        row = {'id': name, 'status': 'passed', 'classification': wanted['classification'],
               'expected_cases': wanted['cases'], 'observed_cases': wanted['cases'], 'results': results}
        if name == 'T05':
            row.update(mutants=[Path(path).stem for path in oracles['tasks'][4]['mutants']],
                       requires_independent_test_semantics_review=True)
        rows.append(row)
        if name == 'T03':
            observations.append(initial)
        if name != 'T06':
            observations.extend(results)
    labels = [item['label'] for item in observations]
    generated = {label + '.hoon': 'a' * 64 for label in labels + ['T02-starter-rejection']}
    pure_labels = [control['label']] + inventory['T01']['labels'] + inventory['T02']['labels'] + inventory['T05']['labels']
    commands = [{'kind': 'native-pure-evaluator', 'status': 'completed', 'label': label,
                 'input_sha256': 'a' * 64, 'exit_code': 0,
                 'stdout': '' if label == 'T02-starter-rejection' else '[%skill-result ' + ('41' if label == control['label'] else '2') + ']',
                 'stderr': 'nest-fail' if label == 'T02-starter-rejection' else ''}
                for label in [pure_labels[0], 'T02-starter-rejection', *pure_labels[1:]]]
    commands += [{'kind': 'native-observed-noun', 'status': 'completed', **value} for value in observations]
    commands += [{'kind': 'native-dojo', 'status': 'completed', 'source': '+skill-eval-check',
                  'stdout': '[%skill-result ' + str(int.from_bytes(bytes.fromhex(value['actual_jam_hex']), 'little')) + ']'}
                 for value in observations if value['label'].startswith(('T03-', 'T04-'))]
    commands += [{'kind': 'native-dojo', 'status': 'completed', 'source': '+skill-eval!eval-desk-probe', 'stdout': '42'}]
    commands += [{'kind': 'native-dojo', 'status': 'completed', 'source': source, 'stdout': '%.y'}
                 for source in S.T06_METADATA_CHECKS.values()]
    names = {'loaded-adapter-closure-current', 'loaded-supervisor-current', 'actual-evaluator-controls',
             'T02-starter-rejection:actual-compiler-rejection', 'candidate-inputs-unchanged',
             'loaded-adapter-closure-still-current', 'loaded-supervisor-still-current', 'all-six-native-tasks-passed',
             'T01:declared-public-interface', 'T02:declared-public-interface', 'T05:immutable-subject',
             'T05:exact-test-imports', 'T05:nonempty-complete-arm-inventory', 'T05:coverage-report',
             'T06:exact-supplied-bytes', 'T06:exact-assembly-manifest', 'T06:repeat-empty-assembly',
             'T06:pinned-platform-baseline',
             'loaded-clay-metadata:skill-eval:desk.bill', 'loaded-clay-metadata:skill-eval:sys.kelvin',
             'T06:exact-native-mounted-desk', 'T06:native-clean-generator-result',
             'T03-initial-save-probe:initial-saved-noun'}
    names.update(label + ':native-evaluator-success' for label in pure_labels)
    names.update(label + ':exact-nonempty-result-frame' for label in labels)
    for name in S.TASKS:
        names.update((name + ':exact-file-inventory', name + ':nonzero-native-results'))
    for name in ('T03', 'T04'):
        names.update((name + ':ten-Gall-arms', name + ':only-authorized-arms-edited'))
    names.update('T05:original-arm-retained:' + arm for arm in oracles['tasks'][4]['preserved_test_arms'])
    return {'tasks': rows, 'checks': [{'name': name, 'passed': True} for name in sorted(names)],
            'commands': commands, 'failure_control': control,
            'prequalification_diagnostics': {'T03-initial-save-probe': initial}, 'candidate_files_sha256': references,
            'candidate_inputs_after': copy.deepcopy(references), 'generated_source_files_sha256': generated,
            'generated_source_files_after': copy.deepcopy(generated),
            'evaluator_controls': {'status': 'passed', 'classification': 'real-native-evaluator',
                'large_frame_bytes': 65537, 'large_frame_sha256': 'b' * 64, 'result_sha256': 'c' * 64,
                'invalid_input': {'exit': 0, 'encoder_rejected': True, 'stdout_hex': '', 'stderr': 'AUTHORED rejection'}}}


class PriorExecutionAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content, cls.oracles = S.verify_package(PACKAGE)

    def reject(self, mutation):
        report = authored_receipt(self.content, self.oracles)
        mutation(report)
        with self.assertRaises((ValueError, TypeError)):
            S.validate_prequalification_execution(report, self.content, self.oracles)

    def test_complete_authored_shape_only_is_accepted_as_structural_data(self):
        S.validate_prequalification_execution(authored_receipt(self.content, self.oracles), self.content, self.oracles)

    def test_missing_empty_and_short_native_result_inventory_rejected(self):
        for name in range(6):
            for replacement in (None, []):
                with self.subTest(task=name, replacement=replacement):
                    self.reject(lambda r, name=name, value=replacement: r['tasks'][name].update(results=value))
        self.reject(lambda r: r['tasks'][0]['results'].pop())

    def test_missing_or_relabelled_cases_rejected(self):
        self.reject(lambda r: r['tasks'][2].pop('expected_cases'))
        self.reject(lambda r: r['tasks'][2].update(observed_cases=['invented']))
        self.reject(lambda r: r['tasks'][0]['results'][0].update(label='wrong-case'))

    def test_removed_or_truthy_fake_failure_control_rejected(self):
        self.reject(lambda r: r.pop('failure_control'))
        self.reject(lambda r: r['failure_control'].update(actual_jam_hex='truthy'))
        self.reject(lambda r: r['failure_control'].update(actual_noun='~'))

    def test_missing_evaluator_controls_and_small_frame_rejected(self):
        self.reject(lambda r: r.pop('evaluator_controls'))
        self.reject(lambda r: r['evaluator_controls'].update(large_frame_bytes=65536))
        self.reject(lambda r: r['evaluator_controls']['invalid_input'].update(encoder_rejected=False))

    def test_initial_save_diagnostic_cannot_replace_full_cases_or_omit_native_evidence(self):
        label = 'T03-initial-save-probe'
        self.reject(lambda r: r.pop('prequalification_diagnostics'))
        self.reject(lambda r: r.update(prequalification_diagnostics={label: {'status': 'passed'}}))
        self.reject(lambda r: r['prequalification_diagnostics'][label].update(actual_noun='[1 1 0]'))
        self.reject(lambda r: r['prequalification_diagnostics'].update(extra=r['failure_control']))
        self.reject(lambda r: r.update(commands=[c for c in r['commands'] if c.get('label') != label]))
        self.reject(lambda r: r['generated_source_files_sha256'].pop(label + '.hoon'))
        self.reject(lambda r: r.update(checks=[c for c in r['checks'] if c['name'] != label + ':initial-saved-noun']))
        self.reject(lambda r: r['tasks'][2].update(results=[r['prequalification_diagnostics'][label]]))

    def test_missing_starter_rejection_or_signal_is_not_rejection(self):
        self.reject(lambda r: r['commands'].pop(1))
        self.reject(lambda r: r['commands'][1].update(exit_code=-15))
        self.reject(lambda r: r['commands'][1].update(stderr='timeout'))

    def test_actual_stdout_compiler_diagnostic_passes_both_parser_and_receipt_admission(self):
        self.assertTrue(S.compiler_rejection(0, T02_ACTUAL_STDOUT, T02_ACTUAL_STDERR))
        self.assertTrue(S.compiler_rejection(0, '', T02_ACTUAL_STDOUT))
        report = authored_receipt(self.content, self.oracles)
        report['commands'][1].update(stdout=T02_ACTUAL_STDOUT, stderr=T02_ACTUAL_STDERR)
        S.validate_prequalification_execution(report, self.content, self.oracles)

    def test_generic_bail_signal_timeout_and_result_do_not_replace_compiler_rejection(self):
        for code, stdout, stderr in ((0, '', T02_ACTUAL_STDERR), (0, 'timeout', 'eval: bail: %exit'),
                (-15, T02_ACTUAL_STDOUT, T02_ACTUAL_STDERR), (True, T02_ACTUAL_STDOUT, ''),
                (0, T02_ACTUAL_STDOUT + '\n[%skill-result 2]', ''),
                (0, T02_ACTUAL_STDOUT, '[%skill-result 2]')):
            with self.subTest(code=code, stdout=stdout, stderr=stderr):
                self.assertFalse(S.compiler_rejection(code, stdout, stderr))
                self.reject(lambda r: r['commands'][1].update(exit_code=code, stdout=stdout, stderr=stderr))
        with patch.object(S, 'MAX_OUTPUT', 8):
            self.assertFalse(S.compiler_rejection(0, T02_ACTUAL_STDOUT, ''))

    def test_empty_false_nonboolean_and_missing_required_checks_rejected(self):
        self.reject(lambda r: r.update(checks=[]))
        self.reject(lambda r: r['checks'][0].update(passed=False))
        self.reject(lambda r: r['checks'][0].update(passed=1))
        self.reject(lambda r: r.update(checks=[row for row in r['checks'] if row['name'] != 'actual-evaluator-controls']))

    def test_mutant_missing_or_not_behaviorally_evaluated_rejected(self):
        self.reject(lambda r: r['tasks'][4]['mutants'].pop())
        self.reject(lambda r: r['tasks'][4]['results'].pop())
        self.reject(lambda r: r['tasks'][4].update(requires_independent_test_semantics_review=False))

    def test_source_and_actual_command_inventory_rejected_when_incomplete(self):
        self.reject(lambda r: r['candidate_inputs_after']['T01'].clear())
        self.reject(lambda r: r['generated_source_files_after'].clear())
        self.reject(lambda r: r['commands'].pop())
        self.reject(lambda r: r['commands'].pop(-2))
        self.reject(lambda r: r.update(commands=[c for c in r['commands']
                    if c.get('source') != '+skill-eval!eval-desk-probe']))
        for source in S.T06_METADATA_CHECKS.values():
            self.reject(lambda r, source=source: next(c for c in r['commands']
                        if c.get('source') == source).update(stdout='%.n'))
        self.reject(lambda r: r['commands'][0].update(stdout=''))
        self.reject(lambda r: r['commands'][0].update(stdout='[%skill-result 2]'))

    def test_task_duplicates_and_status_only_rows_rejected(self):
        self.reject(lambda r: r['tasks'].append(copy.deepcopy(r['tasks'][0])))
        self.reject(lambda r: r.update(tasks=[{'id': name, 'status': 'passed'} for name in S.TASKS]))


class TypedInterfaceTests(unittest.TestCase):
    def test_extra_irregular_gap_test_is_discovered_and_other_spellings_fail_closed(self):
        source = (PACKAGE / 'reviewer/reference/T05/tests/eval-coverage.hoon').read_text()
        source = source.replace('\n--', '\n++   test-extra\n  (expect !>(=(1 1)))\n--')
        self.assertEqual(len(S.arm_names(source)), 7)
        self.assertIn('test-extra', S.arm_names(source))
        self.assertTrue(S.arm_block(source, 'test-extra').startswith('++   test-extra'))
        self.assertIn('++  test-extra\n<editable>\n', S.arm_skeleton(source, ('test-extra',)))
        unsupported = source.replace('++   test-extra', '++\n  test-extra')
        for function in (S.arm_names, lambda text: S.arm_block(text, 'test-extra'),
                         lambda text: S.arm_skeleton(text, ('test-extra',))):
            with self.subTest(function=function), self.assertRaisesRegex(ValueError, 'inventory cannot omit'):
                function(unsupported)

    def test_both_frozen_references_retain_declared_interface(self):
        for task, leaf in (('T01', 'eval-add.hoon'), ('T02', 'eval-maybe.hoon')):
            source = (PACKAGE / 'reviewer/reference' / task / 'lib' / leaf).read_text()
            self.assertTrue(S.declared_gate(source, task))
            self.assertTrue(S.declared_gate(source.replace('  ^-', '  :: comment\n  ^-'), task))

    def test_removed_widened_or_altered_sample_declared_types_rejected(self):
        for task, leaf in (('T01', 'eval-add.hoon'), ('T02', 'eval-maybe.hoon')):
            source = (PACKAGE / 'reviewer/reference' / task / 'lib' / leaf).read_text()
            for altered in (source.replace('  ^-  (unit @ud)\n', ''),
                            source.replace('^-  (unit @ud)', '^-  *'),
                            source.replace('=@ud', '=*')):
                with self.subTest(task=task, altered=altered):
                    self.assertFalse(S.declared_gate(altered, task))


class InputAndNounBounds(unittest.TestCase):
    def test_actual_prequalification_pretty_result_whitespace(self):
        # Exact stripped stdout from failed prequalification 20260925T122058Z,
        # deliberate-false-native-expectation. This tests parsing only and does
        # not replace the retained failed native execution with a native pass.
        actual = ('[ %skill-result\r\n  '
                  '10.602.123.684.338.566.177.939.652.388.787.148.777.188.920.248.210.308.928.773.'
                  '706.642.695.662.615.299.182.632.132.802.634.759.275.267.683.938.877.228.415.'
                  '889.472.646.015.887.216.225.529.507.403.835.343.456.750.928.735.211.397.610.501\r\n]')
        atom = int(actual.split()[2].replace('.', ''))
        self.assertEqual(S.result_jam(actual), atom.to_bytes((atom.bit_length() + 7) // 8, 'little'))
        for malformed in (actual + '\n[%skill-result 2]', 'noise\n' + actual,
                          actual.replace('10.602', '10. 602'), actual.replace('%skill-result', '%other')):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                S.result_jam(malformed)

    def test_file_limit_is_enforced_before_reading_an_extra_file(self):
        with tempfile.TemporaryDirectory() as temp:
            for name in ('first', 'second'):
                (Path(temp) / name).write_text('bounded')
            original = S.os.open
            with patch.object(S.os, 'open', wraps=original) as opened:
                with self.assertRaisesRegex(ValueError, 'file count bound'):
                    S.files(temp, maximum=1)
                self.assertEqual(opened.call_count, 1)

    def test_empty_directory_inventory_is_also_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            for number in range(9):
                (Path(temp) / str(number)).mkdir()
            with self.assertRaisesRegex(ValueError, 'directory entry bound'):
                S.files(temp, maximum=1)

    def test_file_total_and_link_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'one').write_bytes(b'x' * 5)
            with patch.object(S, 'MAX_FILE', 4), self.assertRaisesRegex(ValueError, 'byte bound'):
                S.files(root)
            (root / 'two').write_bytes(b'x' * 5)
            with patch.object(S, 'MAX_TOTAL', 9), self.assertRaisesRegex(ValueError, 'byte bound'):
                S.files(root)
            (root / 'redirect').symlink_to(root / 'one')
            with self.assertRaisesRegex(ValueError, 'Link or special'):
                S.files(root)

    def test_large_decimal_jam_does_not_change_global_digit_limits(self):
        before = sys.get_int_max_str_digits()
        digits = '1' + '0' * 9996 + '1234'
        expected = 10 ** 10000 + 1234
        self.assertEqual(int.from_bytes(S.result_jam('[%skill-result ' + digits + ']'), 'little'), expected)
        self.assertEqual(sys.get_int_max_str_digits(), before)

    def test_malformed_empty_oversized_decimal_and_trailing_output_rejected(self):
        for text in ('', '[%skill-result 0]', '[%skill-result 01]', '[%skill-result 1..234]',
                     '[%skill-result 2] trailing', '[%skill-result 1.23]'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                S.result_jam(text)
        with patch.object(S, 'MAX_JAM', 1), self.assertRaises(ValueError):
            S.result_jam('[%skill-result 999]')
        self.assertEqual(S.result_jam('[%skill-result 1.234]'), (1234).to_bytes(2, 'little'))


class PublicFeedbackSelection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content, cls.oracles = S.verify_package(PACKAGE)

    def test_public_plan_excludes_every_held_out_case_and_mutant_without_changing_oracles(self):
        before = copy.deepcopy(self.oracles)
        for name in S.TASKS:
            plan = S.task_plan(self.oracles, name)
            self.assertEqual([task['id'] for task in plan], [name])
            original = next(task for task in self.oracles['tasks'] if task['id'] == name)
            if name in ('T01', 'T02', 'T03'):
                self.assertEqual(plan[0]['cases'], [case for case in original['cases'] if case.get('public') is True])
                self.assertEqual(len(plan[0]['cases']), 2)
            elif name == 'T04':
                self.assertNotIn('private_scenario', plan[0])
                self.assertEqual(plan[0]['public_scenario'], original['public_scenario'])
            elif name == 'T05':
                self.assertEqual(plan[0]['mutants'], [])
            else:
                self.assertEqual(plan[0], original)
        self.assertEqual(self.oracles, before)
        self.assertEqual(S.task_plan(self.oracles), before['tasks'])

    def test_invalid_public_mode_rejected_before_source_or_runtime_access(self):
        for condition, prequalify, task, attempt in (
                ('prequalification', True, 'T01', 1), ('baseline', False, 'T07', 1),
                ('baseline', False, 'T01', 0), ('baseline', False, 'T01', 4),
                ('baseline', False, 'T01', True), ('baseline', False, 'T01', '1'),
                ('baseline', False, None, 1)):
            with self.subTest(condition=condition, task=task, attempt=attempt), patch.object(S, 'verify_package') as verify:
                with self.assertRaisesRegex(ValueError, 'Public feedback requires'):
                    S.run({}, PACKAGE, '/not-accessed', condition, prequalify=prequalify,
                          feedback_task=task, feedback_attempt=attempt)
                verify.assert_not_called()

    def test_t03_generated_gate_keeps_exact_frozen_case_calls_and_public_filter(self):
        task = self.oracles['tasks'][2]
        source = S.t03_program(task)
        self.assertEqual(source.count('|=  [label=@t incoming=vase expected=* must-reject=? repeat-load=?]'), 1)
        self.assertIn('=/  agent=agent:gall', source)
        self.assertIn('(mute:vi |.((on-load:loaded incoming)))', source)
        for case in task['cases']:
            self.assertEqual(source.count("(run-case '" + case['id'] + "'"), 1)
            self.assertIn('!>(' + case['load_noun'] + ')', source)
        self.assertEqual(source.count('(run-case '), 12)
        public = S.t03_program(S.task_plan(self.oracles, 'T03')[0])
        self.assertEqual(public.count('(run-case '), 2)
        for private in ('(mute:vi ', '[%1 5 2]', 'future-version', '65.536', 'repeat-roundtrip'):
            self.assertNotIn(private, public)

    def test_t03_keeps_native_assertions_and_bounds_projected_evidence_before_rendering(self):
        source = S.t03_program(self.oracles['tasks'][2])
        for stage in ('body-enter', 'case-begin label', 'load-begin label', 'load-returned label',
                      'mute-begin label', 'mute-returned label', 'case-checked label',
                      'roundtrip-load-begin label', 'roundtrip-load-returned label',
                      'all-cases-checked', 'jam-begin', 'result-jam-bytes encoded-bytes'):
            self.assertIn('[%stead-skill-t03 %' + stage + ']', source)
        self.assertEqual(source.count('(jam evidence)'), 1)
        check = '?.  (lte encoded-bytes 262.144)'
        self.assertEqual(S.MAX_JAM, 262144)
        self.assertLess(source.index('%all-cases-checked'), source.index('(jam evidence)'))
        self.assertLess(source.index('(jam evidence)'), source.index(check))
        self.assertLess(source.index(check), source.index('[%skill-result encoded]'))
        self.assertIn('~|  [%stead-skill-t03-result-jam-oversize encoded-bytes]\n  !!', source)
        for assertion in ('?>  =(~ cards)', '?>  =(~ later-cards)', '?>  =(expected q.observed)',
                          '?>  ?=(%| -.rejected)', '?>  =(before after)', '?>  =(observed again)'):
            self.assertIn(assertion, source)
        self.assertIn('[q.saved (met 3 encoded-type) (shax encoded-type)]', source)
        self.assertIn('[label (view-saved before) [-.rejected (met 3 encoded-tang) (shax encoded-tang)] (view-saved after)]', source)
        self.assertIn('[label cards (view-saved observed)]', source)
        self.assertNotIn('[label before rejected after]', source)
        self.assertNotIn('[label cards observed]', source)
        initial = S.t03_initial_program()
        self.assertIn('=/  original=agent:gall', initial)
        self.assertIn('=/  initial=vase  on-save:original', initial)
        self.assertIn('?>  =([%1 0 0] q.initial)', initial)
        self.assertIn('[%skill-result (jam q.initial)]', initial)
        self.assertNotIn('(jam initial)', initial)


class PublicFeedbackExecution(unittest.TestCase):
    """Actual Python adapter execution with all native calls explicitly mocked."""
    @classmethod
    def setUpClass(cls):
        cls.content, cls.oracles = S.verify_package(PACKAGE)
        cls.references = S.select_inputs(cls.content, None, True)

    def execute(self, task, *, condition='baseline', missing_prior=False,
                compile_failure=False, cleanup_failure=False, private_all=False,
                dojo_timeout=False, evaluator_timeout=False, prequalify=False,
                extra_platform_file=False, bad_metadata=None):
        with tempfile.TemporaryDirectory(prefix='stead-public-feedback-host-') as temp, ExitStack() as stack:
            root = Path(temp)
            candidate = root / 'candidate'
            selected = copy.deepcopy(self.references[task])
            if task == 'T05':
                # The public path executes even the original two arms; private
                # scoring alone requires added coverage and the four mutants.
                selected['tests/eval-coverage.hoon'] = self.content['public/starters/T05/tests/eval-coverage.hoon']
                selected['coverage.json'] = json.dumps({'missing_behavior': 'host fixture',
                    'why_existing_tests_miss_it': 'host fixture', 'added_arms': []}).encode()
            if private_all:
                selected = {name + '/' + path: raw for name, values in self.references.items()
                            for path, raw in values.items()}
            for name, raw in selected.items():
                path = candidate / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
            state = root / 'state'
            (state / 'logs').mkdir(parents=True)
            live = state / 'live'
            (live / 'zod/base').mkdir(parents=True)
            kernel = root / 'kernel'
            for name in ('pkg/base-dev/lib/test.hoon', 'pkg/base-dev/lib/default-agent.hoon',
                         'pkg/arvo/sys/vane/gall.hoon', 'pkg/arvo/lib/test/ames-gall.hoon',
                         *('pkg/arvo/' + path for path in S.T06_PLATFORM_BASELINE + S.T06_PLATFORM_ADDITIONS)):
                path = kernel / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(':: HOST-ONLY MOCK NATIVE DEPENDENCY\n')
            lease = {'run_id': 'authored-host-only', 'generation': 1, 'guard_sha256': 'a' * 64,
                     'policy_sha256': 'b' * 64, 'policy': {'authored': True}}
            stop = Mock(side_effect=[None, RuntimeError('authored cleanup failure')] if cleanup_failure else None)

            def dojo(ship, source):
                self.assertEqual(ship, 'zod')
                if source == '|mount %skill-eval':
                    desk = live / 'zod/skill-eval'
                    desk.mkdir()
                    for name in S.T06_PLATFORM_BASELINE:
                        target = desk / name
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes((kernel / 'pkg/arvo' / name).read_bytes())
                    if extra_platform_file:
                        (desk / 'unexpected.hoon').write_text(':: authored unexpected platform file\n')
                if bad_metadata and source == S.T06_METADATA_CHECKS[bad_metadata]:
                    return '%.n'
                if source == '+skill-eval!eval-desk-probe':
                    return '42'
                generator = live / 'zod/base/gen/skill-eval-check.hoon'
                initial = generator.exists() and '%stead-skill-t03-initial' in generator.read_text()
                if source == '+skill-eval-check' and dojo_timeout and not initial:
                    raise TimeoutError('AUTHORED pending native computation')
                return '[ %skill-result\r\n  2\r\n]' if source == '+skill-eval-check' else '%.y'

            host = {'STATE': state, 'LIVE': live, 'SHIPS': ('zod', 'bus', 'nec', 'bud'),
                    'LOCK': {'runtime': {'binary': 'never-executed'}},
                    'WORKFLOW_SOURCE_COMMIT': 'a' * 40, 'LOADED_SOURCE_DIGEST': 'authored-source',
                    'execution_check': Mock(return_value=lease), 'all_stop': stop,
                    'copy_seed_to_live': Mock(), 'launch': Mock(), 'wait_ready': Mock(),
                    'dojo': Mock(side_effect=dojo)}
            original_sha = S.sha
            stack.enter_context(patch.object(S, 'Path', side_effect=lambda value: kernel if value == '/kernel' else Path(value)))
            stack.enter_context(patch.object(S, 'sha', side_effect=lambda value: 'c' * 64 if value == '/toolchain.json' else original_sha(value)))
            stack.enter_context(patch.object(S, 'source_sha', return_value='authored-source'))
            prior = stack.enter_context(patch.object(S, 'require_prequalification',
                side_effect=ValueError('PRIVATE-PRIOR-RECORD') if missing_prior else None,
                return_value={'authored': 'PRIVATE-PRIOR-RECORD'}))
            controls = stack.enter_context(patch.object(S.core_conn, 'evaluator_controls', return_value={'status': 'passed'}))
            launch = stack.enter_context(patch.object(S.subprocess, 'run', side_effect=AssertionError('No native process may execute in host regression')))
            programs = []

            def evaluate(binary, source, record):
                programs.append((record['label'], source))
                if record['label'] == 'T02-starter-rejection':
                    record.update(status='completed', exit_code=0, stdout=T02_ACTUAL_STDOUT, stderr=T02_ACTUAL_STDERR)
                    return 0, T02_ACTUAL_STDOUT, T02_ACTUAL_STDERR
                if evaluator_timeout and record['label'].startswith(task):
                    record.update(status='failed', timed_out=True)
                    raise subprocess.TimeoutExpired(['AUTHORED-evaluator'], 30)
                failed = compile_failure and record['label'].startswith(task)
                record.update(status='completed', exit_code=1 if failed else 0,
                              stdout='' if failed else '[%skill-result 2]',
                              stderr='authored public compiler diagnostic' if failed else '')
                return record['exit_code'], record['stdout'], record['stderr']

            evaluator = stack.enter_context(patch.object(S, 'evaluate_source', side_effect=evaluate))
            def decode(*_):
                generator = live / 'zod/base/gen/skill-eval-check.hoon'
                initial = generator.exists() and '%stead-skill-t03-initial' in generator.read_text()
                return (b'[1 0 0]\n' if initial else b'AUTHORED HOST NOUN', b'')
            stack.enter_context(patch.object(S.core_conn, 'evaluate', side_effect=decode))
            result = S.run(host, PACKAGE, candidate, 'prequalification' if prequalify else condition,
                           prequalify=prequalify,
                           feedback_task=None if private_all or prequalify else task,
                           feedback_attempt=None if private_all or prequalify else 1)
            private = json.loads((state / 'logs' / Path(result['evidence_file']).name).read_bytes())
            public = (None if private_all or prequalify else
                      json.loads((state / 'logs' / Path(result['feedback_file']).name).read_bytes()))
            launch.assert_not_called()
            return {'result': result, 'private': private, 'public': public, 'programs': programs,
                    'prior': prior, 'controls': controls, 'evaluator': evaluator, 'host': host}

    def test_each_public_task_executes_only_its_public_inventory(self):
        for task in S.TASKS:
            with self.subTest(task=task):
                run = self.execute(task)
                public = run['public']
                self.assertEqual(public['status'], 'pass', run['private'].get('error'))
                self.assertFalse(public['private_scoring'])
                self.assertFalse(public['qualifies_phase'])
                self.assertEqual(public['outer_guard_status'], 'pending')
                self.assertEqual(list(public['candidate_files_sha256']), [task])
                self.assertEqual([row['id'] for row in public['tasks']], [task])
                row = public['tasks'][0]
                if task in ('T01', 'T02', 'T03'):
                    self.assertEqual(row['observed_cases'], [case['id'] for case in S.task_plan(self.oracles, task)[0]['cases']])
                elif task == 'T04':
                    self.assertEqual(row['observed_cases'], ['public-0', 'public-1'])
                    self.assertEqual([result['label'] for result in row['results']], ['T04-public-Gall'])
                elif task == 'T05':
                    self.assertEqual(row['observed_cases'], ['test-writer', 'test-stale'])
                    self.assertEqual(row['mutants'], [])
                    self.assertEqual([result['label'] for result in row['results']], ['T05-correct'])
                else:
                    self.assertEqual(row['observed_cases'], ['assembly-bytes', 'repeat-empty-assembly', 'native-clean-generator'])
                    self.assertEqual(row['results'][0]['actual_noun'], '42')
                    platform = run['private']['desk_platform']
                    self.assertEqual(len(platform['initial_files_sha256']), 5)
                    self.assertEqual(list(platform['added_files_sha256']), ['mar/bill.hoon'])
                    self.assertEqual(len(platform['mounted_files_sha256']), 9)
                    calls = run['host']['dojo'].call_args_list
                    for source in S.T06_METADATA_CHECKS.values():
                        self.assertTrue(any(call.args == ('zod', source) for call in calls))
                disclosed = json.dumps(public)
                self.assertNotIn('PRIVATE-PRIOR-RECORD', disclosed)
                self.assertNotIn('deliberate-false-native-expectation', disclosed)
                self.assertNotIn('T04-private-Gall', disclosed)
                self.assertNotIn('all-six-native-tasks-passed', disclosed)
                run['prior'].assert_called_once()

    def test_unexpected_platform_file_blocks_desk_before_candidate_install(self):
        run = self.execute('T06', extra_platform_file=True)
        self.assertEqual(run['public']['status'], 'fail')
        self.assertIn('T06:pinned-platform-baseline', run['private']['tasks'][0]['error'])
        self.assertFalse(any(call.args[1] in ('|commit %skill-eval', '+skill-eval!eval-desk-probe')
                             for call in run['host']['dojo'].call_args_list))

    def test_wrong_typed_metadata_blocks_native_generator(self):
        for name in S.T06_METADATA_CHECKS:
            with self.subTest(name=name):
                run = self.execute('T06', bad_metadata=name)
                self.assertEqual(run['public']['status'], 'fail')
                self.assertIn('loaded-clay-metadata:skill-eval:' + name, run['private']['tasks'][0]['error'])
                self.assertFalse(any(call.args[1] == '+skill-eval!eval-desk-probe'
                                     for call in run['host']['dojo'].call_args_list))

    def test_conditions_receive_identical_public_programs(self):
        baseline = self.execute('T01')
        assisted = self.execute('T01', condition='local_skill_assisted')
        self.assertEqual(baseline['programs'], assisted['programs'])
        self.assertEqual(baseline['public']['tasks'], assisted['public']['tasks'])

    def test_missing_completed_prequalification_blocks_all_native_work_without_disclosing_proof(self):
        run = self.execute('T01', missing_prior=True)
        self.assertEqual(run['public']['status'], 'fail')
        self.assertEqual(run['public']['commands'], [])
        self.assertNotIn('PRIVATE-PRIOR-RECORD', json.dumps(run['public']))
        self.assertIn('PRIVATE-PRIOR-RECORD', run['private']['error'])
        for call in (run['controls'], run['evaluator'], run['host']['dojo'], run['host']['launch']):
            call.assert_not_called()
        run['host']['all_stop'].assert_called_once()

    def test_failed_public_compiler_result_is_retained_and_never_reported_green(self):
        run = self.execute('T01', compile_failure=True)
        self.assertEqual(run['public']['status'], 'fail')
        self.assertEqual(run['public']['tasks'][0]['status'], 'failed')
        self.assertIn('authored public compiler diagnostic', json.dumps(run['public']['commands']))
        self.assertNotIn('PRIVATE-PRIOR-RECORD', json.dumps(run['public']))

    def test_cleanup_failure_invalidates_previously_passing_public_task(self):
        run = self.execute('T01', cleanup_failure=True)
        self.assertEqual(run['public']['tasks'][0]['status'], 'passed')
        self.assertEqual(run['public']['status'], 'fail')
        self.assertTrue(run['public']['infrastructure_error'])
        self.assertIn('authored cleanup failure', run['private']['cleanup_error'])

    def test_private_scoring_or_multiple_tasks_cannot_be_projected_as_feedback(self):
        report = self.execute('T01')['private']
        report['public_feedback'] = False
        with self.assertRaisesRegex(ValueError, 'Only a public feedback'):
            S.public_feedback_projection(report)
        report['public_feedback'] = True
        report['tasks'].append({'id': 'T02', 'status': 'passed'})
        with self.assertRaisesRegex(ValueError, 'cannot disclose other tasks'):
            S.public_feedback_projection(report)

    def test_lens_timeout_aborts_before_following_task_and_enters_cleanup(self):
        run = self.execute('T03', private_all=True, dojo_timeout=True)
        report = run['private']
        self.assertEqual([row['status'] for row in report['tasks']],
                         ['passed', 'passed', 'failed', 'not_run', 'not_run', 'not_run'])
        self.assertEqual(report['native_execution_interrupted']['task'], 'T03')
        self.assertEqual(report['commands'][-1]['source'], '+skill-eval-check')
        self.assertEqual(report['commands'][-1]['status'], 'failed')
        self.assertNotIn('/app/eval-access/hoon', json.dumps(report['commands']))
        self.assertEqual(run['host']['all_stop'].call_count, 2)

    def test_prequalification_retains_small_initial_probe_then_full_timeout_without_scoring_later_tasks(self):
        run = self.execute('T03', prequalify=True, dojo_timeout=True)
        report = run['private']
        self.assertEqual([row['status'] for row in report['tasks']],
                         ['passed', 'passed', 'failed', 'not_run', 'not_run', 'not_run'])
        initial = report['prequalification_diagnostics']['T03-initial-save-probe']
        self.assertEqual(initial['actual_noun'], '[1 0 0]\n')
        self.assertIn('T03-initial-save-probe.hoon', report['generated_source_files_sha256'])
        calls = [c for c in report['commands'] if c.get('source') == '+skill-eval-check']
        self.assertEqual([c['status'] for c in calls], ['completed', 'failed'])
        self.assertEqual(run['host']['all_stop'].call_count, 2)
        self.assertNotIn('/app/eval-access/hoon', json.dumps(report['commands']))
        public = self.execute('T03')['private']
        self.assertNotIn('prequalification_diagnostics', public)
        self.assertNotIn('T03-initial-save-probe.hoon', public['generated_source_files_sha256'])

    def test_evaluator_timeout_also_aborts_remaining_tasks(self):
        run = self.execute('T01', private_all=True, evaluator_timeout=True)
        self.assertEqual([row['status'] for row in run['private']['tasks']],
                         ['failed', 'not_run', 'not_run', 'not_run', 'not_run', 'not_run'])
        self.assertEqual(run['private']['native_execution_interrupted']['task'], 'T01')
        self.assertEqual(run['host']['all_stop'].call_count, 2)
        self.assertFalse(any(label.startswith('T02-') for label, _ in run['programs']))

    def test_public_timeout_is_infrastructure_failure_not_publishable_task_feedback(self):
        run = self.execute('T03', dojo_timeout=True)
        self.assertEqual(run['public']['status'], 'fail')
        self.assertTrue(run['public']['infrastructure_error'])


class FailureEvidence(unittest.TestCase):
    def evaluate(self, output, diagnostics, failure=None):
        record = {'status': 'running'}
        def fake(argv, *, stdout, stderr, **kwargs):
            stdout.write(output)
            stderr.write(diagnostics)
            if failure:
                raise failure(argv)
            return subprocess.CompletedProcess(argv, 0)
        return record, patch.object(S.subprocess, 'run', side_effect=fake)

    def test_timeout_retains_both_raw_prefixes_and_argv(self):
        record, mocked = self.evaluate(b'partial output', b'partial diagnostics', lambda argv: subprocess.TimeoutExpired(argv, 30))
        with mocked, self.assertRaises(subprocess.TimeoutExpired):
            S.evaluate_source('/synthetic-never-executed', '!!', record)
        self.assertEqual(record['status'], 'failed')
        self.assertTrue(record['timed_out'])
        self.assertEqual(record['stdout_prefix_hex'], b'partial output'.hex())
        self.assertEqual(record['stderr_prefix_hex'], b'partial diagnostics'.hex())
        self.assertEqual(record['argv'], ['/synthetic-never-executed', 'eval', '--loom', '29'])

    def test_invalid_utf8_retains_exact_bytes(self):
        record, mocked = self.evaluate(b'\xff', b'compiler text')
        with mocked, self.assertRaises(UnicodeDecodeError):
            S.evaluate_source('/synthetic-never-executed', '!!', record)
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['stdout_prefix_hex'], 'ff')
        self.assertEqual(record['stderr_prefix_hex'], b'compiler text'.hex())

    def test_oversized_output_retains_bounded_prefix_and_size(self):
        record, mocked = self.evaluate(b'x' * 10, b'note')
        with mocked, patch.object(S, 'MAX_OUTPUT', 8), patch.object(S, 'FAILURE_PREFIX', 4):
            with self.assertRaisesRegex(ValueError, 'output bound'):
                S.evaluate_source('/synthetic-never-executed', '!!', record)
        self.assertEqual(record['status'], 'failed')
        self.assertEqual(record['stdout_bytes'], 10)
        self.assertEqual(record['stdout_prefix_hex'], b'xxxx'.hex())
        self.assertFalse(record['stdout_prefix_complete'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
