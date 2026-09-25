"""Real native acceptance; all authority calls use four isolated fake ships."""
from __future__ import annotations
import copy
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import time
import traceback
import threading
import core_conn
import core_cases_v2 as core_cases
import core_export
import qualification_cases
import qualification_gate
import native_transcript
import delivery_suite
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
DEPENDENCIES = ('core_test.py', 'core_conn.py', 'core_cases_v2.py', 'core_export.py',
                'delivery_cases.py', 'delivery_suite.py', 'qualification_cases.py',
                'qualification_gate.py', 'native_transcript.py')


def closure():
    return {name: sha(CODE / name) for name in DEPENDENCIES}


LOADED_CLOSURE = closure()


def bounded_report(report, maximum=16 * 1024 * 1024):
    """Match the supervisor's report admission bound without a silent green drop."""
    payload = (json.dumps(report, indent=2) + '\n').encode()
    if len(payload) <= maximum:
        return report, payload
    failed = {key: report[key] for key in ('classification', 'inputs_before', 'inputs_after',
              'native_tree_sha256', 'toolchain_sha256', 'transport_artifact', 'elapsed_seconds') if key in report}
    failed.update(status='fail', error='Aggregate native summary exceeded16MiB; exact transport sidecar retained',
                  original_summary_bytes=len(payload), original_summary_sha256=hashlib.sha256(payload).hexdigest(),
                  checks=[], qa={'status': 'incomplete'},
                  coverage_limits=['Oversized aggregate assertions were not admitted; no qualification is inferred.'])
    payload = (json.dumps(failed, indent=2) + '\n').encode()
    if len(payload) > maximum:
        raise ValueError('Even the failure summary exceeds its bound')
    return failed, payload


def inputs():
    return {'native': tree_sha(Path('/native/core/desk')), 'runner': closure(),
            'harness': source_sha(CODE), 'toolchain': sha('/toolchain.json'),
            'fixture': sha('/specs/native-fixture.json'), 'cases': sha('/specs/fixtures/native-cases-v2.json'),
            'previous_cases': sha('/specs/fixtures/native-cases.json'),
            'vectors': sha('/specs/fixtures/commands.json'), 'freeze': sha('/specs/v2/contract-freeze.json'),
            'v2_vectors': sha('/specs/v2/commands.json'),
            'previous_freeze': sha('/specs/contract-freeze.json'),
            'qualification_manifest': sha('/specs/v2/qualification-gate.json')}


def concurrent_writes(call, requests, report, record_interval):
    """Release two native calls together and retain their observed lifetimes.

    The intervals cover actual client calls, including encoding and transport;
    they do not claim simultaneous processing inside the authoritative ship.
    Publish records before work so a broken barrier or failed call stays visible.
    """
    if len(requests) != 2 or [value[0] for value in requests] != ['bus', 'zod']:
        raise ValueError('Exactly the two frozen concurrent writers are required')
    release = {'protocol': 'stead.concurrent-native-calls/1',
               'clock': 'time.monotonic_ns', 'participants': 2,
               'barrier_timeout_seconds': 10}
    rows = [{'sender': ship, 'command': copy.deepcopy(cmd), 'route': route,
             'input_sha256': hashlib.sha256(raw).hexdigest()}
            for ship, cmd, route, raw in requests]
    report['concurrent_release'], report['concurrent_submissions'] = release, rows
    barrier = threading.Barrier(3, timeout=10,
        action=lambda: release.update(released_ns=time.monotonic_ns()))

    def invoke(index):
        row = rows[index]
        ship, _, route, raw = requests[index]
        row['ready_ns'] = time.monotonic_ns()
        try:
            barrier.wait()
            row['started_ns'] = time.monotonic_ns()
            result = call(ship, 'command', route, raw)
            row['finished_ns'] = time.monotonic_ns()
            row['response'] = result
            interval = {'kind': 'concurrent-call-interval', 'release': copy.deepcopy(release),
                        **{key: row[key] for key in ('sender', 'route', 'input_sha256',
                                                    'ready_ns', 'started_ns', 'finished_ns')},
                        'response_transcript': copy.deepcopy(result['native']['transcript'])}
            row['interval'] = {'transcript': record_interval(interval)}
            return result
        except BaseException as error:
            row.setdefault('finished_ns', time.monotonic_ns())
            row['error'] = type(error).__name__ + ': ' + str(error)
            raise

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(invoke, index) for index in range(2)]
        barrier.wait()
        results = [future.result() for future in futures]
    if max(row['started_ns'] for row in rows) >= min(row['finished_ns'] for row in rows):
        raise AssertionError('Concurrent native write calls did not overlap')
    return results


