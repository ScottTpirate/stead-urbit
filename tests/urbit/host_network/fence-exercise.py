"""Real disposable-namespace UDP controls, not a native Urbit test."""
import json
import os
from pathlib import Path
import selectors
import socket
import subprocess
import sys
import time
import native_peer_fence as fence
import owned_child


def child(port, family):
    channel = socket.socket(socket.AF_INET6 if family == '6' else socket.AF_INET, socket.SOCK_DGRAM)
    address = '::1' if family == '6' else '127.0.0.1'
    channel.bind((address, port))
    channel.settimeout(.12)
    print('ready', flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request['op'] == 'send':
            try:
                channel.sendto(request['text'].encode(), (address, request['port']))
                value = True
            except PermissionError:
                value = False
        elif request['op'] == 'recv':
            try:
                value = channel.recvfrom(100)[0].decode()
            except TimeoutError:
                value = None
        elif request['op'] == 'nft':
            result = subprocess.run(['/usr/bin/nft', 'flush', 'ruleset'], capture_output=True)
            value = result.returncode
        else:
            raise ValueError('Unknown child operation')
        print(json.dumps(value), flush=True)


def exercise(host_namespace):
    errors = []
    checks = []
    children = []
    controller = fence.NativePeerFence(host_namespace, lambda: None, lambda error: errors.append(str(error)))
    def start(port, family='4'):
        process = subprocess.Popen(owned_child.command(['/usr/bin/python3', '-B', __file__, 'child', str(port), family]),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        children.append(process)
        assert process.stdout.readline().strip() == 'ready'
        return process
    def call(process, op, **kw):
        process.stdin.write(json.dumps(dict(op=op, **kw)) + '\n')
        process.stdin.flush()
        with selectors.DefaultSelector() as poll:
            poll.register(process.stdout, selectors.EVENT_READ)
            assert poll.select(3), 'Child control response timed out'
        return json.loads(process.stdout.readline())
    def check(name, condition):
        checks.append({'name': name, 'passed': bool(condition)})
        assert condition, name
    def packet(sender, receiver, port, token, allowed):
        call(sender, 'send', port=port, text=token)
        check(token, call(receiver, 'recv') == (token if allowed else None))
    try:
        zod, bus, bud = start(31337), start(31519), start(31339)
        v6zod, v6bus = start(31337, '6'), start(31519, '6')
        packet(zod, bus, 31519, 'before-admission', False)
        proof = controller.release('zod', zod)
        check('caps-dropped', bool(proof['capabilities']))
        check('native-socket-inode-bound', proof['socket']['inode'].isdigit())
        packet(zod, bus, 31519, 'one-endpoint-only', False)
        controller.release('bus', bus)
        packet(zod, bus, 31519, 'both-ready-outbound', True)
        packet(bus, zod, 31337, 'both-ready-return', True)
        packet(bud, zod, 31337, 'unready-third-peer', False)
        packet(v6zod, v6bus, 31519, 'ipv6-always-denied', False)
        check('child-cannot-change-rules', call(zod, 'nft') != 0)
        controller.block('zod')
        packet(bus, zod, 31337, 'block-established-peer', False)
        controller.block('bus')
        controller.release('zod', zod)
        zod.terminate()
        zod.wait(timeout=2)
        deadline = time.monotonic() + 1.5
        while True:
            with controller.lock:
                if not controller.ready:
                    check('last-child-removes-ready', True)
                    controller.verify(set())
                    check('kernel-empty-after-last-child', True)
                    break
            assert time.monotonic() < deadline, 'Last child ready entry did not close'
            time.sleep(.02)
        controller.release('bus', bus)
        controller.run('delete rule inet stead_fakes peer_input handle 5\ndelete rule inet stead_fakes peer_output handle 7\n')
        deadline = time.monotonic() + 1.5
        while not errors and time.monotonic() < deadline:
            time.sleep(.02)
        with controller.lock:
            check('both-missing-drop-rules-latch-failure', controller.closed.is_set() and bool(errors))
            controller.verify(set())
            check('failure-restores-full-deny-policy', controller.kernel_state == 'verified-empty')
            raw = subprocess.check_output(['/usr/bin/nft', '-j', 'list', 'set', 'inet', 'stead_fakes', 'ready'])
        check('failure-clears-kernel-ready', not next(row['set'] for row in json.loads(raw)['nftables'] if 'set' in row).get('elem'))
        try:
            controller.release('bus', bus)
        except ValueError:
            check('failed-controller-cannot-reopen', True)
        else:
            raise AssertionError('Failed controller reopened')
    finally:
        for process in children:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=2)
        if not controller.closed.is_set():
            controller.close()
    print(json.dumps({'classification': 'real-host-private-network-controls', 'checks': checks, 'failure_control': errors}), flush=True)


if __name__ == '__main__':
    if sys.argv[1] == 'child':
        child(int(sys.argv[2]), sys.argv[3])
    else:
        exercise(sys.argv[1])
