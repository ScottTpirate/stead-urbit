"""Native peer barrier for a trusted fixture namespace, not hostile child isolation.

Only the controller retains namespace-local NET_ADMIN/SETPCAP. Vere and its
workers must have no capabilities. Lens/Khan/state remain inside the trusted
four-ship fixture boundary. This module is never run in the host net namespace.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import owned_child

PORTS = {'zod': 31337, 'bus': 31519, 'nec': 31338, 'bud': 31339}
DROP_CAPABILITIES = ['setpriv', '--bounding-set=-all', '--inh-caps=-all',
                     '--ambient-caps=-all', '--no-new-privs', '--']
TABLE = 'stead_fakes'
# Explicit statements share one atomic transaction. nftables 1.0.9 accepts a
# nested `create table` body but creates only the table; exact readback rejects it.
POLICY = '''create table inet stead_fakes
add set inet stead_fakes ready { type inet_service; flags timeout; timeout 2s; }
add chain inet stead_fakes peer_input { type filter hook input priority -300; policy accept; }
add chain inet stead_fakes peer_output { type filter hook output priority -300; policy accept; }
add rule inet stead_fakes peer_input iifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 udp sport @ready udp dport @ready accept
add rule inet stead_fakes peer_input meta l4proto udp counter drop
add rule inet stead_fakes peer_output oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 udp sport @ready udp dport @ready accept
add rule inet stead_fakes peer_output meta l4proto udp counter drop
'''


def capabilities(pid):
    fields = dict(line.split(':', 1) for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line)
    return {key: fields[key].strip() for key in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd', 'NoNewPrivs')}


def require_confined_child(process):
    if process.poll() is not None:
        raise ValueError('Native child is not live')
    pending, seen, records = [process.pid], set(), {}
    while pending:
        pid = pending.pop()
        if pid in seen:
            continue
        seen.add(pid)
        if len(seen) > 32:
            raise ValueError('Owned process tree bound')
        state = capabilities(pid)
        if state['NoNewPrivs'] != '1' or any(value != '0000000000000000' for key, value in state.items() if key != 'NoNewPrivs'):
            raise ValueError('Native process retains privileges')
        records[str(pid)] = state
        for task in Path(f'/proc/{pid}/task').iterdir():
            try:
                pending.extend(int(value) for value in (task / 'children').read_text().split())
            except FileNotFoundError:
                continue
    if process.poll() is not None:
        raise ValueError('Child exited during privilege verification')
    return records


def require_owned_udp(process, ship):
    expected = PORTS[ship]
    sockets = set()
    for descriptor in Path(f'/proc/{process.pid}/fd').iterdir():
        try:
            target = descriptor.readlink().as_posix()
        except FileNotFoundError:
            continue
        found = re.fullmatch(r'socket:\[(\d+)\]', target)
        if found:
            sockets.add(found[1])
    rows = []
    owned = []
    for line in Path('/proc/net/udp').read_text().splitlines()[1:]:
        fields = line.split()
        rows.append((fields[1], fields[9]))
        if fields[9] in sockets:
            owned.append((fields[1], fields[9]))
    endpoint = '0100007F:' + f'{expected:04X}'
    matches = [row for row in rows if row[0] == endpoint]
    if len(matches) != 1 or matches[0] not in owned or process.poll() is not None:
        raise ValueError('Exclusive owned loopback Mesa socket not established')
    namespace = os.readlink(f'/proc/{process.pid}/ns/net')
    if namespace != os.readlink('/proc/self/ns/net'):
        raise ValueError('Native child outside owned network namespace')
    return {'ship': ship, 'pid': process.pid, 'endpoint': endpoint, 'inode': matches[0][1], 'network_namespace': namespace}


def require_policy(rows):
    expected = [{'table': {'family': 'inet', 'name': TABLE}},
                *[{'chain': {'family': 'inet', 'table': TABLE, 'name': 'peer_' + direction,
                            'type': 'filter', 'hook': direction, 'prio': -300, 'policy': 'accept'}}
                  for direction in ('input', 'output')],
                {'set': {'family': 'inet', 'name': 'ready', 'table': TABLE,
                         'type': 'inet_service', 'flags': ['timeout'], 'timeout': 2}}]
    for direction, interface in (('input', 'iifname'), ('output', 'oifname')):
        base = {'family': 'inet', 'table': TABLE, 'chain': 'peer_' + direction}
        matches = [({'meta': {'key': interface}}, 'lo'),
                   ({'payload': {'protocol': 'ip', 'field': 'saddr'}}, '127.0.0.1'),
                   ({'payload': {'protocol': 'ip', 'field': 'daddr'}}, '127.0.0.1'),
                   ({'payload': {'protocol': 'udp', 'field': 'sport'}}, '@ready'),
                   ({'payload': {'protocol': 'udp', 'field': 'dport'}}, '@ready')]
        expected.append({'rule': dict(base, expr=[{'match': {'op': '==', 'left': left, 'right': right}}
                                                 for left, right in matches] + [{'accept': None}])})
        expected.append({'rule': dict(base, expr=[{'match': {'op': '==', 'left': {'meta': {'key': 'l4proto'}}, 'right': 17}},
                                                  {'counter': {}}, {'drop': None}])})
    observed = []
    metadata = 0
    for row in rows:
        if not isinstance(row, dict) or len(row) != 1:
            raise ValueError('Native peer policy row shape')
        key, value = next(iter(row.items()))
        if key == 'metainfo':
            metadata += 1
            if value.get('json_schema_version') != 1:
                raise ValueError('Native peer nft schema version')
            continue
        value = copy.deepcopy(value)
        value.pop('handle', None)
        if key == 'set':
            value.pop('elem', None)
        if key == 'rule':
            for expression in value.get('expr', []):
                if 'counter' in expression:
                    count = expression['counter']
                    if set(count) != {'packets', 'bytes'} or any(type(n) is not int or n < 0 for n in count.values()):
                        raise ValueError('Native peer counter shape')
                    expression['counter'] = {}
        observed.append({key: value})
    # nft 1.0.9 lists sets before chains; newer versions list chains first.
    # Declaration display order is immaterial. Preserve every exact field,
    # multiplicity and rule sequence; never sort or coalesce packet rules.
    declaration_key = lambda row: json.dumps(row, sort_keys=True)
    declarations = sorted((row for row in observed if 'rule' not in row), key=declaration_key)
    rules = [row for row in observed if 'rule' in row]
    if (metadata != 1 or declarations != sorted(expected[:4], key=declaration_key)
            or rules != expected[4:]):
        raise ValueError('Native peer packet rules changed')


class NativePeerFence:
    def __init__(self, host_namespace, guard, failed):
        namespace = os.readlink('/proc/self/ns/net')
        if (os.getuid() != 0 or not re.fullmatch(r'net:\[\d+\]', host_namespace)
                or namespace == host_namespace):
            raise ValueError('Fresh owned user/network namespace required')
        state = capabilities('self')
        if any(state[key] != '0000000000001100' for key in ('CapEff', 'CapPrm', 'CapInh', 'CapAmb', 'CapBnd')):
            raise ValueError('Controller requires exactly namespace NET_ADMIN and SETPCAP')
        self.guard, self.failed = guard, failed
        self.lock = threading.RLock()
        self.closed = threading.Event()
        self.children = {}
        self.ready = set()
        self.kernel_state = 'unverified'
        self.run(POLICY)
        self.verify(set())
        self.kernel_state = 'verified-empty'
        self.monitor = threading.Thread(target=self.watch, daemon=True)
        self.monitor.start()

    @staticmethod
    def run(source):
        completed = subprocess.run(owned_child.command([owned_child.nft_binary(), '-f', '-'], privileged=True), input=source.encode(), capture_output=True, timeout=1)
        if completed.returncode != 0 or completed.stdout or completed.stderr:
            raise RuntimeError('Native peer rule transaction failed')

    def verify(self, ports):
        completed = subprocess.run(owned_child.command([owned_child.nft_binary(), '-j', 'list', 'table', 'inet', TABLE], privileged=True), capture_output=True, timeout=1)
        if completed.returncode != 0 or completed.stderr or len(completed.stdout) > 16384:
            raise RuntimeError('Native peer rule readback failed')
        rows = json.loads(completed.stdout)['nftables']
        require_policy(rows)
        values = [row['set'] for row in rows if 'set' in row]
        if (len(values) != 1 or values[0].get('type') != 'inet_service'
                or values[0].get('flags') != ['timeout'] or values[0].get('timeout') != 2):
            raise ValueError('Native ready-set schema changed')
        observed = set()
        for row in values[0].get('elem', []):
            value = row.get('elem') if isinstance(row, dict) else None
            if not isinstance(value, dict) or set(value) - {'val', 'timeout', 'expires'} or value.get('timeout', 2) != 2:
                raise ValueError('Native ready-set lease shape')
            if not 0 < value.get('expires', 0) <= 2:
                raise ValueError('Native ready-set lease expired')
            observed.add(value['val'])
        if observed != ports or len(values[0].get('elem', [])) != len(ports):
            raise ValueError('Native ready-set readback mismatch')

    def replace(self):
        self.kernel_state = 'unverified'
        ports = {PORTS[ship] for ship in self.ready}
        source = f'flush set inet {TABLE} ready\n'
        if ports:
            source += f'add element inet {TABLE} ready {{ ' + ', '.join(f'{port} timeout 2s' for port in sorted(ports)) + ' }\n'
        self.run(source)
        self.verify(ports)
        self.kernel_state = 'leased-ready' if ports else 'verified-empty'

    def abort(self, error, *, force_notify=False):
        notify = force_notify or not self.closed.is_set()
        self.closed.set()
        self.ready.clear()
        self.children.clear()
        self.kernel_state = 'unverified'
        try:
            # Restore the complete empty policy atomically. A cleared set alone
            # cannot protect against missing packet rules or a deleted table.
            self.run(f'destroy table inet {TABLE}\n' + POLICY)
            self.verify(set())
            self.kernel_state = 'verified-empty'
        except BaseException:
            # No closure claim when the packet policy cannot be verified.
            # The caller must immediately stop all owned native children.
            pass
        if notify:
            self.failed(error)

    def block(self, ship):
        with self.lock:
            try:
                if self.closed.is_set() or ship not in PORTS:
                    raise ValueError('Native peer barrier closed or unknown ship')
                self.ready.discard(ship)
                self.children.pop(ship, None)
                self.replace()  # Succeed/read back BEFORE the next Popen.
            except BaseException as error:
                self.abort(error)
                raise

    def release(self, ship, process):
        with self.lock:
            try:
                self.guard()
                if self.closed.is_set() or ship not in PORTS:
                    raise ValueError('Native peer barrier closed')
                proof = {'capabilities': require_confined_child(process), 'socket': require_owned_udp(process, ship)}
                self.children[ship] = process
                self.ready.add(ship)
                self.replace()
                return proof
            except BaseException as error:
                self.abort(error)
                raise

    def watch(self):
        while not self.closed.wait(.25):
            try:
                self.guard()
                with self.lock:
                    previous = self.ready
                    self.ready = {ship for ship in previous if self.children[ship].poll() is None}
                    if previous or self.ready:
                        self.replace()
                    else:
                        self.verify(set())
            except BaseException as error:
                with self.lock:
                    self.abort(error)
                return

    def close(self):
        self.closed.set()
        try:
            with self.lock:
                self.ready.clear()
                self.children.clear()
                try:
                    self.replace()
                except BaseException as error:
                    self.abort(error, force_notify=True)
                    raise
        finally:
            if self.monitor is not threading.current_thread():
                self.monitor.join(timeout=2)
