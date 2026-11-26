"""Seven inert groups. No native, namespace, service, socket or model execution.

Temporary bytes are explicitly host-only vectors, never actual saved nouns.
Privileged metadata and process boundaries are mocked; archive bytes, hashes,
canonical frames and exclusive temporary-file writes use the real helpers.
"""
from __future__ import annotations
import ast
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
from importlib.machinery import PathFinder
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
CI = ROOT / 'scripts/ci'
PACKAGE = CI / 'home_asset_rehearsal'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Restore every temporary module binding and sys.path after source imports.
# Modules themselves retain their direct references; unrelated suites see no replacement.
_names = ('home_asset_rehearsal', 'home_asset_rehearsal.evidence', 'home_asset_rehearsal.result',
    'home_asset_rehearsal.service_adapter', 'execution_policy', 'hosted_apparmor', 'hosted_lease',
    'result', 'saved8_outer_worker')
_prior_path = list(sys.path)
_missing = object()
_prior_modules = {name: sys.modules.get(name, _missing) for name in _names}
try:
    _package = types.ModuleType('home_asset_rehearsal')
    _package.__path__ = [str(PACKAGE)]
    sys.modules['home_asset_rehearsal'] = _package
    E = load('home_asset_rehearsal.evidence', PACKAGE / 'evidence.py')
    R = load('home_asset_rehearsal.result', PACKAGE / 'result.py')
    A = load('home_asset_rehearsal.service_adapter', PACKAGE / 'service_adapter.py')
    P = load('execution_policy', ROOT / 'scripts/urbit/execution_policy.py')
    H = load('hosted_apparmor', CI / 'hosted_apparmor.py')
    L = load('hosted_lease', CI / 'hosted_lease.py')
    sys.modules['result'] = R
    W = load('saved8_outer_worker', PACKAGE / 'worker.py')
finally:
    sys.path[:] = _prior_path
    for name, module in _prior_modules.items():
        if module is _missing:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = module


# Test-only readonly chunks preserve the host's unchanged 1 MiB file limit.
# Runtime archives remain exact full tar files; no host fixture is runtime evidence.
ARCHIVE_CHUNKS = {'previous': [('previous-0.chunk', 524288, 'ff40efb3c3f8351cd7dc6f33e008e22a59ffae8510838032027597f65330fde3'), ('previous-1.chunk', 524288, 'c47dcb795b056405c06fb004c015e4c0d5498d5c78dc49ab20aea414f4233b9a'), ('previous-2.chunk', 344064, 'dee3742b0aeb62d9cfd357b04e1d3f9a5bec1953cfaaaa9aad95515982357e03')], 'target': [('target-0.chunk', 524288, 'ff40efb3c3f8351cd7dc6f33e008e22a59ffae8510838032027597f65330fde3'), ('target-1.chunk', 524288, '9db277dd1c570f46c3605e61ed10d1418cd51f8470fa25543fe0151320230871'), ('target-2.chunk', 524288, '36ece196aaed5c25db52f741975d8539fa0ec1d116aef3cccc2b36b4aaaadf42'), ('target-3.chunk', 75776, '0059daddeb4524e1c4cc04d5827123c1ecd272f1a6b8e612eb713917ccbd486c')]}


def archive_bytes(name):
    if name not in ('previous', 'target'):
        raise ValueError('Fixed test archive only')
    values = []
    for basename, size, digest in ARCHIVE_CHUNKS[name]:
        path = ROOT / 'tests/ci/fixtures/home_asset_outer' / basename
        raw = path.read_bytes()
        if path.is_symlink() or len(raw) != size or size > 524288 or E.sha(raw) != digest:
            raise ValueError('Fixed archive chunk differs')
        values.append(raw)
    result = b''.join(values)
    if (len(result), E.sha(result)) != A.DATA[name + '.tar']:
        raise ValueError('Fixed complete archive differs')
    return result


def literal(name, path):
    for node in ast.parse(path.read_bytes()).body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(name)


