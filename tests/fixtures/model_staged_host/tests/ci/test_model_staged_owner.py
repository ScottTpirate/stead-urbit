"""Inert staged-owner regressions. Real temporary stream bytes, explicit process/lease doubles.
No evaluator, namespace, signal, service, network or privileged operation executes.
"""
from contextlib import ExitStack
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'scripts/ci/pure_eval'


def load(name):
    path = PACKAGE / (name + '.py')
    spec = importlib.util.spec_from_file_location('stage_test_' + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = load('owner_boundary')
with mock.patch.dict(sys.modules, {'owner_boundary': B}):
    C = load('owner_collection')
W = load('worker')
S = load('stage_codec')


def job(label='model-codec-stage-core'):
    raw = label.encode()
    return dict(label=label, kind='suite', source=raw,
                source_sha256=hashlib.sha256(raw).hexdigest(), timeout_seconds=85, arms=())


def stream(raw):
    return dict(present=True, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                base64=base64.b64encode(raw).decode())


class StagedOwnerTests(unittest.TestCase):
    def evaluate_deadline(self, *, retain=True, lease_fault=False, stop_fault=False):
        calls = []
        process = types.SimpleNamespace(pid=1234, returncode=None)
        process.poll = lambda: process.returncode
        def popen(argv, **kw):
            self.assertEqual(kw['stdin'].read(), b'model-codec-stage-core')
            kw['stdout'].write(b'partial stdout\x00')
            kw['stderr'].write(b'partial stderr\n')
            kw['stdout'].flush(); kw['stderr'].flush()
            calls.append('spawn')
            return process
        def stop(child, pidfd):
            self.assertIs(child, process)
            self.assertEqual(pidfd, 77)
            calls.append('stop')
            process.returncode = -15
            if stop_fault:
                raise OSError('authored owned-stop refusal')
        def lease():
            calls.append('lease')
            if lease_fault and process.returncode is not None:
                raise ValueError('authored expired lease after stop')
        original_temporary_file = tempfile.TemporaryFile
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            stack.enter_context(mock.patch.object(W.tempfile, 'TemporaryFile',
                side_effect=lambda **_: original_temporary_file(dir=directory)))
            stack.enter_context(mock.patch.object(W.subprocess, 'Popen', side_effect=popen))
            stack.enter_context(mock.patch.object(W.os, 'pidfd_open', return_value=77))
            stack.enter_context(mock.patch.object(W.os, 'close', side_effect=lambda fd: calls.append(('close', fd))))
            stack.enter_context(mock.patch.object(W, 'stop', side_effect=stop))
            stack.enter_context(mock.patch.object(W, 'process_ids', return_value={1, 42}))
            stack.enter_context(mock.patch.object(W.time, 'monotonic', side_effect=[0.0, 85.0, 85.01]))
            with self.assertRaises(TimeoutError) as found:
                W.evaluate(job(), types.SimpleNamespace(command=lambda argv: argv),
                    types.SimpleNamespace(check=lease), {1, 42}, 525, retain_interruption=retain)
        return found.exception, calls

    def test_actual_anonymous_bytes_are_retained_after_owned_stop(self):
        error, calls = self.evaluate_deadline()
        self.assertEqual(error.pure_interruption, (-15, 85010, b'partial stdout\x00', b'partial stderr\n'))
        self.assertLess(calls.index('stop'), len(calls) - 1)
        self.assertEqual(calls[-1], ('close', 77))
        self.assertFalse(getattr(error, 'pure_cleanup_failed', False))
        error, calls = self.evaluate_deadline(retain=False)
        self.assertFalse(hasattr(error, 'pure_interruption'))
        self.assertEqual(calls[-1], ('close', 77))

    def test_retention_faults_preserve_deadline_and_close_owned_descriptor(self):
        for lease_fault, stop_fault in ((True, False), (False, True)):
            with self.subTest(lease_fault=lease_fault, stop_fault=stop_fault):
                error, calls = self.evaluate_deadline(lease_fault=lease_fault, stop_fault=stop_fault)
                self.assertEqual(str(error), 'Fixed evaluator job deadline')
                self.assertFalse(hasattr(error, 'pure_interruption'))
                self.assertEqual(calls[-1], ('close', 77))
                self.assertEqual(getattr(error, 'pure_cleanup_failed', False), stop_fault)

    def test_interrupted_record_budget_is_atomic_and_has_no_observation(self):
        report = {'protocol':'stead.fixed-staged-pure-eval-report/1', 'interruption':None,
                  'records':[], 'budget_stop':None}
        error = TimeoutError('authored deadline')
        error.pure_interruption = (-15, 85001, b'partial', b'error')
        W.retain_deadline_interruption(report, job(), error, {}, (job(),))
        self.assertEqual(report['records'], [])
        self.assertEqual(set(report['interruption']), {'label','source_sha256','source_bytes',
            'reason','elapsed_ms','stdout','stderr','exit_code'})
        self.assertEqual(report['interruption']['stdout'], stream(b'partial'))
        short = dict(report, interruption=None)
        with mock.patch.object(W, 'STAGING_LIMIT', 1):
            W.retain_deadline_interruption(short, job(), error, {}, (job(),))
        self.assertIsNone(short['interruption'])
        self.assertEqual(short['records'], [])
        self.assertEqual(short['budget_stop']['label'], job()['label'])
        self.assertGreater(short['budget_stop']['bytes'], 1)

    def report_fixture(self):
        jobs = tuple(job(n) for n in ('compiler-control','failing-tang-control',*S.LABELS))
        observations = [dict(status='pass'),dict(status='pass'),
            dict(status='pass',stage={'boundary':'core-ready','core_mug':9,'formula_mug':None})]
        records = [dict(label=j['label'],source_sha256=j['source_sha256'],source_bytes=len(j['source']),
            exit_code=0,stdout=stream(str(i).encode()),stderr=stream(b''),observation=observations[i],elapsed_ms=100)
            for i,j in enumerate(jobs[:3])]
        interrupted = dict(label=jobs[3]['label'],source_sha256=jobs[3]['source_sha256'],
            source_bytes=len(jobs[3]['source']),reason='evaluator-deadline',elapsed_ms=85001,
            stdout=stream(b'partial'),stderr=stream(b'native tail'),exit_code=-15)
        report = dict(protocol='stead.fixed-staged-pure-eval-report/1',status='fail',qualifies_phase=False,
            composition_sha256=S.COMPOSITION_SHA256,runtime_sha256=W.RUNTIME_SHA,records=records,
            source_hashes_before={'input':'f'*64},source_hashes_after={},budget_stop=None,
            error_class='TimeoutError',children_reaped=True,namespace_baseline_restored=True,
            expected_positive_arms=1,expected_controls=2,native_application_executed=False,
            interruption=interrupted)
        codec = types.SimpleNamespace(job_profile=lambda jobs:S.profile(),
            observe=lambda job, code, out, err:observations[int(out)],
            validate_staged_records=S.validate_records)
        return report,codec,jobs

    def test_owner_verifies_next_job_raw_bytes_types_and_completed_prefix(self):
        report,codec,jobs = self.report_fixture()
        checked = C.validate_report(C.canonical(report),codec,jobs,{'input':'f'*64})
        self.assertEqual(checked,report)
        changes = [lambda r:r['interruption'].update(label=S.LABELS[2]),
            lambda r:r['interruption'].update(label='compiler-control'),
            lambda r:r['interruption'].update(elapsed_ms=True),
            lambda r:r['interruption'].update(exit_code=False),
            lambda r:r['interruption']['stdout'].update(sha256='0'*64),
            lambda r:r['interruption']['stderr'].update(base64='Zg==='),
            lambda r:r['records'][2].update(elapsed_ms=540001),
            lambda r:r['records'][2].update(elapsed_ms=500000),
            lambda r:r['records'][0].update(observation=None),
            lambda r:r.update(error_class='ValueError'),
            lambda r:r.update(source_hashes_after={'input':'f'*64}),
            lambda r:r.update(protocol='stead.fixed-pure-eval-report/1')]
        for change in changes:
            wrong=copy.deepcopy(report);change(wrong)
            with self.subTest(change=repr(change)),self.assertRaises((ValueError,TypeError)):
                C.validate_report(C.canonical(wrong),codec,jobs,{'input':'f'*64})

    def test_original_report_schema_does_not_accept_interruption_or_timing(self):
        report,codec,jobs=self.report_fixture()
        selected=dict(S.profile(),name='native-model-simple/1',composition_sha256=W.MODEL_COMPOSITION_SHA,positive_arms=18)
        codec.job_profile=lambda jobs:selected
        report.update(protocol='stead.fixed-pure-eval-report/1',composition_sha256=W.MODEL_COMPOSITION_SHA,expected_positive_arms=18)
        report.pop('interruption')
        for record in report['records']:record.pop('elapsed_ms')
        C.validate_report(C.canonical(report),codec,jobs,{'input':'f'*64})
        for field,value in [('interruption',None),('elapsed_ms',1)]:
            wrong=copy.deepcopy(report)
            if field=='interruption':wrong[field]=value
            else:wrong['records'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                C.validate_report(C.canonical(wrong),codec,jobs,{'input':'f'*64})

    def test_staged_envelope_uses_exact_original_twenty_one_source_bytes(self):
        # Traversal/root metadata are inert doubles; actual fixture bytes and
        # digest checks are real. The independently pinned envelope selects no paths.
        envelope = json.loads((PACKAGE / 'model_data/staged-composition.json').read_bytes())
        base = json.loads(envelope['base_composition'])
        names = set(base['sources']) | {base['composition']['test_helper']['path']}
        fixture = ROOT / 'tests/fixtures/model-staged'
        originals = {name:(fixture / name).read_bytes() for name in names}
        self.assertEqual(len(originals),21)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name,raw in originals.items():
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            def exact(path, expected):
                raw=path.read_bytes()
                W.require({'bytes':len(raw),'sha256':W.sha(raw)} == expected)
                return raw
            with mock.patch.object(W,'SOURCES',root),mock.patch.object(W.os,'walk',return_value=[(str(root),[],list(originals))]),mock.patch.object(W,'exact_file',side_effect=exact):
                files, hashes = W.source_inventory(envelope,W.STAGED_COMPOSITION_SHA)
                self.assertEqual(files,originals)
                self.assertEqual(hashes,{name:W.sha(raw) for name,raw in originals.items()})
                for base in ('',envelope['base_composition']+'\n',None):
                    wrong=dict(envelope,base_composition=base)
                    with self.subTest(base_type=type(base).__name__),self.assertRaises(ValueError):
                        W.source_inventory(wrong,W.STAGED_COMPOSITION_SHA)
                for names in (list(originals)[:-1],[*originals,'ambient.hoon']):
                    with mock.patch.object(W.os,'walk',return_value=[(str(root),[],names)]),self.assertRaises(ValueError):
                        W.source_inventory(envelope,W.STAGED_COMPOSITION_SHA)
                target=root/'native/core/desk/lib/stead-model-codec.hoon'
                target.write_bytes(target.read_bytes()+b'\n')
                with self.assertRaises(ValueError):W.source_inventory(envelope,W.STAGED_COMPOSITION_SHA)
