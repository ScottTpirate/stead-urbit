"""Real thread and process lifetime controls for owned native launches."""
import json
import select
from pathlib import Path
import subprocess
import sys
import threading
import time
import owned_child
import native_peer_fence


def create_from_worker(launcher):
    result = []
    worker = threading.Thread(target=lambda: result.append(launcher.spawn(
        ['/usr/bin/python3', '-B', '-c', "import time; print('ready', flush=True); time.sleep(30)"],
        stdout=subprocess.PIPE)))
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive() and len(result) == 1
    process = result[0]
    assert select.select([process.stdout], [], [], 2)[0], 'Child did not reach its unprivileged executable'
    assert process.stdout.readline(32) == b'ready\n'
    process.stdout.close()
    assert process.poll() is None, 'Child died with requesting worker'
    native_peer_fence.require_confined_child(process)
    return process


def dead(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split()[2] == 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return True


if len(sys.argv) > 1:
    launcher = owned_child.ChildLauncher()
    process = create_from_worker(launcher)
    try:
        launcher.close()
    except RuntimeError:
        pass
    else:
        raise AssertionError('Launcher closed with live child')
    print(process.pid, flush=True)
    sys.stdin.read()
else:
    controller = subprocess.Popen(['/usr/bin/python3', '-B', __file__, 'controller'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    child = int(controller.stdout.readline())
    assert not dead(child)
    controller.kill()
    controller.wait(timeout=2)
    deadline = time.monotonic() + 2
    while not dead(child) and time.monotonic() < deadline:
        time.sleep(.01)
    assert dead(child), 'Owned fixture outlived its controller'
    launcher = owned_child.ChildLauncher()
    process = create_from_worker(launcher)
    process.terminate()
    process.wait(timeout=2)
    launcher.close()
    try:
        launcher.spawn(['/usr/bin/sleep', '30'])
    except RuntimeError:
        pass
    else:
        raise AssertionError('Closed launcher accepted child')
    print(json.dumps({'classification': 'real-host-child-lifetime-controls', 'passed': True,
                      'checks': ['request-worker-exit-preserves-child', 'child-has-no-capabilities',
                                 'live-child-prevents-launcher-close', 'controller-death-kills-child',
                                 'reaped-child-allows-clean-close', 'closed-launcher-refuses-spawn']}))
