"""Actual nft transaction failure controls inside a disposable namespace."""
import json
import subprocess
import sys
import native_peer_fence as fence
import owned_child


def readback(*arguments):
    result = subprocess.run(owned_child.command([owned_child.nft_binary(), '-j', *arguments], privileged=True),
        capture_output=True, timeout=1)
    assert result.returncode == 0 and not result.stderr and len(result.stdout) <= 16384
    return json.loads(result.stdout)['nftables']


invalid = 'add rule inet stead_fakes missing_chain drop\n'
try:
    fence.NativePeerFence.run(fence.POLICY + invalid)
except RuntimeError:
    assert all('table' not in row for row in readback('list', 'tables'))
else:
    raise AssertionError('Invalid installation succeeded')
errors = []
controller = fence.NativePeerFence(sys.argv[1], lambda: None, lambda error: errors.append(str(error)))
try:
    with controller.lock:
        before = readback('list', 'table', 'inet', fence.TABLE)
        try:
            controller.run('destroy table inet stead_fakes\n' + fence.POLICY + invalid)
        except RuntimeError:
            assert readback('list', 'table', 'inet', fence.TABLE) == before
            controller.verify(set())
        else:
            raise AssertionError('Invalid replacement succeeded')
finally:
    controller.close()
assert not errors and not controller.monitor.is_alive()
print(json.dumps({'classification': 'real-host-private-network-atomicity', 'passed': True,
    'checks': ['failed-install-leaves-no-table', 'failed-replacement-preserves-exact-policy']}))
