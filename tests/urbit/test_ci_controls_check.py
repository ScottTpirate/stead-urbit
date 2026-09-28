"""Mocked native control outcomes; exercise diagnostic binding and cleanup."""
from contextlib import ExitStack
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/urbit'))
import ci_controls_check as lane


class CiControlsDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'logs').mkdir()
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(lane,'tree_sha',side_effect=lambda p:'ci' if p==Path('/ci') else 'native'))
        self.stack.enter_context(patch.object(lane,'source_sha',return_value='loaded'))
        self.context={'trees':{'scripts/ci':'ci'}}
        self.stack.enter_context(patch.object(lane.execution_policy,'read_json',return_value=self.context))
        def copytree(source,destination):
            destination.mkdir()
            for group in ('controls','ted'): (destination/group).mkdir()
        self.stack.enter_context(patch.object(lane.shutil,'copytree',side_effect=copytree))
        self.stack.enter_context(patch.object(lane.shutil,'copyfile'))
        self.stack.enter_context(patch.object(lane.native_install,'install',return_value={'fixture':'mocked'}))
        self.native=Mock(return_value={'classification':'mocked-native'})
        self.module=SimpleNamespace(native=self.native)
        self.stack.enter_context(patch.object(lane.importlib.util,'spec_from_file_location',return_value=SimpleNamespace(loader=SimpleNamespace(exec_module=lambda _:None))))
        self.stack.enter_context(patch.object(lane.importlib.util,'module_from_spec',return_value=self.module))
        self.host={'STATE':self.root,'TEAM':object(),'LOADED_SOURCE_DIGEST':'loaded',
            **{name:Mock() for name in ('execution_check','all_stop','copy_seed_to_live','launch','wait_ready','dojo')}}

    def report(self):
        return json.loads(next((self.root/'logs').glob('core-ci-controls-*.json')).read_text())

    def test_one_fake_result_is_bound_and_always_stopped(self):
        result=lane.run(self.host)
        self.assertEqual(result['status'],'pass');self.assertFalse(result['qualifies_phase'])
        self.host['launch'].assert_called_once_with('zod',fresh=True)
        self.assertEqual(self.host['all_stop'].call_count,2)
        self.assertEqual(self.report()['inputs_before'],self.report()['inputs_after'])
        self.assertIsNone(self.native.call_args.args[1])

    def test_changed_controller_cannot_launch(self):
        self.context['trees']['scripts/ci']='changed'
        self.assertEqual(lane.run(self.host)['status'],'fail')
        self.host['launch'].assert_not_called();self.native.assert_not_called()

    def test_native_and_cleanup_failures_never_pass(self):
        def failed(*args,progress):
            progress('compiler',{'classification':'mocked-native','native_failure':{'stage':'parse-terminal'}})
            raise ValueError('synthetic compiler verdict mismatch')
        self.native.side_effect=failed
        self.assertEqual(lane.run(self.host)['status'],'fail')
        self.assertIn('synthetic compiler verdict mismatch',self.report()['error'])
        self.assertEqual(self.report()['control_observations']['compiler']['native_failure']['stage'],'parse-terminal')
        self.native.side_effect=None
        self.host['all_stop'].side_effect=[None,RuntimeError('synthetic cleanup failure')]
        self.assertEqual(lane.run(self.host)['status'],'fail')
        self.assertFalse(self.report()['cleanup'])