def synthetic():
    """Closed host fixture; no Python cue and no native-producer claim."""
    inputs = {'guardian_files': {'worker.py': '1' * 64, 'result.py': '2' * 64},
        'source_files': {path: dict.fromkeys(names, 'c' * 64) for path, names in W.SOURCE_NAMES.items()},
        'desk_hashes': dict.fromkeys(E.STAGES, '3' * 64),
        'assets': {'previous': [{'route': '/stead/', 'sha256': '4' * 64, 'bytes': 3}],
                   'target': [{'route': '/stead/', 'sha256': '5' * 64, 'bytes': 4}],
                   'delta': {'removed': [], 'updated': ['web/stead/inventory.hoon']}}}
    context = {'host_only': True}
    expected = {'run_id': '1' * 32, 'controller_commit': '2' * 40,
        'inputs_sha256': E.sha(E.canonical(inputs)), 'worker_sha256': inputs['guardian_files']['worker.py'],
        'guardian_sources_sha256': E.sha(E.canonical(inputs['guardian_files']))}
    context_sha = E.sha(E.canonical(context))
    proof = {'capabilities': dict.fromkeys(('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd'), '0000000000000000') | {'NoNewPrivs': '1'},
        'udp': '0100007F:7A69', 'uid_map': ['0', '1001', '1'], 'gid_map': ['0', '1002', '1'], 'uid': 0, 'gid': 0,
        'namespaces': {n: n + ':[123]' for n in ('user', 'pid', 'mnt', 'net')}, 'lens_ports': [18080]}
    boot = lambda pid: {'identity': '~zod', 'boot_seconds': 1.5, 'pid': pid, 'proof': deepcopy(proof)}
    report = {'protocol': 'stead.saved8-asset-rehearsal/1', 'status': 'pass',
        'classification': 'disposable-synthetic-saved8-only', 'saved_version': 8,
        'qualifies_phase': False, 'live_pier_used': False, 'browser_authentication': False,
        'error_class': 'none', 'cleanup_error_class': 'none', 'phases': list(R.PHASES),
        'captures': {}, 'capture_custody': {}, 'commands': [{'source_sha256': '6' * 64, 'source_bytes': 5,
            'output_sha256': '7' * 64, 'output_bytes': 0}], 'restarts': [], 'elapsed_ms': 20,
        **{k: expected[k] for k in ('run_id', 'controller_commit', 'inputs_sha256')},
        'previous_artifact': R.PREVIOUS, 'target_artifact': R.NEXT, 'asset_delta': inputs['assets']['delta'],
        'boot': boot(11), 'tls': {'hostname': 'home.localhost', 'certificate_sha256': '8' * 64,
            'protocol': 'TLSv1.3', 'owned_listeners': [{'endpoint': '0100007F:480B', 'inode': '14'}]}, 'cleanup': dict(R.CLEAN)}
    for stage, pid in (('cold', 12), ('rollback-cold', 13)):
        report['restarts'].append({'stage': stage, 'cleanup': dict(R.CLEAN), 'boot': boot(pid),
            'checkpoint': {'sha256': '9' * 64, 'bytes': 1, 'files': 1}})
    for i, name in enumerate(R.READY):
        report[name] = {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~zod',
            'nonce': E.sha(('nonce' + str(i)).encode()), 'incarnation': E.sha(('incarnation' + str(i)).encode())}
    for name in R.ROUTES:
        report[name] = {'assets': deepcopy(inputs['assets']['target' if name == 'routes_assets' else 'previous']),
            'denials': list(R.DENIALS), 'native_tls': True, 'browser_authentication': False,
            'capabilities': dict(E.CAPABILITIES)}
    files = {}
    for stage in E.STAGES:
        raw = b'INERT_HOST_VECTOR_NOT_A_NATIVE_NOUN\x01'
        row = {'protocol': 'stead.saved8-capture-record/1', 'stage': stage, 'saved_version': 8,
            'artifact_bytes': len(raw), 'artifact_sha256': E.sha(raw), 'data': raw,
            **dict.fromkeys(E.PINS, 'a' * 64)}
        row['capture_pin'] = E.sha(b'stead.saved8-capture/1\0' + raw.hex().encode())
        report['captures'][stage] = E.metadata(row)
        custody = {'pid': 11 if stage in ('seed8', 'a0-loaded') else 12, 'process_proof_sha256': E.sha(E.canonical(proof)),
            'desk_inventory_sha256': inputs['desk_hashes'][stage], 'context_sha256': context_sha}
        report['capture_custody'][stage] = custody
        desc = E.metadata(row) | {k: expected[k] for k in ('run_id', 'controller_commit', 'inputs_sha256')} | {
            'previous_artifact_sha256': R.PREVIOUS, 'target_artifact_sha256': R.NEXT, 'runtime_sha256': R.RUNTIME,
            'kernel_commit': R.KERNEL, 'capture_custody': custody, 'qualifies_phase': False,
            'classification': 'synthetic-actual-saved8-rehearsal'}
        files[stage + '.jam'] = R.file_value(raw)
        files[stage + '.json'] = R.file_value(E.canonical(desc) + b'\n')
    value = {'protocol': 'stead.saved8-hosted-worker/1', **expected, 'status': 'pass', 'error_class': 'none',
        'cleanup': True, 'report': report, 'artifacts': files}
    return value, expected, inputs, context


