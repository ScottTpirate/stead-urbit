"""Read-only evidence from the authenticated hosted resource monitor.

This provider never reads or invents workstation temperatures. Hosted thermal
management is explicitly provider-managed and unmeasured by this job.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time

import execution_policy
import hosted_apparmor

POLICY = {'profile': 'github-hosted-native/1', 'cpu_max': '20000 10000',
          'memory_max': 12 * 1024**3, 'memory_swap_max': 0, 'pids_max': 256,
          'sample_seconds': 1, 'stale_seconds': 3, 'deadline_seconds': 7200,
          'thermal': 'provider-managed-unmeasured', 'apparmor_profile': hosted_apparmor.PROFILE,
          'apparmor_policy_sha256': hosted_apparmor.POLICY_SHA256}


def require(condition, message):
    if not condition:
        raise execution_policy.GuardError(message)


def validate(value, *, run_id, now, guard_sha256, cpus):
    require(isinstance(value, dict) and value.get('format') == 'stead.hosted-lease/1'
            and value.get('state') == 'running' and value.get('run_id') == run_id,
            'Hosted lease identity/state differs')
    require(json.dumps(value.get('policy'), sort_keys=True) == json.dumps(POLICY, sort_keys=True)
            and value.get('guard_sha256') == guard_sha256
            and value.get('policy_sha256') == hashlib.sha256(json.dumps(POLICY, sort_keys=True).encode()).hexdigest(),
            'Hosted lease source/policy differs')
    require(type(value.get('generation')) is int and value['generation'] > 0, 'Hosted generation absent')
    times = [value.get(key) for key in ('started', 'observed_at', 'deadline')]
    require(all(type(item) in (int, float) and math.isfinite(item) for item in [now, *times]), 'Hosted clock type')
    started, observed, deadline = times
    require(0 <= started <= observed <= now < deadline and now - observed <= 3
            and deadline - started == 7200, 'Hosted lease stale, future, reversed or expired')
    require(value.get('cpus') == cpus and len(cpus) == 2 and len(set(cpus)) == 2,
            'Hosted CPU identity differs')
    unit = 'stead-hosted-' + run_id + '.service'
    require(value.get('unit') == unit and value.get('cgroup') == '/system.slice/' + unit,
            'Hosted cgroup identity differs')
    require(value.get('limits') == {'cpu.max': POLICY['cpu_max'], 'memory.max': str(POLICY['memory_max']),
            'memory.swap.max': '0', 'pids.max': '256'}, 'Hosted kernel limit evidence differs')
    require(value.get('resource_events') == {'oom': 0, 'oom_kill': 0, 'pids_max': 0}, 'Hosted resource failure')
    require(value.get('authenticated_host') is True, 'Hosted admission was not authenticated')
    service = value.get('service', {})
    expected_service = {'KillMode': 'control-group', 'ExitType': 'main', 'RemainAfterExit': 'no',
        'Restart': 'no', 'OOMPolicy': 'kill', 'RuntimeMaxUSec': '2h', 'TimeoutStopUSec': '15s',
        'Delegate': 'no', 'memory.oom.group': '1', 'AppArmorProfile': hosted_apparmor.PROFILE}
    require(set(service) == {*expected_service, 'MainPID'}
            and all(service.get(key) == item for key, item in expected_service.items())
            and re.fullmatch(r'[1-9][0-9]{0,9}', service.get('MainPID', '')), 'Hosted service lifetime differs')
    require(value.get('apparmor') == {'profile': hosted_apparmor.PROFILE,
        'policy_sha256': hosted_apparmor.POLICY_SHA256,
        'settings': dict.fromkeys(hosted_apparmor.SYSCTLS, '1')}, 'Hosted AppArmor observation differs')
    return value


def progression(previous, value):
    if previous is None:
        return
    immutable = ('run_id', 'started', 'deadline', 'cpus', 'unit', 'cgroup', 'service',
        'policy', 'guard_sha256', 'policy_sha256', 'authenticated_host', 'apparmor')
    require(all(value[key] == previous[key] for key in immutable), 'Hosted lifetime identity changed')
    require(value['generation'] >= previous['generation']
            and value['observed_at'] >= previous['observed_at'], 'Hosted heartbeat moved backwards')
    require(value['generation'] != previous['generation'] or value == previous,
            'Hosted heartbeat changed without a generation')


class HostedProvider:
    def __init__(self):
        self.control = Path('/execution')
        require(os.statvfs(self.control).f_flag & os.ST_RDONLY, 'Hosted control must be read-only')
        self.run_id = os.environ.get('STEAD_EXECUTION_ID', '')
        require(re.fullmatch(r'[0-9a-f]{32}', self.run_id), 'Missing hosted execution identity')
        self.cpus = sorted(os.sched_getaffinity(0))
        self.guard_sha256 = hashlib.sha256(Path('/ci/hosted.py').read_bytes()).hexdigest()
        self.previous = None
        self.lock = threading.Lock()
        self.require(preflight=True)

    def require(self, preflight=False):
        with self.lock:
            return self._require()

    def _require(self):
        hosted_apparmor.require_label()
        require(not (self.control / 'STOP').exists(), 'Hosted execution stop is terminal')
        require(sorted(os.sched_getaffinity(0)) == self.cpus, 'Hosted affinity changed')
        value = validate(execution_policy.read_json(self.control / 'lease.json'),
            run_id=self.run_id, now=time.monotonic(), guard_sha256=self.guard_sha256, cpus=self.cpus)
        progression(self.previous, value)
        self.previous = value
        return value

    @staticmethod
    def observed(value):
        return value['observed_at']

    @staticmethod
    def summary(value):
        return {key: value[key] for key in ('run_id', 'generation', 'guard_sha256', 'policy_sha256', 'policy')}
