"""Closed hosted export of a completed *inspection-only* product journey.

No raw native content, callback trace, process ID, nonce or resource ID is
returned. Authored host fixtures are not native evidence. The hosted caller
must provide its actual collected guardian and actual final cleanup readback.
This path cannot turn the deliberately failed worker/job into qualification.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import product_result
from worker_result import PREFIX, canonical, unique

require, same = product_result.require, product_result.same
HASH = re.compile(r'[0-9a-f]{64}')


def _worker(raw, inputs, run_id, guard, cleanup, policy):
    require(isinstance(raw, bytes) and 0 < len(raw) <= 32 * 1024**2, 'Bounded complete worker output')
    lines = raw.decode('utf-8', errors='strict').splitlines()
    frames = [line for line in lines if line.startswith(PREFIX)]
    require(len(frames) == 1 and lines[-1] == frames[0], 'One final complete worker frame required')
    value = json.loads(frames[0][len(PREFIX):], object_pairs_hook=unique)
    require(isinstance(value, dict) and value.get('format') == 'stead.local-ci-worker/1'
            and value.get('status') == 'fail' and value.get('cleanup') is True
            and value.get('error') == 'ValueError: Native team suite failed'
            and 'cleanup_error' not in value, 'Clean intentional product inspection failure required')
    require(isinstance(run_id, str) and re.fullmatch(r'[0-9a-f]{32}', run_id)
            and value.get('run_id') == run_id
            and value.get('inputs_sha256') == hashlib.sha256(canonical(inputs)).hexdigest(), 'Exact worker input/run binding')
    sources = inputs['controller_files']
    require(hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
            == sources['scripts/ci/product_failure.py']['sha256'], 'Loaded public projector source differs')
    # Inspection bypasses the normal success verifier, so its Doc-child proof
    # must independently remain mandatory on this deliberate-failure path.
    import doc_worker_proof
    require(hashlib.sha256(Path(doc_worker_proof.__file__).read_bytes()).hexdigest()
            == sources['scripts/ci/doc_worker_proof.py']['sha256'], 'Loaded Doc proof verifier differs')
    doc_worker_proof.verify(value.get('doc_worker'),
        sources['scripts/urbit/doc_run_worker.py']['sha256'],
        sources['scripts/ci/doc_worker_proof.py']['sha256'])
    mounted = {prefix: {name[len(prefix) + 1:]: item['sha256']
                for name, item in sources.items() if name.startswith(prefix + '/')}
               for prefix in ('scripts/urbit', 'scripts/ci', 'specs/urbit', 'web/dev')}
    for name in ('scripts/release_install.py', 'scripts/sdk_native/native.py'):
        mounted[name] = sources[name]['sha256']
    mounted['native'] = {name.removeprefix('native/'): item['sha256']
                         for name, item in inputs['composed_files'].items()}
    mount_hash = hashlib.sha256(canonical(mounted)).hexdigest()
    require(value.get('mounts_before') == mount_hash == value.get('mounts_after'), 'Final immutable mounts must match')
    require(same(value.get('isolation'), {'private_network': True, 'host_credentials_absent': True,
        'fresh_state': True, 'external_route_absent': True}), 'Actual isolated fresh worker required')
    seeds = value.get('fresh_seeds')
    require(isinstance(seeds, dict) and set(seeds) == {'format', 'toolchain_sha256', 'ships'}
        and type(seeds['format']) is int and seeds['format'] == 1
        and seeds['toolchain_sha256'] == sources['specs/urbit/toolchain.lock.json']['sha256']
        and isinstance(seeds['ships'], dict) and set(seeds['ships']) == set(product_result.SHIPS)
        and all(isinstance(v, str) and HASH.fullmatch(v) for v in seeds['ships'].values()), 'Actual four fresh source-bound seeds')
    require(isinstance(guard, dict) and guard.get('status') == 'fail'
        and guard.get('error') == 'ValueError: Native worker process failed'
        and guard.get('run_id') == run_id and same(guard.get('policy'), policy)
        and same(guard.get('collector'), {'overflow': False, 'error': None, 'eof': True, 'completed': True})
        and guard.get('cleanup_errors') == [] and guard.get('child_terminated') is True
        and type(guard.get('exit_code')) is int and guard['exit_code'] == 1,
        'Actual complete collected inspection child required')
    admission = value.get('admission')
    require(isinstance(admission, dict) and same(admission, guard.get('admission'))
        and admission.get('status') == 'admitted' and admission.get('run_id') == run_id
        and admission.get('profile') == policy['profile'] and admission.get('authenticated_host') is True,
        'Exact hosted guardian/worker admission required')
    execution = value.get('native', {}).get('execution_guard')
    require(isinstance(execution, dict) and set(execution) == {'run_id', 'generation', 'guard_sha256', 'policy_sha256', 'policy'}
        and execution['run_id'] == run_id and type(execution['generation']) is int and execution['generation'] > 0
        and execution['guard_sha256'] == sources['scripts/ci/hosted.py']['sha256']
        and execution['policy_sha256'] == hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
        and same(execution['policy'], policy), 'Actual source-bound final execution guard')
    require(isinstance(cleanup, dict) and set(cleanup) == {'verified', 'unit', 'empty', 'active_state'}
        and cleanup['verified'] is True and cleanup['empty'] is True
        and cleanup['active_state'] in ('inactive', 'failed') and cleanup['unit'] == admission.get('unit')
        and cleanup['unit'] == 'stead-hosted-' + run_id + '.service', 'Actual owned outer cgroup cleanup required')
    return value


def project(raw, inputs, *, run_id, guard, cleanup, policy, release_fingerprint):
    value = _worker(raw, inputs, run_id, guard, cleanup, policy)
    observed = product_result.verify_observation(value['native'], inputs, release_fingerprint=release_fingerprint)
    require(same(value.get('product_observation'), observed), 'Independent host replay differs from worker observation')
    require(set(observed) == {'format', 'status', 'qualifies_phase', 'scope', 'full_product_partial_restore',
        'browser', 'result', 'assertions', 'callbacks'} and observed['format'] == 'stead.product-journey-observation/1'
        and observed['status'] == 'observed' and observed['qualifies_phase'] is False
        and observed['full_product_partial_restore'] == 'not-observed' and observed['browser'] == 'not-observed'
        and type(observed['assertions']) is int and 0 < observed['assertions'] <= 2000
        and type(observed['callbacks']) is int and 0 < observed['callbacks'] <= 256, 'Closed product observation scope/counts')
    result = observed['result']
    require(isinstance(result, dict) and set(result) == {'profile', 'scope', 'project_id', 'work_id', 'change_id',
        'document_id', 'accepted_markdown_sha256', 'final_fingerprints'}
        and result['profile'] == 'native-human-doc/1'
        and result['scope'] == 'actual native Gall; HTTP/browser/agent-run not included'
        and isinstance(result['accepted_markdown_sha256'], str) and HASH.fullmatch(result['accepted_markdown_sha256']),
        'Closed exact human journey result')
    fingerprints = result['final_fingerprints']
    require(isinstance(fingerprints, dict) and set(fingerprints) == {'release_authority', 'review_authority', 'release_vase', 'lifecycle_vase'}
        and all(isinstance(v, str) and HASH.fullmatch(v) for v in fingerprints.values())
        and fingerprints['release_authority'] == fingerprints['review_authority']
        and fingerprints['release_vase'] == fingerprints['lifecycle_vase'], 'Final actual helper hash agreement')
    # Fixed keys and fixed labels only. No arbitrary native string is copied.
    return {'format': 'stead.product-inspection-export/1', 'status': 'observed', 'qualifies_phase': False,
        'profile': 'native-human-doc/1', 'scope': 'native-human-doc-journey-and-predecessor-pause',
        'worker_output_sha256': hashlib.sha256(raw).hexdigest(),
        'inputs_sha256': hashlib.sha256(canonical(inputs)).hexdigest(),
        'verified_observation_sha256': hashlib.sha256(canonical(observed)).hexdigest(),
        'accepted_markdown_sha256': result['accepted_markdown_sha256'],
        'final_authority_sha256': fingerprints['release_authority'], 'final_saved_vase_sha256': fingerprints['release_vase'],
        'assertions': observed['assertions'], 'callbacks': observed['callbacks'],
        'owned_cold_restarts': 16, 'paused_predecessor': True, 'full_product_partial_restore': False,
        'browser': False, 'agent_run': False, 'outer_cleanup_verified': True}
