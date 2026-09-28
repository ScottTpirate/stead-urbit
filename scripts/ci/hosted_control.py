"""Actual hosted resource/lifetime control; deliberately executes no Hoon."""
import json
import os
import subprocess
import sys
import time
sys.path[:0] = ['/code', '/ci']
import execution_policy
from hosted_lease import HostedProvider
import worker
import native_peer_fence
import owned_child

provider = HostedProvider()
worker.admission(provider)
inputs = execution_policy.read_json('/ci-inputs.json', maximum=1024 * 1024)
worker.mounted_inputs(inputs)
isolation = worker.isolation(inputs)
failures = []
try:
    fence = native_peer_fence.NativePeerFence(inputs['host_network_namespace'], provider.require,
        lambda error: failures.append(type(error).__name__))
except Exception:
    # Fixed synthetic policy only, before any candidate/native process starts.
    # Preserve the refusal; readback is diagnostic data, never admission.
    for arguments in (['--version'], ['-j', 'list', 'table', 'inet', native_peer_fence.TABLE]):
        result = subprocess.run(owned_child.command([owned_child.nft_binary(), *arguments], privileged=True),
            capture_output=True, timeout=2)
        print('STEAD_HOSTED_CONTROL_PACKET_DIAGNOSTIC ' + json.dumps({
            'arguments': arguments, 'exit_code': result.returncode,
            'stdout': result.stdout[:4096].decode('utf-8', errors='replace'),
            'stderr': result.stderr[:1024].decode('utf-8', errors='replace'),
            'truncated': len(result.stdout) > 4096 or len(result.stderr) > 1024}), flush=True)
    raise
fence.close()
worker.require(not failures and not fence.monitor.is_alive(), 'Pre-native packet controller failed')
child = subprocess.Popen(['/usr/bin/python3', '-I', '-B', '-c', 'import time; time.sleep(60)'],
    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    env={'PATH': '/usr/bin:/bin'})
worker.require(os.getpgid(child.pid) == child.pid and child.poll() is None, 'Detached control descendant absent')
print('STEAD_HOSTED_CONTROL_READY ' + json.dumps({'run_id': provider.run_id,
    'detached_descendant': True, 'isolation': isolation, 'peer_fence_verified': True}), flush=True)
deadline = time.monotonic() + 60
try:
    while time.monotonic() < deadline:
        provider.require()
        time.sleep(.05)
    raise RuntimeError('Control did not interrupt its owned worker')
except execution_policy.GuardError as error:
    print('STEAD_HOSTED_CONTROL_REFUSED ' + json.dumps({'run_id': provider.run_id,
        'reason': str(error)}), flush=True)
    raise SystemExit(1)
# The detached descendant intentionally outlives this worker. Only the owned
# service/namespace cleanup can satisfy the parent-side empty-cgroup assertion.