def run(host):
    started = time.monotonic()
    run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    report = {'status': 'fail', 'classification': 'local-real-native-fake-ships',
              'checks': [], 'commands': [], 'coverage_limits': [
                  'Synthetic sender bindings; no live/browser authentication or production isolation.',
                  'Warm process restart and declared on-load checks; no abrupt crash-window injection.',
                  'Observer signs cover issued synthetic Gall ducts; runtime mark failures must be retained.',
                  'Native document objects exported through stock Git; no Smart HTTP forge.',
                  'Source recipes are unqualified until their exact native outcomes and independent evidence are present.',
                  'No provisioning, shared-container lifecycle, browser sessions, HTTPS UI or live identity.']}
    before_inputs = inputs()
    report['inputs_before'] = before_inputs
    report['installed_files'] = {str(path.relative_to('/native/core/desk')): sha(path)
                                 for path in sorted(Path('/native/core/desk').rglob('*.hoon'))}
    report['installed_by_ship'], report['clay_verified_by_ship'] = {}, {}
    lifecycle_start = len(host['EVIDENCE'])
    export_count = 0
    transcript = native_transcript.Transcript(Path('/state/logs') / ('core-' + run_id + '-transport.jsonl.gz'))
    transcript_lock = threading.Lock()
    runtime_logs = native_transcript.RuntimeLogs(Path('/state/logs'), transcript)
    probes = delivery_suite.ProbePool()

    def check(name, condition, **details):
        report['checks'].append({'name': name, 'passed': bool(condition), **details})
        if not condition:
            raise AssertionError(name)

    def command(ship, source, expected=None):
        result = host['dojo'](ship, source)
        report['commands'].append({'ship':ship, 'dojo':source, 'result':result})
        if expected is not None:
            check(ship + ':' + source, result.strip() == expected)
        return result

    def clay_bytes(ship):
        # A Hood ACK is not proof that Clay has imported this exact source.
        for source in sorted(Path('/native/core/desk').rglob('*.hoon')):
            digest = sha(source)
            literal = core_conn.atom(bytes.fromhex(digest)[::-1])
            path = '/' + str(source.relative_to('/native/core/desk')).replace('.hoon','/hoon')
            expression = f'=/  raw=@t  .^(@t %cx /=base={path})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))'
            command(ship, expression, '%.y')
            report['clay_verified_by_ship'].setdefault(ship, {})[str(source.relative_to('/native/core/desk'))] = digest

    binary = '/runtime/' + host['LOCK']['runtime']['binary']

    def call(ship, mode, route='/', raw=b'', **kwargs):
        host['execution_check']()
        try:
            result = core_conn.run(binary, host['LIVE'] / ship / '.urb/conn.sock', mode, route, raw, **kwargs)
        except Exception as error:
            failure = {'ship': ship, 'mode': mode, 'route': route, 'status': 'failed',
                       'input_sha256': hashlib.sha256(raw).hexdigest(),
                       'error': type(error).__name__ + ': ' + str(error),
                       'transport': getattr(error, 'native_failure', None)}
            with transcript_lock:
                reference = transcript.append(failure)
            report['commands'].append({key: value for key, value in failure.items() if key != 'transport'} | {'transcript': reference})
            raise
        record = {'ship':ship, 'mode':mode, 'route':route, 'input_sha256':hashlib.sha256(raw).hexdigest(),
                  'input_bytes':len(raw), **result}
        # Keep exact large framing/control evidence once, outside the bounded
        # summary. Callback consumers receive hashes plus the evidence location.
        with transcript_lock:
            reference = transcript.append(record)
        summary = {key: record[key] for key in ('ship', 'mode', 'route', 'input_sha256',
                   'input_bytes', 'response_frame_sha256')}
        summary.update(transcript=reference,
                       stdout=record['stdout'] if len(record['stdout']) <= 1024 else '<see exact transcript>',
                       stderr=record['stderr'], request_sha256=hashlib.sha256(record['request'].encode()).hexdigest())
        report['commands'].append(summary)
        host['execution_check']()
        return {**(result['outcome'] or {'raw':None, 'json':None}), 'native':summary}

    def snapshot():
        outcome = call('zod', 'read', '/v1/fixture-snapshot')
        value = outcome['json']
        if value is None or value.get('protocol') != 'stead.fixture-snapshot/1':
            raise AssertionError('Owner snapshot absent')
        return value

    def same(before, after):
        return before['state_jam_sha256'] == after['state_jam_sha256']

    def restart():
        begin = time.monotonic()
        old_pid = host['PROCESSES']['zod'].pid
        host['shutdown']('zod')
        stopped = host['PROCESSES']['zod'].returncode
        host['launch']('zod')
        host['wait_ready']('zod')
        return {'old_pid':old_pid, 'old_exit':stopped, 'replacement_pid':host['PROCESSES']['zod'].pid,
                'elapsed_seconds':round(time.monotonic()-begin, 3),
                'external_effect_observation':'No external effect subsystem is implemented; network namespace has only loopback.'}

    def export(ship, project, container, snapshot=None):
        nonlocal export_count
        export_count += 1
        destination = Path('/state/logs') / f'core-export-{run_id}-{export_count}'
        return core_export.export(call, destination, ship, project, container, snapshot, api_version=2)

    def object_matrix(case, captures):
        ids = corpus['fixture_ids']
        project = ids['project']
        bus_container, zod_container = ids['bus_container'], ids['zod_container']
        bus = captures[case['action']['base_manifest_from']]['export']
        bus_head = bus['snapshot_commit_oid']
        bus_blob = next(oid for oid, obj in bus['objects'].items() if obj['kind'] == 'blob')
        zod = call('zod', 'read', f'/v2/git/{project}/{zod_container}')['json']['payload']
        zod_head = zod['snapshot_commit_oid']
        zod_blob = next(oid for oid, kind in zod['objects'].items() if kind == 'blob')
        variations = [(bus_container,bus_head,bus_blob), (zod_container,zod_head,zod_blob),
                      (bus_container,zod_head,zod_blob), (zod_container,bus_head,bus_blob),
                      (bus_container,'0'*40,bus_blob), (bus_container,bus_head,'0'*40)]
        return {'variants':[{'name':name, 'response':call('bus','read',f'/v2/git-object/{project}/{cid}/{head}/{oid}')}
                            for name,(cid,head,oid) in zip(case['action']['variants'],variations,strict=True)]}

    def trusted_now_ms():
        return int(snapshot()['now_ms'])

    def wait_until(deadline):
        begin = time.monotonic()
        now = trusted_now_ms()
        while now < deadline:
            if host['STOP_REQUESTED'].is_set():
                raise InterruptedError('Stop requested during expiry test')
            if time.monotonic() - begin > 180:
                raise TimeoutError('Native clock did not cross the bounded grant expiry')
            time.sleep(min(5, max(.05, (deadline-now)/1000)))
            now = trusted_now_ms()
        return {'deadline_ms':deadline, 'now_ms':now, 'elapsed_seconds':round(time.monotonic()-begin,3)}

    def control(value, *, succeeds=True, sender='zod'):
        result = call(sender, 'control', control=value)
        if succeeds:
            check('owner-control:' + value[0], result['json'] == {})
        else:
            check('owner-control-rejected:' + value[0], result['json'] is None and 'poke-fail' in result['native']['stderr'])
        return result

    def pause(seconds):
        host['execution_check']()
        time.sleep(seconds)
        host['execution_check']()

    observed = delivery_suite.ReadObserver(call, pause, runtime_logs, probe_pool=probes)

    def delivery_evidence(case, ship, route, result):
        native = result.get('native', {})
        return observed.delivery_evidence(case, ship or native.get('ship'),
                                         route or native.get('route'), result)

    def unavailable_home(attempt):
        begin = len(host['EVIDENCE'])
        old_pid = host['PROCESSES']['zod'].pid
        host['shutdown']('zod')
        stopped = host['PROCESSES']['zod'].returncode
        try:
            outcome = attempt(call)
        finally:
            # No forced/crashed fixture is resumed or promoted to a clean seed.
            host['execution_check']()
            host['launch']('zod')
            host['wait_ready']('zod')
        return {'old_pid': old_pid, 'old_exit': stopped,
                'replacement_pid': host['PROCESSES']['zod'].pid,
                'attempt': outcome, 'native': host['EVIDENCE'][begin:]}

    def delivery_sink(record):
        # Suite arguments can include the exact request bytes positionally.
        def portable(value):
            if isinstance(value, bytes):
                return {'bytes_hex': value.hex()}
            if isinstance(value, dict):
                return {key: portable(item) for key, item in value.items()}
            if isinstance(value, (list, tuple)):
                return [portable(item) for item in value]
            return value
        with transcript_lock:
            reference = transcript.append(portable(record))
        return {**reference, 'sha256': reference['record_sha256'],
                'path': '.piers/fakes/logs/' + reference['artifact']}

    def codec():
        cases = []
        for version, path in ((1, '/specs/fixtures/commands.json'), (2, '/specs/v2/commands.json')):
            vectors = json.loads(Path(path).read_text())
            check(f'codec-v{version}-six-frozen-vectors', len(vectors) == 6)
            for index, vector in enumerate(vectors):
                cases.append((f'frozen-v{version}-vector-{index}', core_cases.canonical(vector['request']), 'accept', vector))
        for case in corpus['codec_lane']['new_vectors']:
            if 'raw_utf8' in case:
                raw = case['raw_utf8'].encode()
            elif 'raw_hex' in case:
                raw = bytes.fromhex(case['raw_hex'])
            elif 'raw_recipe' in case:
                recipe = case['raw_recipe']
                raw = (recipe['prefix'] + recipe['append_utf8'] * recipe['repeat']).encode()
            else:
                recipe = case['command_recipe']
                cmd = copy.deepcopy(corpus['commands'][recipe['base_command_ref']])
                for path, value in recipe.get('replace', {}).items():
                    cmd[path[1:]] = value
                for path, spec in recipe['repeat_string'].items():
                    _, parent, field = path.split('/')
                    cmd[parent][field] = spec['value'] * spec['repeat']
                raw = core_cases.canonical(cmd)
            cases.append((case['name'], raw, case['expected']['codec'], None))
        previous = snapshot()
        for name, raw, expected, vector in cases:
            result = call('bus', 'codec', raw=raw)
            value = result['json']
            if expected == 'accept':
                canonical = core_cases.canonical(json.loads(raw))
                digest = hashlib.sha256(json.loads(raw)['protocol'].encode() + b'\0' + canonical).hexdigest()
                check('codec:' + name, value == {'status':'accepted', 'canonical':canonical.decode(), 'sha256':digest})
                if vector is not None:
                    check('codec-frozen-digest:' + name, digest == vector['sha256'])
            else:
                check('codec:' + name, value == {'status':'rejected', 'error':'invalid_command'})
                poke = call('bus', 'poke', raw=raw)
                check('home-rejects-malformed:' + name, poke['json'] is None and 'stead-invalid-command' in poke['native']['stderr'])
            check('codec-no-business-change:' + name, same(previous,snapshot()))

    def contexts():
        normal = {'classification':'public-synthetic','custody':'local-disposable',
                  'runtime':'isolated-fake','authentication':'fake-native/1'}
        baseline = snapshot()
        cmd = corpus['commands'][corpus['trusted_context_lane']['probe_commands'][0]]
        raw = core_cases.canonical(cmd)
        route = f"/v2/result/~bus/{core_cases.BINDINGS['bus']}/{cmd['project_id']}/{cmd['request_id']}/{core_cases.command_digest(raw)}"
        for case in corpus['trusted_context_lane']['cases']:
            name = case['name']
            info = case['owner_local_fixture_change']
            if info['target'] == 'profile':
                field = info['field']
                op = 'missing' if info['change'] == 'missing' else 'profile'
                change, restore = (op,'bus',field,'unsupported'), ('profile','bus',field,normal[field])
            else:
                pairs = {'expired-binding':(('expiry','0'),('expiry','4102444800000')),
                         'revoked-binding':(('active','no'),('active','yes')),
                         'missing-binding':(('binding-drop',''),('binding-restore','')),
                         'unsupported-agent-delegation':(('kind','agent'),('kind','person')),
                         'contradictory-context':(('kind','service'),('kind','person'))}
                if name == 'unsupported-authentication-mechanism':
                    change,restore = ('profile','bus','authentication','oidc'),('profile','bus','authentication','fake-native/1')
                else:
                    a,b = pairs[name]
                    change,restore = (a[0],'bus','',a[1]),(b[0],'bus','',b[1])
            control(change)
            invalid = snapshot()
            result = call('bus','command',route,raw)
            check('invalid-context-watch-nack:' + name, result['json'] is None
                  and 'stead-watch-denied' in result['native']['stderr']
                  and 'watch-ack-fail' in result['native']['stderr'])
            # Direct native poke must also recheck context when no result channel exists.
            poke = call('bus','poke',raw=raw)
            check('invalid-context-poke-transport-only:' + name, poke['json'] == {})
            for path in corpus['trusted_context_lane']['probe_reads']:
                result = call('bus','read',path)
                check('context-read-denied:' + name, result['json'] == core_cases.DENIAL)
            check('context-probes-preserve-state:' + name, same(invalid,snapshot()))
            control(restore)
            check('context-restored:' + name, same(baseline,snapshot()))

    def concurrency():
        ids = corpus['fixture_ids']
        before = snapshot()
        template = copy.deepcopy(corpus['commands']['journal_first_project_followup'])
        requests = []
        for index, ship in enumerate(('bus','zod')):
            cmd = copy.deepcopy(template)
            cmd['request_id'] = f'019939ba-4000-7000-8000-00000000800{index}'
            cmd['expected_revision'] = '4'
            cmd['payload']['title'] = 'Concurrent synthetic writer ' + ship
            raw = core_cases.canonical(cmd)
            route = f"/v2/result/~{ship}/{core_cases.BINDINGS[ship]}/{cmd['project_id']}/{cmd['request_id']}/{core_cases.command_digest(raw)}"
            requests.append((ship,cmd,route,raw))
        def record_interval(value):
            with transcript_lock:
                return transcript.append(value)
        results = concurrent_writes(call, requests, report, record_interval)
        check('two-principal-concurrent-call-overlap',
              max(row['started_ns'] for row in report['concurrent_submissions'])
              < min(row['finished_ns'] for row in report['concurrent_submissions']))
        accepted = [i for i,r in enumerate(results) if r['json'] and r['json'].get('status') == 'accepted']
        rejected = [r for r in results if r['json'] == {'protocol':'stead.result/2','status':'rejected','error':'revision_conflict'}]
        check('two-principal-concurrent-cas-one-winner', len(accepted)==1 and len(rejected)==1)
        winner = accepted[0]
        check('concurrent-receipt-trusted-sender', results[winner]['json']['principal_id'] == corpus['principals'][requests[winner][0]]
              and results[winner]['json']['resource_revision']=='5')
        view = call('nec','read',f"/v2/work/{ids['project']}/{ids['work_a']}")
        check('concurrent-winner-visible-to-reader', view['json']['payload'] == requests[winner][1]['payload'] and view['json']['resource_revision']=='5')
        after = snapshot()
        check('concurrent-cas-one-acceptance', int(after['journal_events'])==int(before['journal_events'])+1
              and int(after['receipts'])==int(before['receipts'])+1 and after['objects']==before['objects'])
        path = f"/v2/document/{ids['project']}/{ids['bus_container']}/{ids['document_a']}"
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(call,ship,'read',path) for ship in ('bus','bud')]
            owner,outsider = [future.result() for future in pending]
        check('concurrent-same-path-read-separation', owner['json']['payload']['markdown']==corpus['commands']['document_a_2']['payload']['markdown']
              and outsider['json']==core_cases.DENIAL)
        bus,cmd,route,raw = requests[0]
        denied = call('bud','command',route,raw)
        check('sender-cannot-reserve-another-result-route', denied['json'] is None and 'stead-watch-denied' in denied['native']['stderr'])
        check('concurrent-reads-and-wrong-route-preserve-state', same(after,snapshot()))

    try:
        report['source_commit'] = host['qualified_source']()
        host['execution_check'](preflight=True)
        check('loaded-supervisor-source-matches', before_inputs['harness'] == host['LOADED_SOURCE_DIGEST'])
        check('loaded-core-runner-source-matches', before_inputs['runner'] == LOADED_CLOSURE)
        report['evaluator_controls'] = core_conn.evaluator_controls(binary)
        report['commands'].extend(report['evaluator_controls']['commands'])
        check('native-evaluator-failure-and-large-frame-controls', report['evaluator_controls']['status'] == 'passed')
        host['execution_check']()
        corpus = json.loads(Path('/specs/fixtures/native-cases-v2.json').read_text())
        check('frozen-contract-manifest-matches-corpus', before_inputs['freeze'] == corpus['contract_freeze']['sha256'])
        check('preserved-v1-freeze-matches-corpus', before_inputs['previous_freeze'] == corpus['contract_freeze']['previous_sha256'])
        host['all_stop']()
        host['copy_seed_to_live']()
        for ship in host['SHIPS']:
            host['launch'](ship)
            host['wait_ready'](ship)
        for ship in host['SHIPS']:
            for source in sorted(Path('/native/core/desk').rglob('*.hoon')):
                target = host['LIVE'] / ship / 'base' / source.relative_to('/native/core/desk')
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                check('installed-byte-match:' + ship + ':' + str(source.relative_to('/native/core/desk')), sha(source) == sha(target))
                report['installed_by_ship'].setdefault(ship, {})[str(source.relative_to('/native/core/desk'))] = sha(target)
            command(ship, '|commit %base')
            clay_bytes(ship)
            command(ship, '+stead-build-probe', '%stead-builds-pass')
        command('zod', '+stead-codec-probe', '%stead-codec-six-vectors-pass')
        command('zod', '+stead-core-probe', '%stead-core-basic-and-counter-edge-pass')
        command('zod', '+stead-reducers-probe', '%stead-native-reducers-pass')
        command('zod', '|start %stead-home')
        for ship in host['SHIPS']:
            command(ship, '|start %stead-observer')
        check('fixture-initialized-once', call('zod','fixture',raw=Path('/specs/native-fixture.json').read_bytes())['json'] == {})
        report['qa'] = core_cases.run(corpus, call, snapshot, restart, export, object_matrix,
                                     trusted_now_ms=trusted_now_ms, wait_until=wait_until,
                                     classification='local-real-native-fake-ships', include_second_project=True,
                                     include_scoped_privacy=True, delivery_evidence=delivery_evidence,
                                     defer_phase1_reviews=True)
        outcomes = report['qa']['case_counts']
        expected_cases = [c['name'] for c in corpus['ordered_cases']]
        for lane in ('real_expiry_continuation','source_review_continuation','separate_project_journal_lane', 'scoped_privacy_lane'):
            expected_cases.extend(c['name'] for c in corpus[lane]['cases'])
        check('all-qa-native-cases-executed-without-failure', len(expected_cases)==148
              and [c['name'] for c in report['qa']['cases']]==expected_cases
              and sum(outcomes.values())==len(expected_cases)
              and not outcomes.get('failed') and not outcomes.get('not_run'))
        # Required missing assertions keep the current report nonpassing.
        report['qa_coverage_status'] = report['qa']['status']
        print('core: ordered, expiry, authorization and export outcomes complete', flush=True)
        codec()
        contexts()
        before = snapshot()
        for op in ('load-future','load-counter'):
            result = control((op,'bus','',''),succeeds=False)
            check('unsupported-state-specific-rejection:' + op, 'stead-unsupported-state' in result['native']['stderr'])
            check('unsupported-state-preserves-data:' + op, same(before,snapshot()))
        control(('roundtrip','bus','',''))
        check('native-on-save-on-load-roundtrip', same(before,snapshot()))
        control(('binding-drop','bus','',''),succeeds=False,sender='bud')
        check('outsider-cannot-use-fixture-control', same(before,snapshot()))
        concurrency()
        report['delivery'] = delivery_suite.run(corpus, call, snapshot=snapshot,
            pending_snapshot=lambda: call('zod', 'read', '/v1/pending-snapshot'),
            control=lambda *value: control(value), trusted_now_ms=trusted_now_ms,
            wait_until=wait_until, unavailable_home=unavailable_home, pause=pause,
            runtime_errors=runtime_logs, provenance=before_inputs,
            classification='real-native-fake-ships', probe_pool=probes, sink=delivery_sink)
        check('delivery-has-no-observed-failure', all(case['status'] in ('passed', 'incomplete')
              for case in report['delivery']['cases']))
        report['qualification'] = qualification_cases.run(call,
            classification='local-real-native-fake-ships', provenance=before_inputs)
        check('native-capacity-and-predecessor-qualification', report['qualification']['status'] == 'passed'
              and report['qualification']['native_qualified']
              and len(report['qualification']['recipes']) == 8
              and all(lane['status'] == 'executed' for lane in report['qualification']['recipes'].values()))
        report['supported_predecessor_versions'] = [1]
        # Independent artifact verification is a distinct closeout operation
        # over the completed guarded report. This runner cannot approve itself.
        report['independent_closeout'] = {
            'status': 'pending', 'manifest_sha256': before_inputs['qualification_manifest'],
            'command': 'python3 scripts/urbit/qualification_gate.py --manifest specs/urbit/v2/qualification-gate.json --evidence EVIDENCE_INDEX --bindings EXACT_BINDINGS --output CURRENT_GATE',
            'scope': 'A native execution result does not close the phase or approve a merge.'}
        report['deferred_qa_requirements'] = qualification_gate.deferred_execution(report)
        report['execution_status'] = 'completed-awaiting-independent-qualification'
        report['status'] = 'execution_complete'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        traceback.print_exc()
    report['inputs_after'] = inputs()
    try:
        report['source_commit_after'] = host['qualified_source']()
        if report.get('source_commit') != report['source_commit_after']:
            raise ValueError('Qualification source commit changed')
    except Exception as error:
        report.update(status='fail', source_binding_error=str(error))
    if before_inputs != report['inputs_after']:
        report.update(status='fail', error='Source/input changed during execution; results cannot label changed bytes')
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    report['lifecycle'] = host['EVIDENCE'][lifecycle_start:]
    report['native_tree_sha256'] = before_inputs['native']
    report['toolchain_sha256'] = before_inputs['toolchain']
    report['transport_artifact'] = transcript.close()
    path = Path('/state/logs') / ('core-' + run_id + '.json')
    report, payload = bounded_report(report)
    path.write_bytes(payload)
    return {'status':report['status'], 'checks_passed':sum(c['passed'] for c in report['checks']),
            'checks_failed':[c for c in report['checks'] if not c['passed']], 'error':report.get('error'),
            'qa_case_counts':report.get('qa',{}).get('case_counts'), 'qa_coverage_status':report.get('qa_coverage_status'),
            'elapsed_seconds':report['elapsed_seconds'], 'evidence_file':'.piers/fakes/logs/' + path.name}
