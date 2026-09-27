import json
import sys
import native_peer_fence as fence

errors = []
controller = fence.NativePeerFence(sys.argv[1], lambda: None, lambda error: errors.append(str(error)))
# Stop automatic refresh, then inject missing-policy failure into close itself.
controller.closed.set()
controller.monitor.join(timeout=2)
controller.run('destroy table inet stead_fakes\n')
try:
    controller.close()
except RuntimeError:
    assert errors and controller.closed.is_set()
    assert controller.kernel_state == 'verified-empty'
    controller.verify(set())
else:
    raise AssertionError('Missing-policy close reported success')
print(json.dumps({'classification': 'real-host-private-network-close-failure', 'passed': True,
                  'checks': ['close-error-propagated', 'cleanup-notified', 'full-deny-policy-restored']}))
