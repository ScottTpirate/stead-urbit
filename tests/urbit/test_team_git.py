"""Real stock Git against synthetic observed bytes; not native Hoon evidence."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import socket
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/urbit'))
import team_git as subject
import digests


def uid(n):
    return '019939ba-4000-7000-8000-' + f'{n:012x}'


class Observed:
    def __init__(self):
        self.objects = {}

    def add(self, kind, body):
        oid = hashlib.sha1(f'{kind} {len(body)}\0'.encode() + body).hexdigest()
        self.objects[oid] = (kind, body)
        return oid

    def snapshot(self, files, parent=None):
        tree = self.add('tree', b''.join(b'100644 ' + name.encode() + b'\0' + bytes.fromhex(self.add('blob', body))
            for name, body in sorted(files.items())))
        body = 'tree ' + tree + '\n' + ('parent ' + parent + '\n' if parent else '')
        body += 'author Exact Name <exact@example.test> 1000000000 +0000\ncommitter Exact Name <exact@example.test> 1000000000 +0000\n\nObserved synthetic fixture\n'
        return self.add('commit', body.encode())

    def reader(self, container, head):
        def read(oid):
            if oid is None:
                return {'protocol':'stead.fixture-git/3','project_id':uid(1),'container_id':container,
                    'snapshot_commit_oid':head,'objects':{key:kind for key,(kind,body) in self.objects.items()}}
            kind, body = self.objects[oid]
            return {'protocol':'stead.fixture-git-object/3','snapshot_commit_oid':head,'oid':oid,
                    'kind':kind,'byte_length':str(len(body)),'hex':body.hex()}
        return read


class TeamGitTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.runtime').mkdir(mode=0o700, exist_ok=True)
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / '.runtime')
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def materialize(self, graph, name, container, head):
        return subject.materialize(graph.reader(container,head), self.root/name, uid(1), container, head)

    def test_real_git_exact_markdown_ancestry_identity_and_private_exclusion(self):
        private = Observed()
        files = {uid(3)+'.md': b'# Private draft\n'}
        first = private.snapshot(files)
        files[uid(4)+'.md'] = b'# UNSELECTED-PRIVATE-CANARY\n'
        second = private.snapshot(files, first)
        files[uid(3)+'.md'] = b'# Edited private draft\n'
        third = private.snapshot(files, second)
        public = Observed()
        selected = b'# Selected canonical page\nTokyo \xe6\x9d\xb1\xe4\xba\xac\n'
        published_head = public.snapshot({uid(6)+'.md': selected})
        publication = self.materialize(public,'publication',uid(5),published_head)
        edited_body = selected + b'Edited shared explanation\n'
        edited_head = public.snapshot({uid(6)+'.md':edited_body},published_head)
        edited = self.materialize(public,'edited',uid(5),edited_head)
        source = self.materialize(private,'private',uid(2),third)
        fixture = {'format':'stead.browser-git-fixture/1','execution_id':'a'*32,'project_id':uid(1),
            'source':{'container_id':uid(2),'commits':[third,second,first],
                'files':{name:body.decode() for name,body in files.items()}},
            'destination':{'container_id':uid(5),'document_id':uid(6),'published_head':published_head,
                'edited_head':edited_head,'published_markdown':selected.decode(),'edited_markdown':edited_body.decode()}}
        subject.validate_fixture(fixture,'a'*32)
        self.assertTrue(all(subject.verify_publication(source,publication,edited,fixture).values()))
        self.assertIn(['fsck','--full','--strict'],[row['arguments'] for row in edited['commands']])
        self.assertEqual(edited['objects'][edited_head]['body'], public.objects[edited_head][1])
        for change in ('blob','canary','ancestry'):
            wrong = copy.deepcopy(edited)
            if change == 'blob':
                oid, body = next((key,row) for key,row in source['objects'].items() if row['kind']=='blob')
                wrong['objects'][oid] = body
            elif change == 'canary':
                wrong['objects'][edited_head]['body'] += b'UNSELECTED-PRIVATE-CANARY'
            else:
                wrong['commits'] = [edited_head+' '+third, third]
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.verify_publication(source,publication,wrong,fixture)

    def test_terminal_zero_in_tree_oid_is_preserved_through_real_git(self):
        for number in range(10000):
            body = f'canonical body {number}\n'.encode()
            if hashlib.sha1(f'blob {len(body)}\0'.encode()+body).digest()[-1] == 0:
                break
        else:
            self.fail('Bounded synthetic terminal-zero fixture absent')
        graph = Observed(); head = graph.snapshot({uid(3)+'.md':body})
        tree = next(body for kind,body in graph.objects.values() if kind=='tree')
        self.assertTrue(tree.endswith(b'\0'))
        result = self.materialize(graph,'zero',uid(2),head)
        self.assertEqual(result['files'], {uid(3)+'.md':body})
        self.assertIn(tree,[row['body'] for row in result['objects'].values()])

    def test_corrupt_unreachable_and_wrong_scope_observations_fail(self):
        for change in ('digest','unreachable','scope','length'):
            graph = Observed(); head = graph.snapshot({uid(3)+'.md':b'body\n'})
            if change == 'unreachable': graph.add('blob',b'unreachable')
            reader = graph.reader(uid(2),head)
            def corrupted(oid):
                value = reader(oid)
                if change == 'scope' and oid is None: value['container_id'] = uid(8)
                if oid == head and change == 'digest': value['hex'] = '00' + value['hex'][2:]
                if oid == head and change == 'length': value['byte_length'] = str(int(value['byte_length'])-1)
                return value
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.materialize(corrupted,self.root/change,uid(1),uid(2),head)

    def test_observation_requires_one_bounded_atom_and_unique_json(self):
        def atom(raw): return '0x'+format(int.from_bytes(raw,'little'),'x')
        expected = {'protocol':'synthetic'}
        self.assertEqual(subject.observe(lambda *_:atom(json.dumps(expected).encode()),uid(1),uid(2),'a'*40),expected)
        for bad in ('%generator-build-fail','0x1 0x2',atom(b'{"a":1,"a":2}')):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                subject.observe(lambda *_:bad,uid(1),uid(2),'a'*40)

    def test_early_probe_binds_manifest_and_commit_to_accepted_receipt(self):
        graph = Observed()
        head = graph.snapshot({uid(3)+'.md': b'# Native fixture\n'})
        read = graph.reader(uid(2), head)
        replies = [subject.core_conn.atom(json.dumps(read(oid)).encode()) for oid in (None, head)]
        dojo = Mock(side_effect=replies)
        result = subject.probe(dojo, uid(1), uid(2), head)
        self.assertEqual(result, {'project_id': uid(1), 'container_id': uid(2), 'head': head,
            'declared_objects': 3, 'commit_bytes': len(graph.objects[head][1]), 'commit_sha1': head})
        self.assertEqual(dojo.call_count, 2)
        self.assertIn('%manifest', dojo.call_args_list[0].args[1])
        self.assertIn('%object', dojo.call_args_list[1].args[1])

    def test_early_probe_rejects_wrong_scope_bounds_kind_and_commit_bytes(self):
        graph = Observed()
        head = graph.snapshot({uid(3)+'.md': b'# Native fixture\n'})
        read = graph.reader(uid(2), head)
        for change in ('project', 'container', 'head', 'manifest-kind', 'manifest-bound',
                       'object-head', 'object-kind', 'zero-length', 'length', 'digest'):
            manifest, value = read(None), read(head)
            if change == 'project': manifest['project_id'] = uid(8)
            elif change == 'container': manifest['container_id'] = uid(8)
            elif change == 'head': manifest['snapshot_commit_oid'] = '0'*40
            elif change == 'manifest-kind': manifest['objects'][head] = 'blob'
            elif change == 'manifest-bound': manifest['objects'].update({f'{n:040x}':'blob' for n in range(513)})
            elif change == 'object-head': value['oid'] = '0'*40
            elif change == 'object-kind': value['kind'] = 'blob'
            elif change == 'zero-length': value.update(byte_length='0', hex='')
            elif change == 'length': value['byte_length'] = str(int(value['byte_length'])+1)
            elif change == 'digest': value['hex'] = '00' + value['hex'][2:]
            replies = [subject.core_conn.atom(json.dumps(item).encode()) for item in (manifest, value)]
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.probe(Mock(side_effect=replies), uid(1), uid(2), head)

    def test_observation_emits_typed_hoon_literals_without_changing_git_ids(self):
        # The actual first browser read failed at digit five of an ungrouped
        # head literal. Exercise that shape and both leading/trailing zeroes.
        head = '0123456789abcdef0123456789abcdef01234560'
        oid = 'fedcba9876543210fedcba9876543210fedcba00'
        expected = {'protocol': 'synthetic'}
        reply = '0x' + format(int.from_bytes(json.dumps(expected).encode(), 'little'), 'x')
        dojo = Mock(return_value=reply)
        self.assertEqual(subject.observe(dojo, uid(1), uid(2), head, oid), expected)
        dojo.assert_called_once_with('zod',
            f"+stead-team-git-export [%object '{uid(1)}' '{uid(2)}' "
            "0x123.4567.89ab.cdef.0123.4567.89ab.cdef.0123.4560 "
            "0xfedc.ba98.7654.3210.fedc.ba98.7654.3210.fedc.ba00]")
        dojo.reset_mock()
        subject.observe(dojo, uid(1), uid(2), '0' * 39 + '1')
        dojo.assert_called_once_with('zod',
            f"+stead-team-git-export [%manifest '{uid(1)}' '{uid(2)}' 0x1 0x0]")

    def test_private_fixture_binds_exact_single_owned_regular_file(self):
        path=self.root/'input.json';raw=b'{"fixture":"synthetic"}'
        path.write_bytes(raw);path.chmod(0o600)
        digest=hashlib.sha256(raw).hexdigest()
        self.assertEqual(subject.private_fixture(path,digest),{'fixture':'synthetic'})
        with self.assertRaises(ValueError): subject.private_fixture(path,'0'*64)
        path.chmod(0o644)
        with self.assertRaises(ValueError): subject.private_fixture(path,digest)
        path.chmod(0o600); alias=self.root/'alias';alias.symlink_to(path)
        with self.assertRaises(OSError): subject.private_fixture(alias,digest)
        os.link(path,self.root/'hardlink')
        with self.assertRaises(ValueError): subject.private_fixture(path,digest)


class TeamGitSupervisorTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.runtime').mkdir(mode=0o700, exist_ok=True)
        self.folder = tempfile.TemporaryDirectory(dir=ROOT / '.runtime')
        self.addCleanup(self.folder.cleanup)
        self.state = Path(self.folder.name); (self.state/'logs').mkdir()
        spec = importlib.util.spec_from_file_location('git_test_supervisor', ROOT/'scripts/urbit/supervisor.py')
        self.owner = importlib.util.module_from_spec(spec)
        original = Path.read_text
        with patch.object(Path,'read_text',lambda path,*a,**kw: '{}' if path==Path('/toolchain.json') else original(path,*a,**kw)), \
                patch.object(digests,'source_sha',return_value='host-test'):
            spec.loader.exec_module(self.owner)
        self.owner.STATE=self.state; self.owner.TEAM=object()
        self.owner.PROGRESS.update(ready=True,stage='ready',team_evidence={'file':'team-check-synthetic.json','sha256':'a'*64})
        self.owner.execution_check=Mock(return_value={'run_id':'a'*32})
        self.owner.EXECUTION_PROVIDER=SimpleNamespace(summary=lambda lease:dict(lease))
        self.owner.all_stop=Mock()
        self.name='team-git-20260928T120000Z.json'
        def observed(host,name,digest):
            self.owner.execution_policy.write_json(self.state/'logs'/self.name,{'status':'pass','classification':'mocked-native'})
            return {'status':'pass','evidence_file':'.piers/fakes/logs/'+self.name,'fixture_sha256':digest}
        self.runner=patch.object(self.owner.team_git,'run',side_effect=observed)
        self.runner.start();self.addCleanup(self.runner.stop)

    def call(self):
        server,client=socket.socketpair()
        with client:
            client.sendall(json.dumps({'op':'team-git-check','fixture':'browser-git-20260928T120000Z.json','sha256':'b'*64}).encode()+b'\n')
            self.owner.handle(server)
            return json.loads(client.recv(65536))

    def test_actual_rpc_persists_final_guard_before_hashing_and_keeps_native_binding(self):
        response=self.call();self.assertTrue(response['ok'])
        result=response['result'];path=self.state/'logs'/self.name
        self.assertEqual(result['sha256'],digests.sha(path))
        self.assertEqual(json.loads(path.read_text())['execution_guard'],{'run_id':'a'*32})
        self.assertEqual(result['status'],'pass');self.assertTrue(self.owner.PROGRESS['ready'])
        self.owner.all_stop.assert_not_called()

    def test_guard_failure_persists_failure_and_stops_fixture(self):
        self.owner.execution_check.side_effect=[{'run_id':'a'*32},ValueError('synthetic guardian stop')]
        result=self.call()['result'];path=self.state/'logs'/self.name
        self.assertEqual(result['status'],'fail');self.assertEqual(json.loads(path.read_text())['status'],'fail')
        self.assertEqual(result['sha256'],digests.sha(path));self.assertFalse(self.owner.PROGRESS['ready'])
        self.owner.all_stop.assert_called_once()

    def test_eager_source_identity_changes_when_only_git_verifier_changes(self):
        with patch.object(digests,'sha',return_value='a'*64):
            original=digests.source_sha(ROOT/'scripts/urbit')
        with patch.object(digests,'sha',side_effect=lambda path:'b'*64 if path.name=='team_git.py' else 'a'*64):
            self.assertNotEqual(original,digests.source_sha(ROOT/'scripts/urbit'))
