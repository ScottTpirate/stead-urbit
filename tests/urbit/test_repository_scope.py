"""Host-only checks of the closed T04 selector; no Hoon process is started."""
import ast
import copy
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('repository_scope_units', ROOT / 'scripts/urbit/native_units.py')
UNITS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(UNITS)
INVENTORY = json.loads((ROOT / 'specs/urbit/phase2-pure-units.json').read_text())
SOURCE = (ROOT / 'scripts/urbit/team_check.py').read_text()
EXPECTED = ('/tests/stead-repository-catalog', '/tests/stead-repository-import', '/controls/stead-unit-failure')


class RepositoryScopeTests(unittest.TestCase):
    def invoke(self, *, corrupt=False, transport_failure=False):
        observed, checkpoints, checks = [], [], []
        report = {'commands': []}
        class FixedPath:
            def __init__(self, value): self.value = str(value)
            def __truediv__(self, value): return FixedPath(self.value + '/' + str(value))
            def read_text(self):
                self_outer.assertEqual(self.value, '/specs/phase2-pure-units.json')
                return json.dumps(INVENTORY)
            def resolve(self, strict):
                self_outer.assertTrue(strict)
                self_outer.assertIn(self.value, ('/kernel/pkg/arvo/ted/test.hoon', '/kernel/pkg/arvo/mar/path.hoon'))
                return self
            def is_relative_to(self, value): return value == '/kernel'
            def stat(self):
                self_outer.assertEqual(self.value, '/state/logs/zod.log')
                return SimpleNamespace(st_size=0)
            def open(self, mode):
                self_outer.assertEqual((self.value, mode), ('/state/logs/zod.log', 'rb'))
                return io.BytesIO(b'')
        self_outer = self
        def command(ship, source, expected=None):
            self.assertEqual(ship, 'zod')
            if source.startswith('`path`%'): return source[len('`path`%'):]
            self.assertEqual(expected, '%.y')
            self.assertIn('/=base=/', source)
            return '%.y'
        def execute(binary, socket, resolved, timeout=60):
            observed.append((resolved, timeout))
            if transport_failure:
                raise TimeoutError('inert transport timeout')
            entry = next(row for row in [*INVENTORY['suites'], INVENTORY['negative_control']] if row['path'] == resolved)
            negative = resolved == EXPECTED[-1]
            terminal = 'built   ' + resolved + '/hoon\n'
            if negative: terminal += 'stead-intentional-native-unit-failure\n'
            terminal += ''.join(('FAILED ' if negative else 'OK ') + resolved + '/' + arm + '\n' for arm in entry['arms'])
            terminal += '[32 %avow 0 %noun ' + ('1' if negative else '0') + ']\n'
            if corrupt and resolved == EXPECTED[0]: terminal = '[32 %avow 0 %noun 0]\n'
            return {'stdout': terminal}
        node = next(n for n in ast.walk(ast.parse(SOURCE)) if isinstance(n, ast.FunctionDef) and n.name == 'pure_units')
        module = ast.Module(body=[copy.deepcopy(node)], type_ignores=[])
        namespace = {'native_units': UNITS, 'json': json, 'Path': FixedPath, 'report': report,
                     'binary': 'inert', 'sha': lambda path: '00' * 32,
                     'core_conn': SimpleNamespace(atom=lambda value: 0), 'command': command,
                     'checkpoint': checkpoints.append, 'check': lambda name, value: checks.append((name, value)),
                     'time': SimpleNamespace(monotonic=lambda: 1.0),
                     'host': {'LIVE': FixedPath('/owned'), 'execution_check': lambda: None,
                              'record': lambda name, value: None}}
        exec(compile(ast.fix_missing_locations(module), '<exact-pinned-pure-units>', 'exec'), namespace)
        with mock.patch.object(UNITS, 'run', side_effect=execute):
            try:
                namespace['pure_units']()
            except Exception as error:
                return error, report, observed, checkpoints, checks
        self.fail('Diagnostic collector must never return normally')

    def test_inventory_exact_registry_and_ten_new_arms(self):
        self.assertIs(UNITS.validate_inventory(INVENTORY), INVENTORY)
        self.assertEqual((INVENTORY['expected_arm_count'], len(INVENTORY['suites'])), (339, 50))
        selected = [row for row in INVENTORY['suites'] if row['path'] in EXPECTED]
        self.assertEqual([len(row['arms']) for row in selected], [6, 4])
        for entry in selected:
            source = (ROOT / ('native/core/desk' + entry['path'] + '.hoon')).read_text()
            actual = [line[4:] for line in source.splitlines() if line.startswith('++  test-')]
            self.assertEqual(entry['arms'], actual)

    def test_registry_rejects_missing_unknown_count_name_and_deadline(self):
        variants = []
        for key, value in [('timeout_seconds', 61), ('timeout_seconds', True), ('arms', ['test-repository-catalog-unknown'])]:
            item = copy.deepcopy(INVENTORY); row = next(r for r in item['suites'] if r['path'] == EXPECTED[0]); row[key] = value; variants.append(item)
        item = copy.deepcopy(INVENTORY); item['suites'].pop(); variants.append(item)
        item = copy.deepcopy(INVENTORY); item['suites'][-1]['path'] = '/tests/not-admitted'; variants.append(item)
        for count in (338, 339.0, True):
            item = copy.deepcopy(INVENTORY); item['expected_arm_count'] = count; variants.append(item)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(ValueError): UNITS.validate_inventory(item)

    def test_actual_collector_selects_only_ten_and_negative_then_always_fails(self):
        error, report, observed, checkpoints, checks = self.invoke()
        self.assertIs(type(error), ValueError)
        self.assertEqual(str(error), 'Pure-unit diagnostic complete; qualification disabled')
        self.assertEqual([path for path, _ in observed], list(EXPECTED))
        self.assertTrue(all(timeout == 60 for _, timeout in observed))
        self.assertEqual([row['outcome'] for row in report['native_units']], ['passed', 'passed', 'expected-failure'])
        self.assertEqual(report['native_unit_failures'], [])
        self.assertTrue(report['diagnostic_only'])
        self.assertEqual(len(checks), 3)

    def test_completed_invalid_suite_is_retained_and_remaining_scope_runs(self):
        error, report, observed, checkpoints, checks = self.invoke(corrupt=True)
        self.assertIs(type(error), ValueError)
        self.assertEqual(str(error), 'Pure-unit diagnostic complete; qualification disabled')
        self.assertEqual([path for path, _ in observed], list(EXPECTED))
        self.assertEqual(report['native_unit_failures'], [EXPECTED[0]])
        self.assertEqual([row['path'] for row in report['native_units']], list(EXPECTED[1:]))
        self.assertIn('native-unit-diagnostic-failure', checkpoints)

    def test_transport_failure_propagates_without_running_later_suites(self):
        error, report, observed, checkpoints, checks = self.invoke(transport_failure=True)
        self.assertIs(type(error), TimeoutError)
        self.assertEqual([path for path, _ in observed], [EXPECTED[0]])
        self.assertEqual(report['native_units'], [])
        self.assertEqual(report['native_unit_failures'], [])
        self.assertEqual(checks, [])
        self.assertEqual(len(report['native_unit_transcripts']), 1)

    def test_original_app_build_is_before_scoped_units(self):
        tree = ast.parse(SOURCE)
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        build = [node for node in calls if node.func.id == 'build_probe']
        units = [node for node in calls if node.func.id == 'pure_units']
        self.assertEqual((len(build), len(units)), (1, 1))
        self.assertLess(build[0].lineno, units[0].lineno)
        self.assertEqual(ast.unparse(build[0]), 'build_probe(ship, command, report, checkpoint)')


if __name__ == '__main__':
    unittest.main()
