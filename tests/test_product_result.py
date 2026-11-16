"""Authored boundary fixtures only; no runtime, child or execution assertion."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREPARED = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts/urbit'), str(ROOT / 'scripts')]
import team_check
import review_prepare
import release_install


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, PREPARED / relative)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


conn = load('product_conn', 'scripts/urbit/product_conn.py')
load('product_home_check', 'scripts/urbit/product_home_check.py')
load('product_controller', 'scripts/urbit/product_controller.py')
verifier = load('product_result', 'scripts/ci/product_result.py')


def framed(noun):
    raw = verifier._jam(noun)
    return (b'\0' + len(raw).to_bytes(4, 'little') + raw).hex()


def authored_call(*, family='product', ship='bus', mode='query', value=None, target='zod', app='stead-home', route='/', result=None):
    value = {'protocol': 'stead.query/4', 'request_id': team_check.uid(501)} if value is None else value
    raw = conn.canonical(value)
    result = {'protocol': 'authored.fixture/1', 'status': 'read'} if result is None else result
    result_raw = conn.canonical(result)
    parts = [p for p in route.split('/') if p]
    path_noun = verifier.noun_list([verifier._atom(p) for p in parts])
    thread = 'stead-team-client' if family == 'legacy' else 'stead-product-check'
    target_noun = verifier.cell(verifier.SHIP_ATOMS[target], verifier._atom(app), verifier._atom(mode), path_noun, int.from_bytes(raw, 'little'))
    noun = verifier.cell(32, verifier._atom('fyrd'), verifier.cell(verifier._atom('base'), verifier._atom(thread), verifier._atom('noun'), verifier.cell(verifier._atom('noun'), target_noun)))
    response = verifier.cell(32, verifier._atom('avow'), 0, verifier._atom('noun'), verifier._atom('stead-core-result'), verifier._atom(result_raw.hex()))
    path_text = '[' + ' '.join(verifier.core_conn.atom(p.encode()) for p in parts) + ' ~]' if parts else '~'
    row = {'ship': ship, 'mode': mode, 'target': target, 'app': app, 'route': route,
        'input_hex': raw.hex(), 'input_sha256': verifier.hashlib.sha256(raw).hexdigest(),
        'request': f'[32 %fyrd [%base %{thread} %noun [%noun [~{target} %{app} %{mode} {path_text} {verifier.core_conn.atom(raw)}]]]]',
        'request_frame_hex': framed(noun), 'response_frame_hex': framed(response),
        'response_frame_sha256': verifier.hashlib.sha256(bytes.fromhex(framed(response))).hexdigest(),
        'stdout': "[32 %avow 0 %noun %stead-core-result '" + result_raw.hex() + "']", 'stderr': '',
        'outcome': {'raw': result_raw.decode(), 'json': result}}
    return row, value


def authored_restart():
    ship, app, nonce, incarnation = 'zod', 'stead-home', 'b' * 64, 'c' * 64
    rows = []
    def dojo(ship, source):
        result = '%base' if source.startswith('.^(desk ') else '0x' + 'a' * 64
        rows.append({'ship': ship, 'dojo': source, 'result': result})
        return result
    saved = verifier.team_lifecycle.TeamLifecycle.saved_fingerprint(None, ship, dojo)
    verifier.team_lifecycle.TeamLifecycle.saved_fingerprint(None, ship, dojo)
    dojo(ship, f'.^(desk %gd /={app}=/$)')
    for source, result in [(f'|rein %base [%.n %{app}]', ''), (f'|rein %base [%.y %{app}]', ''),
                           (f'.^(? %gu /={app}=/$)', '%.y')]:
        rows.append({'ship': ship, 'dojo': source, 'result': result})
    boot = {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~zod',
            'nonce': nonce, 'incarnation': incarnation}
    row, _ = authored_call(family='legacy', ship=ship, mode='bootstrap',
        value={'protocol': 'stead.bootstrap/1', 'nonce': nonce}, target=ship, app=app,
        route='/bootstrap/' + nonce, result=boot)
    rows.append(row)
    rows.append({'ship': ship, 'dojo': f'(lien ~(tap in .^((set [@tas ?]) %ge /=base=/$)) |=([name=@tas live=?] =(name %{app})))', 'result': '%.y'})
    encoded = verifier._jam(verifier.cell(verifier.cell(verifier._atom('g'), verifier._atom('stead-startup'), 0), verifier.cell(verifier._atom('idle'), verifier._atom(app))))
    injection = {'source': '[[%g %stead-startup ~] [%idle %stead-home]]', 'bytes': len(encoded),
        'jam_sha256': verifier.hashlib.sha256(encoded).hexdigest(), 'seals': 15, 'encoder_stderr': ''}
    caps = {key: '0000000000000000' for key in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd')}
    caps['NoNewPrivs'] = '1'
    admission = {'pid': 200, 'incarnation': incarnation,
        'peer_proof': {'capabilities': {'200': caps}, 'socket': {'ship': ship, 'pid': 200,
            'endpoint': '0100007F:' + f'{verifier.native_peer_fence.PORTS[ship]:04X}', 'inode': '1234', 'network_namespace': 'net:[123]'}},
        'tls': {'hostname': 'home.localhost', 'certificate_sha256': 'd' * 64, 'protocol': 'TLSv1.3',
                'owned_listeners': [{'endpoint': '0100007F:' + f'{verifier.native_tls.PORTS[ship]:04X}', 'inode': '5678'}]}}
    events = [('configured restart expectation zod', {'saved_vase_sha256': saved}),
        ('shutdown zod', {'exit_code': 0, 'forced': False}),
        ('configured launch zod', {'pid': 200, 'argv': ['authored'], 'injection': injection}),
        ('launch zod', {'pid': 200, 'argv': ['authored']}), ('zod: zuse', '%408'),
        ('configured suspension zod', {'pid': 200, 'present_on_base': True}),
        ('configured admission zod', admission)]
    entry = {'ship': ship, 'saved_vase_sha256': saved, 'new_incarnation': incarnation, 'passed': True,
        'old_pid': 100, 'new_pid': 200, 'old_nonce': 'a' * 64, 'new_nonce': nonce, 'old_exit_code': 0,
        'command_start': 0, 'command_end': len(rows), 'injection': injection,
        'lifecycle': [{'utc': '2026-11-15T00:00:00Z', 'command': name, 'result': value} for name, value in events]}
    return rows, entry


def incomplete_outer():
    """Source-bound authored shell that lacks the actual journey; must fail."""
    modules = {'scripts/ci/product_result.py': verifier,
        'scripts/urbit/product_capture.py': verifier.product_capture,
        'scripts/urbit/product_controller.py': verifier.product_controller,
        'scripts/urbit/product_conn.py': conn, 'scripts/urbit/product_home_check.py': verifier.product_home_check,
        'scripts/urbit/team_check.py': team_check, 'scripts/urbit/team_lifecycle.py': verifier.team_lifecycle,
        'scripts/urbit/review_prepare.py': review_prepare, 'scripts/urbit/core_conn.py': verifier.core_conn,
        'scripts/urbit/native_peer_fence.py': verifier.native_peer_fence,
        'scripts/urbit/native_tls.py': verifier.native_tls, 'scripts/release_install.py': release_install}
    sources = {name: {'sha256': verifier.hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()}
               for name, module in modules.items()}
    sources['scripts/urbit/supervisor.py'] = {'sha256': verifier.hashlib.sha256((ROOT / 'scripts/urbit/supervisor.py').read_bytes()).hexdigest()}
    composed = {}
    for name in ('ted/stead-product-checkpoint.hoon', 'gen/stead-product-checkpoint.hoon', 'gen/stead-v10-capture.hoon'):
        path = 'native/core/desk/' + name
        sources[path] = {'sha256': verifier.hashlib.sha256((PREPARED / path).read_bytes()).hexdigest()}
        composed[path] = sources[path]
    rows, owners = [], {}
    for index, ship in enumerate(verifier.SHIPS, 1):
        nonce = str(index) * 64
        owners[ship] = {'pid': 100 + index, 'nonce': nonce}
        boot = {'protocol': 'stead.bootstrap/1', 'status': 'ready', 'home': '~' + ship,
                'nonce': nonce, 'incarnation': str(index + 4) * 64}
        row, _ = authored_call(family='legacy', ship=ship, mode='bootstrap',
            value={'protocol': 'stead.bootstrap/1', 'nonce': nonce}, target=ship,
            app=verifier.team_lifecycle.APPS[ship], route='/bootstrap/' + nonce, result=boot)
        rows.append(row)
    trace = [{'kind': 'wrong-callback', 'arguments': [], 'options': {}, 'command_start': 4,
              'command_end': 4, 'check_start': 0, 'check_end': 0, 'result': None}]
    now = 1_700_000_000_000
    record = {'profile': 'native-human-doc/1', 'status': 'observed', 'classification': 'prepared-disposable-native-journey',
        'qualifies_phase': False, 'restarts': [], 'paused_predecessor': None,
        'old_captures': {'predecessor': {}, 'product': {}},
        'full_product_partial_restore': 'not-observed', 'browser': 'separate-fresh-fixture-required',
        'config': team_check.configuration(now), 'now': now, 'trace': trace, 'result': {},
        'initial_owners': owners, 'command_start': 4, 'command_end': 4, 'check_start': 0, 'check_end': 0}
    inputs = {'expected_native_inputs': {'authored': 'not execution evidence'},
              'controller_files': sources, 'composed_files': composed}
    installed = {name.removeprefix('native/core/desk/'): item['sha256'] for name, item in composed.items()}
    report = {'status': 'fail', 'error': verifier.DISABLED, 'qualifies_phase': False,
        'inputs_before': inputs['expected_native_inputs'], 'inputs_after': inputs['expected_native_inputs'],
        'installed': {ship: installed.copy() for ship in verifier.SHIPS}, 'commands': rows, 'checks': [],
        'product_journey': record}
    return report, inputs


class ResultTests(unittest.TestCase):
    def test_exact_authored_frame_correlates_without_execution_claim(self):
        row, value = authored_call()
        result = verifier.native_call(row, family='product', ship='bus', mode='query', value=value, options={})
        self.assertEqual(result, {'protocol': 'authored.fixture/1', 'status': 'read'})

    def test_native_request_payload_and_route_must_match_frame(self):
        row, value = authored_call()
        for changed in (value | {'request_id': team_check.uid(502)}, value | {'extra': 'authority'}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                verifier.native_call(row, family='product', ship='bus', mode='query', value=changed, options={})
        with self.assertRaises(ValueError):
            verifier.native_call(row, family='product', ship='bus', mode='query', value=value, options={'route': '/wrong'})

    def test_altered_frame_cannot_be_saved_by_matching_text_or_hash(self):
        row, value = authored_call()
        changed = copy.deepcopy(row)
        changed['response_frame_hex'] = framed(verifier.cell(32, verifier._atom('avow'), 1))
        changed['response_frame_sha256'] = verifier.hashlib.sha256(bytes.fromhex(changed['response_frame_hex'])).hexdigest()
        with self.assertRaises(ValueError):
            verifier.native_call(changed, family='product', ship='bus', mode='query', value=value, options={})

    def test_request_frame_cannot_name_another_thread(self):
        row, value = authored_call()
        changed, _ = authored_call(family='legacy')
        row['request_frame_hex'] = changed['request_frame_hex']
        with self.assertRaises(ValueError):
            verifier.native_call(row, family='product', ship='bus', mode='query', value=value, options={})

    def test_terminal_json_and_observed_outcome_must_be_identical(self):
        row, value = authored_call()
        row['outcome']['json']['status'] = 'accepted'
        with self.assertRaises(ValueError):
            verifier.native_call(row, family='product', ship='bus', mode='query', value=value, options={})

    def test_complete_canonical_frame_and_bounds_required(self):
        row, _ = authored_call()
        for frame in (row['response_frame_hex'] + '00', row['response_frame_hex'][:-2], '00' * 16390):
            with self.subTest(length=len(frame)), self.assertRaises(ValueError):
                verifier.frame_noun(frame)

    def test_same_native_bootstrap_must_bind_target_ship(self):
        value = {'protocol': 'stead.bootstrap/1', 'nonce': 'c' * 64}
        row, value = authored_call(family='legacy', ship='nec', mode='bootstrap', value=value,
                                  target='nec', app='stead-identity', route='/bootstrap/' + value['nonce'])
        options = {'target': 'nec', 'app': 'stead-identity', 'route': row['route'], 'timeout': 75}
        verifier.native_call(row, family='legacy', ship='nec', mode='bootstrap', value=value, options=options)
        with self.assertRaises(ValueError):
            verifier.native_call(row, family='legacy', ship='bus', mode='bootstrap', value=value, options=options | {'target': 'bus'})

    def test_actual_helper_sources_and_order_replayed_without_child(self):
        rows = []
        class Capture:
            def dojo(self, ship, source):
                result = '%base' if source.startswith('.^(desk ') else '0x' + 'a' * 64
                rows.append({'ship': ship, 'dojo': source, 'result': result})
                return result
        capture = Capture()
        expected = verifier.fingerprints(capture, release_install.saved_home_fingerprint)
        cursor = verifier.Commands(rows, 0, len(rows))
        self.assertEqual(verifier.fingerprints(cursor, release_install.saved_home_fingerprint), expected)
        cursor.done()
        changed = copy.deepcopy(rows)
        changed[0]['dojo'] += ' '
        with self.assertRaises(ValueError):
            verifier.fingerprints(verifier.Commands(changed, 0, len(changed)), release_install.saved_home_fingerprint)

    def test_extra_dropped_or_disagreeing_fingerprint_is_rejected(self):
        rows = []
        class Capture:
            def dojo(self, ship, source):
                result = '%base' if source.startswith('.^(desk ') else '0x' + 'a' * 64
                rows.append({'ship': ship, 'dojo': source, 'result': result})
                return result
        verifier.fingerprints(Capture(), release_install.saved_home_fingerprint)
        for changed in (rows[:-1], [rows[1], rows[0], *rows[2:]], [rows[0] | {'result': '0x' + 'b' * 64}, *rows[1:]]):
            with self.subTest(length=len(changed)), self.assertRaises(ValueError):
                verifier.fingerprints(verifier.Commands(changed, 0, len(changed)), release_install.saved_home_fingerprint)
        cursor = verifier.Commands([*rows, rows[0]], 0, len(rows) + 1)
        verifier.fingerprints(cursor, release_install.saved_home_fingerprint)
        with self.assertRaises(ValueError):
            cursor.done()

    def test_only_exact_home_idle_injection_is_accepted(self):
        app = 'stead-home'
        encoded = verifier._jam(verifier.cell(verifier.cell(verifier._atom('g'), verifier._atom('stead-startup'), 0), verifier.cell(verifier._atom('idle'), verifier._atom(app))))
        proof = {'source': '[[%g %stead-startup ~] [%idle %stead-home]]',
            'bytes': len(encoded), 'jam_sha256': verifier.hashlib.sha256(encoded).hexdigest(), 'seals': 15, 'encoder_stderr': ''}
        verifier.injection(proof, 'zod')
        for mutation in ({'source': '[[%g %stead-startup ~] [%load ~]]'}, {'seals': 0}, {'bytes': len(encoded) + 1}):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verifier.injection(proof | mutation, 'zod')

    def test_no_legacy_or_product_qualification_can_be_inferred(self):
        for status, error, qualifies in [('pass', '', False), ('fail', verifier.DISABLED, True)]:
            with self.subTest(status=status, qualifies=qualifies), self.assertRaises(ValueError):
                verifier.verify_observation({'status': status, 'error': error, 'qualifies_phase': qualifies}, {},
                                            release_fingerprint=release_install.saved_home_fingerprint)

    def test_authored_restart_binds_fingerprint_new_nonce_and_owned_admission(self):
        rows, entry = authored_restart()
        checks = []
        def check(name, condition):
            self.assertIs(condition, True)
            checks.append(name)
        cursor = verifier.Commands(rows, 0, len(rows))
        verifier.verify_restart(cursor, entry, 'zod', check)
        cursor.done()
        self.assertEqual(checks, ['product-zod-previous-child-reaped', 'product-zod-suspended-exact-saved-vase',
                                  'product-zod-fresh-native-bootstrap'])

    def test_saved_capture_is_replayed_only_between_suspension_and_reinstall(self):
        rows, entry = authored_restart()
        capture = verifier.product_capture
        raw, fingerprint = b'authored-only', 'a' * 64
        response = {'protocol': 'stead.v10-capture/1', 'target': 'product',
            'offset': '0', 'length': str(len(raw)), 'total_bytes': str(len(raw)),
            'capture_pin': capture.domain('stead.v10-capture/1', raw.hex().encode()),
            'native_vase_fingerprint': fingerprint, 'type_pin': 'b' * 64,
            'payload_pin': 'c' * 64, 'data_hex': raw.hex()}
        idle = {'ship': 'zod', 'dojo': '.^(? %gu /=stead-home=/$)', 'result': '%.n'}
        observation = {'ship': 'zod', 'dojo': capture.source('product', 0, ''),
            'result': hex(int.from_bytes(capture.canonical(response), 'little'))}
        capture_rows = [idle, observation, idle, *rows[:2]]
        combined = [*rows[:4], *capture_rows, *rows[4:]]
        entry['command_end'] = len(combined)
        def observed(cursor, saved):
            retained = capture.collect(cursor.dojo,
                lambda: verifier.team_lifecycle.TeamLifecycle.saved_fingerprint(None, 'zod', cursor.dojo),
                'product', saved)
            self.assertEqual(capture.validate_record(retained), raw)
        cursor = verifier.Commands(combined, 0, len(combined))
        verifier.verify_restart(cursor, entry, 'zod', lambda n, c: self.assertTrue(c), capture=observed)
        cursor.done()
        for changed in ([*capture_rows, *rows], [*rows[:4], *capture_rows[1:], *rows[4:]]):
            with self.subTest(length=len(changed)), self.assertRaises(ValueError):
                verifier.verify_restart(verifier.Commands(changed, 0, len(changed)),
                    entry | {'command_end': len(changed)}, 'zod',
                    lambda n, c: self.assertTrue(c), capture=observed)

    def test_large_capture_response_bound_is_exact_source_only(self):
        authored = load('authored_capture_source', 'tests/test_product_capture.py')
        source = authored.AuthoredSource(b'x' * (verifier.product_capture.CHUNK + 1))
        rows = []
        def recorded(ship, command):
            result = source.dojo(ship, command)
            rows.append({'ship': ship, 'dojo': command, 'result': result})
            return result
        expected = verifier.product_capture.collect(recorded, lambda: authored.FP, 'product', authored.FP)
        self.assertGreater(len(rows[1]['result']), 32768)
        cursor = verifier.Commands(rows, 0, len(rows))
        actual = verifier.product_capture.collect(cursor.dojo, lambda: authored.FP, 'product', authored.FP)
        cursor.done()
        self.assertEqual(actual, expected)
        for ship, command, output in (
                ('zod', rows[1]['dojo'], '0x' + '1' * 100000),
                ('bus', rows[1]['dojo'], rows[1]['result']),
                ('zod', '+unrelated', rows[1]['result']),
                ('zod', rows[1]['dojo'] + ' ', rows[1]['result'])):
            row = {'ship': ship, 'dojo': command, 'result': output}
            with self.subTest(ship=ship, command=command), self.assertRaises(ValueError):
                verifier.Commands([row], 0, 1).dojo(ship, command)

    def test_reused_nonce_wrong_incarnation_or_missing_custody_event_fails(self):
        rows, entry = authored_restart()
        variants = [entry | {'new_nonce': entry['old_nonce']}, entry | {'new_incarnation': 'e' * 64},
                    entry | {'lifecycle': entry['lifecycle'][:-1]}, entry | {'old_exit_code': -9},
                    entry | {'saved_vase_sha256': 'e' * 64}]
        for changed in variants:
            with self.subTest(changed=set(changed)), self.assertRaises(ValueError):
                verifier.verify_restart(verifier.Commands(rows, 0, len(rows)), changed, 'zod', lambda n, c: self.assertTrue(c))

    def test_admitted_privileged_or_wrong_process_socket_is_rejected(self):
        rows, entry = authored_restart()
        for kind in ('capability', 'pid', 'tls'):
            changed = copy.deepcopy(entry)
            admission = changed['lifecycle'][-1]['result']
            if kind == 'capability':
                admission['peer_proof']['capabilities']['200']['CapEff'] = '0000000000000001'
            elif kind == 'pid':
                admission['peer_proof']['socket']['pid'] = 300
            else:
                admission['tls']['hostname'] = 'another.localhost'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                verifier.verify_restart(verifier.Commands(rows, 0, len(rows)), changed, 'zod', lambda n, c: self.assertTrue(c))

    def test_source_bound_initial_bootstrap_is_not_a_complete_journey(self):
        report, inputs = incomplete_outer()
        with self.assertRaisesRegex(ValueError, 'Exact ordered callback correlation'):
            verifier.verify_observation(report, inputs, release_fingerprint=release_install.saved_home_fingerprint)

    def test_source_change_and_partial_restore_scope_claim_fail_before_replay(self):
        report, inputs = incomplete_outer()
        changed = copy.deepcopy(inputs)
        changed['controller_files']['scripts/urbit/team_lifecycle.py']['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'helper source differs'):
            verifier.verify_observation(report, changed, release_fingerprint=release_install.saved_home_fingerprint)
        report['product_journey']['full_product_partial_restore'] = 'passed'
        with self.assertRaisesRegex(ValueError, 'scope cannot expand'):
            verifier.verify_observation(report, inputs, release_fingerprint=release_install.saved_home_fingerprint)

    def test_recorded_exit_and_slice_fields_require_exact_integers(self):
        rows, entry = authored_restart()
        mutations = [{'old_exit_code': False}, {'old_exit_code': 0.0},
                     {'command_start': False}, {'command_end': float(entry['command_end'])}]
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verifier.verify_restart(verifier.Commands(rows, 0, len(rows)), entry | mutation,
                                        'zod', lambda n, c: self.assertTrue(c))
        for field in ('command_start', 'command_end', 'check_start', 'check_end'):
            report, inputs = incomplete_outer()
            report['product_journey'][field] = float(report['product_journey'][field])
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'range bounds'):
                verifier.verify_observation(report, inputs, release_fingerprint=release_install.saved_home_fingerprint)

    def test_json_metadata_cannot_equate_booleans_floats_and_integers(self):
        self.assertFalse(verifier.same({'passed': True}, {'passed': 1}))
        self.assertFalse(verifier.same({'exit': 0}, {'exit': False}))
        self.assertFalse(verifier.same({'index': 4}, {'index': 4.0}))
        rows, entry = authored_restart()
        for mutation in ('forced', 'suspended', 'seals', 'bytes', 'pid'):
            changed = copy.deepcopy(entry)
            if mutation == 'forced':
                changed['lifecycle'][1]['result']['forced'] = 0
            elif mutation == 'suspended':
                changed['lifecycle'][5]['result']['present_on_base'] = 1
            elif mutation in ('seals', 'bytes'):
                changed['injection'][mutation] = float(changed['injection'][mutation])
            else:
                changed['lifecycle'][6]['result']['peer_proof']['socket']['pid'] = 200.0
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                verifier.verify_restart(verifier.Commands(rows, 0, len(rows)), changed,
                                        'zod', lambda n, c: self.assertTrue(c))


if __name__ == '__main__':
    unittest.main()
