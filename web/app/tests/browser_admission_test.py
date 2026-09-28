"""Synthetic admission records and real file refusals; no native/browser run."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'web/app'), str(ROOT / 'scripts/urbit')]
import browser_admission as admission


class BrowserAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.reference = {'file': 'team-check-20260927T120000Z.json', 'sha256': 'b' * 64}
        self.status = {'profile': 'configured-team', 'stage': 'ready', 'ready': True,
            'execution_guard': {'state': 'running', 'run_id': 'a' * 32}, 'team_evidence': self.reference,
            'ships': {ship: {'pid': index + 10, 'exit': None} for index, ship in enumerate(('zod','bus','nec','bud'))}}
        self.inputs = {'native': 'c' * 64, 'harness': 'd' * 64, 'runner': {'probe.py': 'e' * 64}}
        self.installed = {'app/stead-home.hoon': 'f' * 64}
        self.native = {'status': 'pass', 'stage': 'completed', 'classification': 'local-real-configured-gall-development',
            'execution_guard': {'run_id': 'a' * 32}, 'inputs_before': self.inputs, 'inputs_after': self.inputs,
            'installed': {ship: self.installed for ship in self.status['ships']},
            'checks': [{'name': 'synthetic-control', 'passed': True}],
            'restarts': {ship: {'passed': True} for ship in self.status['ships']}}
        self.expected = {'execution_id': 'a' * 32, 'native_prerequisite': self.reference, 'runner': 'e' * 64}
        self.transport = {'classification': 'local-real-browser-native-tls', 'status': 'pass',
            'inputs_before': self.expected, 'inputs_after': self.expected, 'browser_process': {'cleanup': {'empty': True}}}
        self.journey = {'classification': 'real-browser-native-gall', 'status': 'pass', 'execution_id': 'a' * 32,
            'checks': [{'name': 'synthetic-control', 'passed': True}]}

    def test_unready_failed_foreign_and_missing_live_binding_refused(self):
        self.assertEqual(admission.live_reference(self.status), self.reference)
        for delta in ({'ready': False}, {'stage': 'compiling'}, {'profile': 'legacy-fixture'},
                {'execution_guard': {'state':'stopped','run_id':'a'*32}}, {'ships': {}}, {'team_evidence': None},
                {'team_evidence': {**self.reference, 'file': '../team-check-20260927T120000Z.json'}}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                admission.live_reference({**self.status, **delta})
        dead = copy.deepcopy(self.status)
        dead['ships']['bus']['exit'] = 0
        with self.assertRaises(ValueError):
            admission.live_reference(dead)

    def test_native_report_binds_source_installed_bytes_guard_checks_and_restarts(self):
        admission.verify_native(self.native, self.status, self.inputs, self.installed)
        for delta in ({'status':'fail'}, {'stage':'running'}, {'execution_guard':{'run_id':'b'*32}},
                {'inputs_before':{}}, {'inputs_after':{}}, {'installed':{}}, {'checks':[]},
                {'checks':[{'name':'failed','passed':False}]}, {'restarts':{}}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                admission.verify_native({**self.native, **delta}, self.status, self.inputs, self.installed)
        with self.assertRaises(ValueError):
            admission.verify_native(self.native, self.status, {**self.inputs, 'native':'0'*64}, self.installed)
        with self.assertRaises(ValueError):
            admission.verify_native(self.native, self.status, self.inputs, {'app/stead-home.hoon':'0'*64})
        with self.assertRaises(ValueError):
            admission.verify_native(self.native, self.status, self.inputs, {})

    def test_browser_requires_matching_transport_journey_and_completed_cleanup(self):
        admission.verify_browser(self.transport, self.journey, self.expected)
        for delta in ({'status':'fail'}, {'classification':'rendered-mock'}, {'inputs_before':{}},
                {'inputs_after':{}}, {'browser_process':{'cleanup':{'empty':False}}}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                admission.verify_browser({**self.transport, **delta}, self.journey, self.expected)
        for delta in ({'status':'fail'}, {'execution_id':'b'*32}, {'checks':[]}, {'classification':'mock'}):
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                admission.verify_browser(self.transport, {**self.journey, **delta}, self.expected)
        with self.assertRaises(ValueError):
            admission.verify_browser(self.transport, self.journey, {**self.expected,'native_prerequisite':{**self.reference,'sha256':'f'*64}})

    def test_actual_report_bytes_must_match_the_live_supervisor_digest(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as folder:
            state = Path(folder); (state / 'logs').mkdir()
            path = state / 'logs' / self.reference['file']
            raw = json.dumps(self.native).encode()
            path.write_bytes(raw); path.chmod(0o600)
            status = copy.deepcopy(self.status)
            status['team_evidence']['sha256'] = hashlib.sha256(raw).hexdigest()
            with patch.object(admission, 'native_inputs', return_value=self.inputs), \
                    patch.object(admission, 'source_inventory', return_value=self.installed):
                self.assertEqual(admission.require_native(ROOT,state,status), status['team_evidence'])
                path.write_bytes(raw + b'\n')
                with self.assertRaisesRegex(ValueError, 'live supervisor binding'):
                    admission.require_native(ROOT,state,status)

    def test_journey_file_is_digest_bound_and_browser_name_is_fixed(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as folder:
            root = Path(folder); (root / '.runtime').mkdir()
            name = 'browser-native-20260927T120000Z'
            output = root / '.runtime' / name; output.mkdir(mode=0o700)
            raw = json.dumps(self.journey).encode()
            (output / 'browser-report.json').write_bytes(raw)
            (output / 'transport-report.json').write_text(json.dumps({**self.transport,'journey_sha256':hashlib.sha256(raw).hexdigest()}))
            for path in output.iterdir(): path.chmod(0o600)
            with patch.object(admission, 'require_native', return_value=self.reference), \
                    patch.object(admission, 'browser_inputs', return_value=self.expected):
                result = admission.require_browser(root, root, self.status, name)
                self.assertEqual(result['journey_sha256'], hashlib.sha256(raw).hexdigest())
                for bad in ('../'+name, 'browser-expiry-20260927T120000Z', name+'/'):
                    with self.assertRaises(ValueError): admission.require_browser(root,root,self.status,bad)
                (output / 'browser-report.json').write_bytes(raw+b'\n')
                with self.assertRaisesRegex(ValueError, 'transport binding'):
                    admission.require_browser(root,root,self.status,name)

    def test_redirected_parent_duplicate_keys_and_public_file_refused(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as folder:
            root = Path(folder); real = root / 'real'; real.mkdir()
            path = real / 'input.json'; path.write_bytes(b'{"a":1,"a":2}'); path.chmod(0o600)
            with self.assertRaisesRegex(ValueError, 'Duplicate'): admission.private_json(path,100)
            path.write_bytes(b'{"a":1}'); path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'private'): admission.private_json(path,100)
            path.chmod(0o600); (root / 'alias').symlink_to(real, target_is_directory=True)
            before = set(os.listdir('/proc/self/fd'))
            with self.assertRaises(OSError): admission.private_json(root/'alias/input.json',100)
            self.assertEqual(set(os.listdir('/proc/self/fd')),before)

    def test_frontend_build_must_match_packaged_native_bytes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.runtime') as folder:
            root = Path(folder)
            (root / 'web/app/dist').mkdir(parents=True)
            target = root / 'native/core/desk/web/stead'; target.mkdir(parents=True)
            body = b'synthetic public asset'
            digest = hashlib.sha256(body).hexdigest()
            asset = target / ('asset-'+digest+'.stead-asset'); asset.write_bytes(body)
            manifest = root / 'web/app/dist/manifest.json'
            raw = json.dumps({'format':1,'classification':'frontend-build-only',
                'files':{'index.html':{'bytes':len(body),'sha256':digest}}}).encode()
            manifest.write_bytes(raw)
            self.assertEqual(admission.frontend_binding(root),hashlib.sha256(raw).hexdigest())
            asset.write_bytes(b'x'*len(body))
            with self.assertRaisesRegex(ValueError,'packaged native'): admission.frontend_binding(root)
            asset.unlink()
            with self.assertRaises(FileNotFoundError): admission.frontend_binding(root)
            asset.symlink_to(manifest)
            with self.assertRaises(OSError): admission.frontend_binding(root)
            manifest.write_text('{"format":1,"classification":"frontend-build-only","files":{}}')
            with self.assertRaises(ValueError): admission.frontend_binding(root)