def decode(value, expected, inputs, context):
    return R.decode(R.encode(value), expected, context_sha=E.sha(E.canonical(context)),
        desk_hashes=inputs['desk_hashes'], assets=inputs['assets'])


def guard_check():
    """Only the pinned pure cleanup predicate; no hosted bootstrap/import."""
    source = ast.parse((CI / 'hosted.py').read_bytes())
    node = next(x for x in source.body if isinstance(x, ast.FunctionDef) and x.name == 'require_collected_child')
    scope = {'require': lambda ok, message: R.require(ok)}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<fixed-cleanup-predicate>', 'exec', dont_inherit=True), scope)
    return scope['require_collected_child']


class Saved8OuterTests(unittest.TestCase):
    def test_full_native_capture_compression_is_bounded_and_reversible(self):
        import base64
        import zlib
        raw = b'abcd' * 925973
        encoded = R.file_value(raw)
        self.assertEqual(R.file_bytes(encoded, E.MAX_CAPTURE), raw)
        for payload in (b'', zlib.compress(raw + b'x'), zlib.compress(raw) + b'tailing'):
            other = dict(encoded, deflate_base64=base64.b64encode(payload).decode())
            with self.assertRaises(ValueError):
                R.file_bytes(other, E.MAX_CAPTURE)

    def test_fixed_archive_source_routes_and_command_schema(self):
        # Real filesystem resolution only: neither competing initializer executes.
        # The captured host package must win over a later regular package.
        with tempfile.TemporaryDirectory() as folder:
            later = Path(folder) / 'later'; later_package = later / 'home_asset_rehearsal'
            later_package.mkdir(parents=True)
            (later_package / '__init__.py').write_text("raise AssertionError('competing package executed')\n")
            (later_package / 'evidence.py').write_text("raise AssertionError('competing evidence executed')\n")
            spec = PathFinder.find_spec('home_asset_rehearsal', [str(CI), str(later)])
            self.assertEqual(Path(spec.origin), PACKAGE / '__init__.py')
            self.assertEqual(list(spec.submodule_search_locations), [str(PACKAGE)])
            self.assertIsNotNone(spec.loader)
            # A namespace-only first root really loses to the later regular package.
            bare = Path(folder) / 'bare'; (bare / 'home_asset_rehearsal').mkdir(parents=True)
            losing = PathFinder.find_spec('home_asset_rehearsal', [str(bare), str(later)])
            self.assertEqual(Path(losing.origin), later_package / '__init__.py')
            # Exercise the actual fixed child constructor with a private module table.
            # Its production path is asserted before mapping that one readonly root
            # to the host fixture solely for filesystem submodule resolution.
            fake_sys = types.SimpleNamespace(modules={})
            with mock.patch.object(W, 'sys', fake_sys):
                W.fixed_package()
            child = fake_sys.modules['home_asset_rehearsal']
            self.assertEqual(child.__package__, 'home_asset_rehearsal')
            self.assertEqual(child.__path__, ['/ci/home_asset_rehearsal'])
            mapped_path = [str(PACKAGE) if p == '/ci/home_asset_rehearsal' else p for p in child.__path__]
            child_spec = PathFinder.find_spec('home_asset_rehearsal.evidence', mapped_path)
            self.assertEqual(Path(child_spec.origin), PACKAGE / 'evidence.py')
            self.assertEqual(set(fake_sys.modules), {'home_asset_rehearsal'})
            # Only the real __main__ startup calls it, before the evidence import.
            worker_ast = ast.parse((PACKAGE / 'worker.py').read_bytes())
            startup = next(i for i, n in enumerate(worker_ast.body) if isinstance(n, ast.If)
                and any(isinstance(x, ast.Call) and isinstance(x.func, ast.Name)
                        and x.func.id == 'fixed_package' for x in ast.walk(n)))
            evidence_import = next(i for i, n in enumerate(worker_ast.body)
                if isinstance(n, ast.ImportFrom) and n.module == 'home_asset_rehearsal')
            self.assertLess(startup, evidence_import)
            self.assertEqual(ast.unparse(worker_ast.body[startup].test), "__name__ == '__main__'")
        # Real pinned archive bytes and full manifest hashes, not fabricated packages.
        prior, _, old, _ = A.archive(archive_bytes('previous'), 'previous')
        target, _, new, _ = A.archive(archive_bytes('target'), 'target')
        self.assertEqual((len(old), len(new)), (116, 118))
        self.assertEqual({n: v for n, v in prior.items() if n.startswith('desk/') and not n.startswith('desk/web/')},
                         {n: v for n, v in target.items() if n.startswith('desk/') and not n.startswith('desk/web/')})
        for raw, name in ((b'fake supplied vase', 'previous'), (archive_bytes('previous')[:-1] + b'x', 'previous'),
                          (archive_bytes('target'), 'previous')):
            with self.subTest(name=name, size=len(raw)), self.assertRaises(ValueError): A.archive(raw, name)
        for path, digest in A.FROZEN.items():
            self.assertEqual(E.sha((ROOT / path).read_bytes()), digest)
        # Derive the eleven return labels directly from the frozen producer AST.
        module = ast.parse((PACKAGE / 'runner.py').read_bytes())
        routes = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'routes')
        denied = next(n for n in routes.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'denied' for t in n.targets))
        names = [ast.literal_eval(row.elts[0]) for row in denied.value.elts]
        for node in routes.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'append':
                value = node.value.func.value
                if isinstance(value, ast.Subscript) and isinstance(value.slice, ast.Constant) and value.slice.value == 'denials':
                    names.append(ast.literal_eval(node.value.args[0]))
        self.assertEqual(names, R.DENIALS)
        self.assertEqual(names[-2:], ['plain-http', 'anonymous-protected-api'])
        pins = json.loads((ROOT / 'specs/urbit/toolchain.lock.json').read_bytes())
        h = types.SimpleNamespace(ROOT=Path('/owned'), local=types.SimpleNamespace(TEMP_BYTES=512*1024**2, STATE_BYTES=8*1024**3))
        context = {'fixed_profile': A.PROFILE, 'pins': pins, 'run_id': 'a' * 32, 'control_case': None}
        argv = A.command(h, Path('/job'), context)
        self.assertEqual(argv[-4:], ['/usr/bin/python3', '-I', '-B', '/guardian/worker.py'])
        self.assertEqual([argv[i+1] for i, v in enumerate(argv) if v == '--cap-add'], ['CAP_NET_ADMIN', 'CAP_SETPCAP'])
        self.assertNotIn('--bind', argv)
        self.assertNotIn('/native', argv)
        for bad in ({**context, 'fixed_profile': 'other'}, {**context, 'control_case': 'parent-death'}):
            with self.assertRaises(ValueError): A.command(h, Path('/job'), bad)
        workflow = (ROOT / '.github/workflows/native-hosted.yml').read_text()
        section = workflow.split('      - name: Publish fixed saved8 resource control evidence only\n', 1)[1]
        paths = [line.strip() for line in section.splitlines() if line.strip().startswith('/var/lib/')]
        controls = literal('CONTROL_CASES', CI / 'hosted.py')
        self.assertEqual(paths, ['/var/lib/stead-ci-controller/hosted-evidence/control-' + c + '-' + n + '.json' for c in controls for n in ('report', 'inputs')])
        main = next(n for n in ast.parse((CI / 'hosted.py').read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        self.assertTrue(any(isinstance(n, ast.Constant) and n.value == 'home-assets-saved8' for n in ast.walk(main)))

    def test_admission_map_source_and_lease_refusals(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root = Path(folder)
            for kind, owner in (('uid', 1001), ('gid', 1002)): (root / (kind + '_map')).write_text('0 ' + str(owner) + ' 1\n')
            real_path = Path
            stack.enter_context(mock.patch.object(W, 'Path', lambda p: root / real_path(p).name))
            for name in ('getuid', 'geteuid', 'getgid', 'getegid'): stack.enter_context(mock.patch.object(W.os, name, return_value=0))
            stack.enter_context(mock.patch.object(W.os, 'getgroups', return_value=[]))
            value = {'owner_uid': 1001, 'owner_gid': 1002}
            W.mapped_owner(value)
            for text in ('0 1003 1\n', '0 1001 1\n1 1004 1\n', '0 1001 2\n'):
                (root / 'uid_map').write_text(text)
                with self.subTest(map=text), self.assertRaises(ValueError): W.mapped_owner(value)
            (root / 'uid_map').write_text('0 1001 1\n')
            with self.assertRaises(ValueError): W.mapped_owner(value | {'owner_uid': True})
            with mock.patch.object(W.os, 'geteuid', return_value=1), self.assertRaises(ValueError): W.mapped_owner(value)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'one.py').write_bytes(b'exact source')
            # Privileged readonly/UID metadata mocked here; actual paths and SHA checked.
            with mock.patch.object(W, 'regular', side_effect=lambda p, maximum: Path(p).read_bytes()):
                W.source_tree(root, {'one.py': E.sha(b'exact source')})
                (root / 'one.py').write_bytes(b'changed')
                with self.assertRaises(ValueError): W.source_tree(root, {'one.py': E.sha(b'exact source')})
                (root / 'extra.py').write_bytes(b'extra')
                with self.assertRaises(ValueError): W.source_tree(root, {'one.py': E.sha(b'changed')})
            (root / 'link.py').symlink_to(root / 'one.py')
            with self.assertRaises((ValueError, OSError)): W.regular(root / 'link.py', 100, captured=True)
        # The fixed provider inherits all original source/lease/current checks.
        for name in ('require', '_require', 'observed', 'summary'):
            self.assertIs(getattr(W.FixedProvider, name), getattr(L.HostedProvider, name))
        provider = object.__new__(W.FixedProvider)
        provider.control, provider.run_id, provider.cpus, provider.guard_sha256 = Path('/execution'), 'a'*32, [0, 1], 'b'*64
        provider.previous = None
        with mock.patch.object(H, 'require_label', side_effect=P.GuardError('inert lease refusal')):
            with self.assertRaises(P.GuardError): provider._require()

    def test_exact_frame_artifacts_and_frozen_return_schema(self):
        value, expected, inputs, context = synthetic()
        observed, files = decode(value, expected, inputs, context)
        self.assertEqual(set(files), set(R.NAMES)); self.assertEqual(observed['status'], 'pass')
        for fault in ('missing', 'extra', 'wrong-bytes', 'wrong-type', 'wrong-descriptor', 'wrong-tail', 'wrong-context', 'missing-route', 'bad-cap', 'bad-cleanup'):
            bad = deepcopy(value)
            if fault == 'missing': del bad['artifacts']['seed8.jam']
            elif fault == 'extra': bad['artifacts']['other.jam'] = bad['artifacts']['seed8.jam']
            elif fault == 'wrong-bytes': bad['artifacts']['seed8.jam']['data_hex'] = '00' * bad['artifacts']['seed8.jam']['bytes']
            elif fault == 'wrong-type': bad['report']['saved_version'] = True
            elif fault == 'wrong-descriptor': bad['artifacts']['seed8.json']['sha256'] = '0' * 64
            elif fault == 'wrong-tail': bad['report']['captures']['a0-cold']['durable_pin'] = '0' * 64
            elif fault == 'wrong-context': bad['report']['capture_custody']['seed8']['context_sha256'] = '0' * 64
            elif fault == 'missing-route': bad['report']['routes_a0']['denials'].remove('plain-http')
            elif fault == 'bad-cap': bad['report']['routes_assets']['capabilities']['max_request_bytes'] = 65536
            else: bad['report']['cleanup']['reaped'] = False
            with self.subTest(fault=fault), self.assertRaises(ValueError): decode(bad, expected, inputs, context)
        for raw in (R.encode(value)[:-1], R.encode(value) + b'\n', R.PREFIX + b'{"x":1,"x":2}\n'):
            with self.assertRaises(ValueError): R.decode(raw, expected, context_sha=E.sha(E.canonical(context)), desk_hashes=inputs['desk_hashes'], assets=inputs['assets'])
        with self.assertRaises(ValueError): decode(value, expected | {'worker_sha256': '0'*64}, inputs, context)
        failed = R.failure(expected, 'runner-failed', cleanup=True)
        self.assertEqual(R.decode(failed, expected, context_sha='', desk_hashes={}, assets={})[1], {})
        row = json.loads(failed[len(R.PREFIX):]); row['artifacts'] = value['artifacts']
        with self.assertRaises(ValueError): decode(row, expected, inputs, context)

    def test_whole_frame_budget_and_failed_worker_preservation(self):
        # The exact aggregate bound includes framing, JSON, escaping and hex.
        blank = {'payload': ''}
        overhead = len(R.encode(blank))
        self.assertEqual(len(R.encode({'payload': 'x' * (R.MAX_FRAME - overhead)})), R.MAX_FRAME)
        with self.assertRaises(OverflowError): R.encode({'payload': 'x' * (R.MAX_FRAME - overhead + 1)})
        combined = {'report': 'x' * (2*1024**2), 'artifacts': {name: {'data_hex': (b'x'*E.MAX_CAPTURE).hex()} for name in R.NAMES if name.endswith('.jam')}}
        with self.assertRaises(OverflowError): R.encode(combined)
        value, expected, inputs, context = synthetic()
        for fault in ('lease-after-run', 'overflow'):
            output = io.BytesIO()
            current = mock.Mock(side_effect=[{}, P.GuardError('inert expired')] if fault == 'lease-after-run' else None, return_value={})
            provider = types.SimpleNamespace(require=current)
            runner = types.ModuleType('home_asset_rehearsal.runner'); runner.run = mock.Mock(return_value=value['report'])
            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(W, 'admission', return_value=(inputs, expected, E.sha(E.canonical(context)), provider)))
                stack.enter_context(mock.patch.object(W.signal, 'signal'))
                stack.enter_context(mock.patch.object(W.os, 'umask'))
                stack.enter_context(mock.patch.object(W.sys, 'stdout', types.SimpleNamespace(buffer=output)))
                stack.enter_context(mock.patch.object(W, 'capture_files', return_value=value['artifacts']))
                for name in ('source_tree', 'mapped_owner'): stack.enter_context(mock.patch.object(W, name))
                runtime_check = stack.enter_context(mock.patch.object(W, 'runtime_inputs'))
                stack.enter_context(mock.patch.dict(sys.modules, {'home_asset_rehearsal': _package, 'home_asset_rehearsal.runner': runner}))
                stack.enter_context(mock.patch.object(_package, 'runner', runner, create=True))
                if fault == 'overflow':
                    original = R.encode
                    stack.enter_context(mock.patch.object(R, 'encode', side_effect=lambda row: (_ for _ in ()).throw(OverflowError()) if row['status'] == 'pass' else original(row)))
                self.assertEqual(W.main(), 1)
                if fault == 'overflow':
                    runtime_check.assert_called_once_with(inputs)
                else:
                    runtime_check.assert_not_called()
            self.assertTrue(runner.run.called)
            failed, files = R.decode(output.getvalue(), expected, context_sha='', desk_hashes={}, assets={})
            self.assertEqual(failed['status'], 'fail'); self.assertEqual(files, {})
            self.assertEqual(failed['error_class'], 'frame-overflow' if fault == 'overflow' else 'runner-failed')

    def test_owner_eof_reap_cleanup_doc_and_original_error_gates(self):
        value, expected, inputs, context = synthetic()
        gate = guard_check()
        guard = {'collector': {'overflow': False, 'error': None, 'eof': True, 'completed': True}, 'cleanup_errors': [],
            'child_terminated': True, 'exit_code': 0, 'run_id': expected['run_id'], 'policy': {'fixed': True},
            'status': 'pass', 'doc_worker_admission': {'inert': True}}
        fake_doc = types.ModuleType('doc_worker_proof'); fake_doc.verify_admission = mock.Mock()
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(sys.modules, {'doc_worker_proof': fake_doc}):
            root = Path(folder); (root / 'console.private.log').write_bytes(R.encode(value))
            h = types.SimpleNamespace(execution_policy=types.SimpleNamespace(read_json=mock.Mock(return_value=guard)),
                require_collected_child=gate, POLICY={'fixed': True})
            def owner(): return {'cleanup': {'verified': True}, 'errors': []}
            self.assertEqual(set(A.collected(h, root, owner(), inputs, context, expected['run_id'], expected['controller_commit'])), set(R.NAMES))
            for fault in ('eof', 'overflow', 'reap', 'exit-bool', 'lease', 'whole-cleanup', 'original-error', 'doc'):
                bad, row = deepcopy(guard), owner()
                if fault == 'eof': bad['collector']['eof'] = False
                elif fault == 'overflow': bad['collector']['overflow'] = True
                elif fault == 'reap': bad['child_terminated'] = False
                elif fault == 'exit-bool': bad['exit_code'] = False
                elif fault == 'lease': bad['status'] = 'fail'
                elif fault == 'whole-cleanup': row['cleanup']['verified'] = False
                elif fault == 'original-error': row['errors'] = [{'phase': 'owned-service', 'error_class': 'RuntimeError'}]
                h.execution_policy.read_json.return_value = bad
                fake_doc.verify_admission.side_effect = ValueError('inert doc refusal') if fault == 'doc' else None
                with self.subTest(fault=fault), self.assertRaises(ValueError): A.collected(h, root, row, inputs, context, expected['run_id'], expected['controller_commit'])
                if fault == 'original-error': self.assertEqual(row['errors'][0]['phase'], 'owned-service')

    def test_exclusive_receipt_last_and_export_failure_rollback(self):
        value, expected, inputs, context = synthetic()
        _, files = decode(value, expected, inputs, context)
        def owner(): return {'status': 'pass', 'errors': [], 'cleanup': {'verified': True}, 'artifacts': {}, 'report': value['report']}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); row = owner(); order = []
            original = A.exclusive
            def logged(path, raw, created): order.append(path.name); return original(path, raw, created)
            with mock.patch.object(A, 'exclusive', side_effect=logged): self.assertEqual(A.publish(root, row, inputs, files), 'pass')
            self.assertEqual(order[-1], 'owner-report.json')
            self.assertEqual({p.name for p in root.iterdir()}, {*R.NAMES, 'inputs.json', 'report.json', 'owner-report.json'})
            self.assertEqual(json.loads((root / 'owner-report.json').read_bytes())['artifacts'], {n: {'bytes': len(raw), 'sha256': E.sha(raw)} for n, raw in files.items()})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); row = owner()
            def fault(path, raw, created):
                if path.name == 'report.json': raise OSError('inert write failure')
                return original(path, raw, created)
            with mock.patch.object(A, 'exclusive', side_effect=fault): self.assertEqual(A.publish(root, row, inputs, files), 'fail')
            self.assertEqual([p.name for p in root.iterdir()], ['owner-report.json'])
            failed = json.loads((root / 'owner-report.json').read_bytes())
            self.assertEqual(failed['status'], 'fail'); self.assertEqual(failed['artifacts'], {})
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / 'seed8.jam').write_bytes(b'prior attempt'); row = owner()
            self.assertEqual(A.publish(root, row, inputs, files), 'fail')
            self.assertEqual((root / 'seed8.jam').read_bytes(), b'prior attempt')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); row = owner(); row.update(status='fail', errors=[{'phase': 'owned-service', 'error_class': 'TimeoutError'}], report=None)
            self.assertEqual(A.publish(root, row, inputs, {}), 'fail')
            self.assertEqual(row['errors'][0]['error_class'], 'TimeoutError')
            self.assertFalse(any((root / n).exists() for n in R.NAMES))

    def test_public_evidence_permissions_under_private_umask(self):
        value, expected, inputs, context = synthetic()
        _, artifacts = decode(value, expected, inputs, context)
        source = ast.parse((PACKAGE / 'service_adapter.py').read_bytes())
        outer = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'outer')
        start = next(i for i, n in enumerate(outer.body) if isinstance(n, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'public' for t in n.targets))
        end = next(i for i in range(start, len(outer.body)) if isinstance(outer.body[i], ast.Expr)
                   and isinstance(outer.body[i].value, ast.Call)
                   and isinstance(outer.body[i].value.func, ast.Name)
                   and outer.body[i].value.func.id == 'publish')
        # Execute only the actual fixed public-directory preparation statements.
        # Root ownership is an explicit double; actual temporary modes and bytes
        # are real, with the same private umask as hosted.main.
        directory_code = compile(ast.Module(body=outer.body[start:end], type_ignores=[]),
                                 '<captured-public-directory>', 'exec', dont_inherit=True)
        previous_umask = os.umask(0o077)
        try:
            for outcome in ('pass', 'initial-failure', 'export-failure'):
                with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                    base = Path(folder)
                    private = base / 'private'; private.mkdir(mode=0o700)
                    secret = private / 'console.private.log'; secret.write_bytes(b'private fixture')
                    def controlled(path):
                        self.assertEqual(path, base / 'home-asset-evidence')
                        self.assertFalse(path.is_symlink())
                        self.assertEqual(path.stat().st_mode & 0o777, 0o700)
                    hosted = types.SimpleNamespace(ROOT=base, regular_root=controlled)
                    namespace = {'hosted': hosted, 'os': os}
                    exec(directory_code, namespace)
                    public = namespace['public']
                    self.assertEqual(public.stat().st_mode & 0o777, 0o755)
                    row = {'status': 'pass', 'errors': [], 'cleanup': {'verified': True},
                           'artifacts': {}, 'report': value['report']}
                    files = artifacts
                    if outcome == 'initial-failure':
                        row.update(status='fail', errors=[{'phase': 'intake', 'error_class': 'ValueError'}], report=None)
                        files = {}
                    order = []
                    original = A.exclusive
                    def checked(path, raw, created):
                        if outcome == 'export-failure' and path.name == 'report.json':
                            raise OSError('inert export refusal')
                        original(path, raw, created)
                        self.assertEqual(path.stat().st_mode & 0o777, 0o644)
                        self.assertEqual(path.read_bytes(), raw)
                        order.append(path.name)
                    with mock.patch.object(A, 'exclusive', side_effect=checked):
                        self.assertEqual(A.publish(public, row, inputs, files),
                                         'pass' if outcome == 'pass' else 'fail')
                    self.assertEqual(order[-1], 'owner-report.json')
                    expected_files = ({*R.NAMES, 'inputs.json', 'report.json', 'owner-report.json'}
                                      if outcome == 'pass' else {'inputs.json', 'owner-report.json'}
                                      if outcome == 'initial-failure' else {'owner-report.json'})
                    self.assertEqual({p.name for p in public.iterdir()}, expected_files)
                    self.assertTrue(all((p.stat().st_mode & 0o777) == 0o644 for p in public.iterdir()))
                    receipt = json.loads((public / 'owner-report.json').read_bytes())
                    self.assertEqual(receipt['status'], 'pass' if outcome == 'pass' else 'fail')
                    if outcome != 'pass':
                        self.assertEqual(receipt['artifacts'], {})
                    self.assertEqual(private.stat().st_mode & 0o777, 0o700)
                    self.assertEqual(secret.stat().st_mode & 0o777, 0o600)
                    self.assertEqual(secret.read_bytes(), b'private fixture')
        finally:
            os.umask(previous_umask)
