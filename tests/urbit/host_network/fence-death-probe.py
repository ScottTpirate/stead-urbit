"""Real parent-death controls for the privileged nft helper."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import owned_child

FIFO = Path('/tmp/delayed-nft')


def dead(pid):
    try:
        return Path(f'/proc/{pid}/stat').read_text().split()[2] == 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return True


if len(sys.argv) > 1:
    process = subprocess.Popen(owned_child.command(['/usr/bin/nft', '-f', str(FIFO)], privileged=True),
                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 2
    while Path(f'/proc/{process.pid}/comm').read_text().strip() != 'nft':
        assert process.poll() is None and time.monotonic() < deadline
        time.sleep(.01)
    print(process.pid, flush=True)
    sys.stdin.read()
else:
    os.mkfifo(FIFO, 0o600)
    controller = subprocess.Popen(['/usr/bin/python3', '-B', __file__, 'controller'],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    nft_pid = int(controller.stdout.readline())
    controller.kill()
    controller.wait(timeout=2)
    deadline = time.monotonic() + 2
    while not dead(nft_pid) and time.monotonic() < deadline:
        time.sleep(.01)
    assert dead(nft_pid), 'Orphan nft survived controller death'
    # A delayed valid transaction cannot execute after its controller dies.
    descriptor = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK)
    os.write(descriptor, b'create table inet after_dead_controller\n')
    os.close(descriptor)
    result = subprocess.run(['/usr/bin/nft', 'list', 'table', 'inet', 'after_dead_controller'], capture_output=True)
    assert result.returncode != 0, 'Dead helper committed delayed rules'
    # A wrapper reaching admission after its original controller has died must
    # refuse before nft, even though it now has a different live parent.
    late = subprocess.run(['/usr/bin/python3', '-B', str(Path(owned_child.__file__)), str(controller.pid),
                           'controller', '/usr/bin/nft', 'create', 'table', 'inet', 'late_controller'], capture_output=True)
    assert late.returncode != 0 and b'Controller exited before child admission' in late.stderr
    result = subprocess.run(['/usr/bin/nft', 'list', 'table', 'inet', 'late_controller'], capture_output=True)
    assert result.returncode != 0
    print(json.dumps({'classification': 'real-host-private-network-parent-death',
                      'checks': ['in-flight-nft-killed', 'delayed-transaction-absent', 'late-child-refused'], 'passed': True}))
