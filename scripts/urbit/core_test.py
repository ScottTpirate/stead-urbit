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
import core_conn
import core_cases
import core_export
from digests import sha, source_sha, tree_sha

CODE = Path(__file__).parent
DEPENDENCIES = ('core_test.py', 'core_conn.py', 'core_cases.py', 'core_export.py')


def closure():
    return {name: sha(CODE / name) for name in DEPENDENCIES}


LOADED_CLOSURE = closure()


def inputs():
    return {'native': tree_sha(Path('/native/core/desk')), 'runner': closure(),
            'harness': source_sha(CODE), 'toolchain': sha('/toolchain.json'),
            'fixture': sha('/specs/native-fixture.json'), 'cases': sha('/specs/fixtures/native-cases.json'),
            'vectors': sha('/specs/fixtures/commands.json'), 'freeze': sha('/specs/contract-freeze.json')}


def run(host):
    started = time.monotonic()
    run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())
    report = {'status': 'fail', 'classification': 'local-real-native-fake-ships',
              'checks': [], 'commands': [], 'coverage_limits': [
                  'Synthetic sender bindings; no live/browser authentication or production isolation.',
                  'Warm process restart and declared on-load checks; no abrupt crash-window injection.',
                  'Delivery reducer is executed; full adversarial Gall subscription races remain separate.',
                  'Native document objects exported through stock Git; no Smart HTTP forge.',
                  'UUID collisions and project sequence counters remain metadata confidentiality gates.']}
    before_inputs = inputs()
    report['inputs_before'] = before_inputs
    lifecycle_start = len(host['EVIDENCE'])
    export_count = 0

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

    binary = '/runtime/' + host['LOCK']['runtime']['binary']

    def call(ship, mode, route='/', raw=b'', **kwargs):
        result = core_conn.run(binary, host['LIVE'] / ship / '.urb/conn.sock', mode, route, raw, **kwargs)
        record = {'ship':ship, 'mode':mode, 'route':route, 'input_sha256':hashlib.sha256(raw).hexdigest(),
                  'input_bytes':len(raw), **result}
        # Large malformed bytes are reproducible from the immutable corpus.
        if len(record['request']) > 16384:
            record['request_sha256'] = hashlib.sha256(record.pop('request').encode()).hexdigest()
            record['request_omission'] = 'Large input: exact bytes are specified by the hashed corpus recipe.'
        report['commands'].append(record)
        return {**(result['outcome'] or {'raw':None, 'json':None}), 'native':record}

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
        return core_export.export(call, destination, ship, project, container, snapshot)

    def object_matrix(case, captures):
        ids = corpus['fixture_ids']
        project = ids['project']
        bus_container, zod_container = ids['bus_container'], ids['zod_container']
        bus = captures[case['action']['base_manifest_from']]['export']
        bus_head = bus['snapshot_commit_oid']
        bus_blob = next(oid for oid, obj in bus['objects'].items() if obj['kind'] == 'blob')
        zod = call('zod', 'read', f'/v1/git/{project}/{zod_container}')['json']['payload']
        zod_head = zod['snapshot_commit_oid']
        zod_blob = next(oid for oid, kind in zod['objects'].items() if kind == 'blob')
        variations = [(bus_container,bus_head,bus_blob), (zod_container,zod_head,zod_blob),
                      (bus_container,zod_head,zod_blob), (zod_container,bus_head,bus_blob),
                      (bus_container,'0'*40,bus_blob), (bus_container,bus_head,'0'*40)]
        return {'variants':[{'name':name, 'response':call('bus','read',f'/v1/git-object/{project}/{cid}/{head}/{oid}')}
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

    def codec():
        cases = []
        for index, vector in enumerate(json.loads(Path('/specs/fixtures/commands.json').read_text())):
            cases.append((f'frozen-vector-{index}', core_cases.canonical(vector['request']), 'accept', vector))
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
                digest = core_cases.command_digest(canonical)
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
        route = f"/v1/result/~bus/{core_cases.BINDINGS['bus']}/{cmd['project_id']}/{cmd['request_id']}/{core_cases.command_digest(raw)}"
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
            route = f"/v1/result/~{ship}/{core_cases.BINDINGS[ship]}/{cmd['project_id']}/{cmd['request_id']}/{core_cases.command_digest(raw)}"
            requests.append((ship,cmd,route,raw))
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(call,ship,'command',route,raw) for ship,cmd,route,raw in requests]
            results = [future.result() for future in pending]
        accepted = [i for i,r in enumerate(results) if r['json'] and r['json'].get('status') == 'accepted']
        rejected = [r for r in results if r['json'] == {'protocol':'stead.result/1','status':'rejected','error':'revision_conflict'}]
        check('two-principal-concurrent-cas-one-winner', len(accepted)==1 and len(rejected)==1)
        winner = accepted[0]
        check('concurrent-receipt-trusted-sender', results[winner]['json']['principal_id'] == corpus['principals'][requests[winner][0]]
              and results[winner]['json']['resource_revision']=='5')
        view = call('nec','read',f"/v1/work/{ids['project']}/{ids['work_a']}")
        check('concurrent-winner-visible-to-reader', view['json']['payload'] == requests[winner][1]['payload'] and view['json']['resource_revision']=='5')
        after = snapshot()
        check('concurrent-cas-one-acceptance', int(after['journal_events'])==int(before['journal_events'])+1
              and int(after['receipts'])==int(before['receipts'])+1 and after['objects']==before['objects'])
        path = f"/v1/document/{ids['project']}/{ids['document_a']}"
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(call,ship,'read',path) for ship in ('bus','bud')]
            owner,outsider = [future.result() for future in pending]
        check('concurrent-same-path-read-separation', owner['json']['payload']['markdown']==corpus['commands']['document_a_2']['payload']['markdown']
              and outsider['json']==core_cases.DENIAL)
        bus,cmd,route,raw = requests[0]
        denied = call('bud','command',route,raw)
        check('sender-cannot-reserve-another-result-route', denied['json'] is None and 'stead-watch-denied' in denied['native']['stderr'])
        check('concurrent-reads-and-wrong-route-preserve-state', same(after,snapshot()))
        report['concurrent_submissions'] = [{'sender':r[0], 'command':r[1], 'response':out} for r,out in zip(requests,results,strict=True)]

    try:
        check('loaded-supervisor-source-matches', before_inputs['harness'] == host['LOADED_SOURCE_DIGEST'])
        check('loaded-core-runner-source-matches', before_inputs['runner'] == LOADED_CLOSURE)
        corpus = json.loads(Path('/specs/fixtures/native-cases.json').read_text())
        check('frozen-contract-manifest-matches-corpus', before_inputs['freeze'] == corpus['contract_freeze']['sha256'])
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
            command(ship, '|commit %base')
            clay_bytes(ship)
            command(ship, '+stead-build-probe', '%stead-builds-pass')
        command('zod', '+stead-codec-probe', '%stead-codec-six-vectors-pass')
        command('zod', '+stead-reducers-probe', '%stead-native-reducers-pass')
        command('zod', '|start %stead-home')
        check('fixture-initialized-once', call('zod','fixture',raw=Path('/specs/native-fixture.json').read_bytes())['json'] == {})
        report['qa'] = core_cases.run(corpus, call, snapshot, restart, export, object_matrix,
                                     trusted_now_ms=trusted_now_ms, wait_until=wait_until,
                                     classification='local-real-native-fake-ships', include_second_project=True)
        outcomes = report['qa']['case_counts']
        expected_cases = [c['name'] for c in corpus['ordered_cases']]
        for lane in ('real_expiry_continuation','source_review_continuation','separate_project_journal_lane'):
            expected_cases.extend(c['name'] for c in corpus[lane]['cases'])
        check('all-qa-native-cases-executed-without-failure', len(expected_cases)==129
              and [c['name'] for c in report['qa']['cases']]==expected_cases
              and sum(outcomes.values())==len(expected_cases)
              and not outcomes.get('failed') and not outcomes.get('not_run'))
        # Preserve independent QA's incomplete/source-only assertions verbatim.
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
        report['supported_predecessor_versions'] = []
        report['status'] = 'pass'
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
        traceback.print_exc()
    report['inputs_after'] = inputs()
    if before_inputs != report['inputs_after']:
        report.update(status='fail', error='Source/input changed during execution; results cannot label changed bytes')
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    report['lifecycle'] = host['EVIDENCE'][lifecycle_start:]
    report['native_tree_sha256'] = before_inputs['native']
    report['toolchain_sha256'] = before_inputs['toolchain']
    path = Path('/state/logs') / ('core-' + run_id + '.json')
    path.write_text(json.dumps(report, indent=2) + '\n')
    return {'status':report['status'], 'checks_passed':sum(c['passed'] for c in report['checks']),
            'checks_failed':[c for c in report['checks'] if not c['passed']], 'error':report.get('error'),
            'qa_case_counts':report.get('qa',{}).get('case_counts'), 'qa_coverage_status':report.get('qa_coverage_status'),
            'elapsed_seconds':report['elapsed_seconds'], 'evidence_file':'.piers/fakes/logs/' + path.name}
