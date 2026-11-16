"""Six inert terminal-monitor regressions; no processes, procfs or evaluator runs.

The existing source-bound collector fixtures provide constructed reports only.
These tests do not reproduce either historical worker's unavailable raw output.
"""
from contextlib import ExitStack, contextmanager
import importlib.util
from pathlib import Path
import types
import unittest
from unittest.mock import Mock, patch

SOURCE = Path(__file__).with_name('test_pure_eval_collection.py')
spec = importlib.util.spec_from_file_location('terminal_collection_fixture', SOURCE)
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)
B, C = F.B, F.C


class ProcPath:
    def __init__(self, value, reader): self.value, self.reader = value, reader
    def __truediv__(self, part): return ProcPath(self.value + '/' + str(part), self.reader)
    def __str__(self): return self.value
    def read_text(self): return self.reader(self.value.rsplit('/', 1)[-1])
    def stat(self): return self.reader('root')


class PureEvalCurrentTests(unittest.TestCase):
    @contextmanager
    def proc(self, *, dead=False, missing=None, dies=True, error=FileNotFoundError, mismatch=None):
        anchor = {'pid': 90, 'pidfd': 777, 'identity': (90, 900), 'root_identity': (3, 4),
                  'namespaces': {name: name + ':[2]' for name in B.NAMESPACES}}
        value = {'unit': 'owned.service', 'host_uid': 1001, 'host_gid': 1002}
        state = {'dead': dead, 'reads': [], 'polls': 0}
        fields = {'Uid': '1001 1001 1001 1001', 'Gid': '1002 1002 1002 1002', 'NoNewPrivs': '1',
                  **{name: '0000000000000000' for name in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')}}
        def read(key):
            state['reads'].append(key)
            if key == missing:
                state['dead'] = dies
                raise error('inert proc observation')
            if key == mismatch or (key == 'status' and mismatch in fields):
                # A mismatch already obtained must remain fatal even when the
                # same worker exits before a possible later observation.
                state['dead'] = True
            if key == 'identity': return (90, 999) if mismatch == key else anchor['identity']
            if key == 'cgroup': return '0::/other.service\n' if mismatch == key else '0::/system.slice/owned.service\n'
            if key.startswith('ns:'):
                return 'foreign:[9]' if mismatch == key else anchor['namespaces'][key[3:]]
            if key == 'root': return types.SimpleNamespace(st_dev=3, st_ino=5 if mismatch == key else 4)
            if key == 'status':
                rows = dict(fields)
                if mismatch in rows: rows[mismatch] = '0' if mismatch == 'NoNewPrivs' else '999'
                return '\n'.join(name + ':\t' + text for name, text in rows.items())
            raise AssertionError(key)
        def poll(readable, writable, exceptional, timeout):
            self.assertEqual((readable, writable, exceptional, timeout), ([777], [], [], 0))
            state['polls'] += 1
            return ([777] if state['dead'] else [], [], [])
        heartbeat, group = Mock(), Mock()
        with ExitStack() as stack:
            for target, name, replacement in (
                    (B, 'group', group), (B.select, 'select', Mock(side_effect=poll)),
                    (B, 'proc_identity', lambda pid: read('identity')),
                    (B, 'Path', lambda *parts: ProcPath('/'.join(map(str, parts)), read)),
                    (B.os, 'readlink', lambda path: read('ns:' + str(path).rsplit('/', 1)[-1]))):
                stack.enter_context(patch.object(target, name, replacement))
            yield anchor, value, heartbeat, group, state

    def collect_dead(self, *, missing_eof=False, duplicate=False, cleanup_ok=True,
                     omit_final=False, wrong_exit=False):
        owner, ready, final, raw = F.envelope(True)
        events = []
        stdin, stdout, stderr = (F.Stream(fd, events) for fd in (700, 701, 702))
        code = 0 if wrong_exit else 1
        process = types.SimpleNamespace(stdin=stdin, stdout=stdout, stderr=stderr, returncode=code,
            poll=lambda: code if stdout.closed and stderr.closed else None, wait=Mock(return_value=code))
        payload = C.canonical(ready) + b'\n'
        if not omit_final: payload += C.canonical(final) + b'\n'
        if duplicate: payload += C.canonical(final) + b'\n'
        chunks = {701: [payload, b''], 702: [b'']}
        def read(fd, _):
            if missing_eof and fd == 701 and len(chunks[701]) == 1:
                raise OSError('inert missing EOF')
            return chunks[fd].pop(0)
        def cleanup(*_): events.append(('cleanup',)); return cleanup_ok
        def retained(*_):
            self.assertTrue(stdout.closed and stderr.closed)
            self.assertIn(('cleanup',), events)
            events.append(('artifact',))
            return raw
        with self.proc() as (anchor, value, heartbeat, _, state), ExitStack() as stack:
            # Deterministically reproduce the terminal transition between the
            # former external poll and the monitor's actual retained-pidfd poll.
            self.assertEqual(B.select.select([777], [], [], 0)[0], [])
            state['dead'] = True
            for target, name, replacement in (
                    (C.selectors, 'DefaultSelector', F.Selector), (C.os, 'set_blocking', Mock()),
                    (C.os, 'read', read), (C, 'service_current', Mock()), (C, 'cleanup', cleanup),
                    (B, 'pin_ready', Mock(return_value=anchor)),
                    (B, 'loopback_observation', Mock(return_value={'fixed': True})),
                    (B, 'current', Mock()), (B, 'read_output', Mock(side_effect=retained)),
                    (B, 'close_anchor', Mock(side_effect=lambda _: events.append(('anchor-close',))))):
                stack.enter_context(patch.object(target, name, replacement))
            result, artifact = C.run(process, Path('/inert'), value, owner, heartbeat, F.CODEC,
                                     F.selected(), F.HASHES)
            if not duplicate: self.assertGreaterEqual(state['polls'], 2)
        return result, artifact, events, process

    def test_terminal_double_poll_drains_failed_report_only_after_reap_and_eof(self):
        result, artifact, events, process = self.collect_dead()
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['error_class'], 'none')
        self.assertEqual(artifact, C.canonical(F.report(True)))
        self.assertTrue(result['parent_admitted'] and result['child_streams_eof'] and result['owned_children_empty'])
        self.assertEqual(result['worker_exit_code'], 1)
        self.assertEqual([event for event in events if event[0] == 'go'], [('go', b'go\n')])
        self.assertLess(events.index(('cleanup',)), events.index(('artifact',)))
        self.assertLess(events.index(('artifact',)), events.index(('anchor-close',)))
        process.wait.assert_called_once_with(timeout=1)

    def test_exit_between_each_proc_read_is_only_an_original_pidfd_exit_observation(self):
        with self.proc() as (anchor, value, heartbeat, group, state):
            self.assertIs(B.monitor_current(anchor, value, heartbeat), True)
            self.assertEqual(state['reads'], ['identity', 'cgroup', 'ns:user', 'ns:mnt', 'ns:pid', 'ns:net', 'root', 'status'])
        for lookup in ('identity', 'cgroup', 'ns:user', 'ns:mnt', 'ns:pid', 'ns:net', 'root', 'status'):
            for error in (FileNotFoundError, ProcessLookupError):
                with self.subTest(lookup=lookup, error=error.__name__), self.proc(missing=lookup, error=error) as (anchor, value, heartbeat, group, state):
                    self.assertIs(B.monitor_current(anchor, value, heartbeat), False)
                    heartbeat.assert_called_once_with(); group.assert_called_once_with(value)
                    self.assertEqual(state['polls'], 2)
                    self.assertEqual(state['reads'][-1], lookup)

    def test_live_missing_permission_and_arbitrary_errors_remain_refusals(self):
        for error, dies in ((FileNotFoundError, False), (ProcessLookupError, False),
                            (PermissionError, True), (OSError, True), (ValueError, True)):
            with self.subTest(error=error.__name__), self.proc(missing='ns:mnt', error=error, dies=dies) as (anchor, value, heartbeat, group, state):
                with self.assertRaises(error): B.monitor_current(anchor, value, heartbeat)
        with self.proc(dead=True) as (anchor, value, heartbeat, group, state):
            # Ready/admission callers retain the original strict current API.
            with self.assertRaises(ValueError): B.current(anchor, value, heartbeat)

    def test_obtained_pid_root_namespace_and_credential_mismatches_cannot_be_hidden_by_later_exit(self):
        fields = ('identity', 'cgroup', 'ns:user', 'ns:mnt', 'ns:pid', 'ns:net', 'root',
                  'Uid', 'Gid', 'NoNewPrivs', 'CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb')
        for name in fields:
            with self.subTest(field=name), self.proc(mismatch=name) as (anchor, value, heartbeat, group, state):
                with self.assertRaises(ValueError): B.monitor_current(anchor, value, heartbeat)
                self.assertTrue(state['dead'])
                self.assertEqual(state['polls'], 1)
                self.assertEqual(state['reads'][-1], name if name in fields[:7] else 'status')

    def test_lease_and_group_failures_are_fatal_even_when_owned_pidfd_is_signaled(self):
        for failure in ('heartbeat', 'group'):
            with self.subTest(failure=failure), self.proc(dead=True) as (anchor, value, heartbeat, group, state):
                (heartbeat if failure == 'heartbeat' else group).side_effect = ValueError('inert current guard')
                with self.assertRaises(ValueError): B.monitor_current(anchor, value, heartbeat)
                self.assertEqual(state['polls'], 0)
                self.assertEqual(state['reads'], [])

    def test_exit_does_not_bypass_final_eof_exit_code_or_complete_cleanup(self):
        for kwargs in ({'missing_eof': True}, {'duplicate': True}, {'cleanup_ok': False},
                       {'omit_final': True}, {'wrong_exit': True}):
            with self.subTest(kwargs=kwargs):
                result, artifact, events, _ = self.collect_dead(**kwargs)
                self.assertEqual(result['status'], 'fail')
                self.assertIsNone(artifact)
                self.assertNotIn(('artifact',), events)
                self.assertIn(('cleanup',), events)
                self.assertIn(('anchor-close',), events)


if __name__ == '__main__':
    unittest.main()
