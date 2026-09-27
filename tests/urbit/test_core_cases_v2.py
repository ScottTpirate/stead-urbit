"""V2 recipe/adapter regressions: host-only, canned outcomes, no fake ships."""
from __future__ import annotations

import copy
import gzip
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/urbit'))
import core_cases_v2 as E
import contracts_v2 as C

CORPUS=json.loads((ROOT/'specs/urbit/fixtures/native-cases-v2.json').read_bytes())
CASES={case['name']:case for case in CORPUS['ordered_cases']}


def subset(*names):
    return {'commands':copy.deepcopy(CORPUS['commands']),'principals':CORPUS['principals'],
            'fixture_ids':CORPUS['fixture_ids'],'ordered_cases':[copy.deepcopy(CASES[name]) for name in names]}


def result(value):
    return {'raw':json.dumps(value,sort_keys=True,separators=(',',':')),'json':copy.deepcopy(value),
            'native':{'classification':'host-mocked-executor-test'}}


def state(digit='0',**counts):
    return {'state_jam_sha256':digit*64,'now_ms':'1900000000000',
            'counts':{'journal':0,'receipts':0,'objects':0,'object_bytes':0,'projects':0,'works':0,'documents':0,'grants':0,**counts},
            'revisions':{}}


def creation():
    cmd=CORPUS['commands']['project_create'];project=cmd['project_id']
    record={'protocol':'stead.journal/1','sequence':'1','previous_digest':'0'*64,
            'canonical_command':E.canonical(cmd).decode(),'old_revision':'0','new_revision':'1',
            'principal_id':CORPUS['principals']['zod'],'binding_id':E.BINDINGS['zod'],
            'policy_revision':'0','authority_epoch':'1','accepted_at_ms':'1900000000000','git_commit_oid':'',
            'authentication':'fake-native/1','authentication_strength':'synthetic-native-sender'}
    journal=json.dumps(record,sort_keys=True,separators=(',',':'))
    receipt={'protocol':'stead.receipt/2','status':'accepted','request_id':cmd['request_id'],
             'canonical_sha256':hashlib.sha256(b'stead.command/2\0'+E.canonical(cmd)).hexdigest(),
             'project_id':project,'resource_id':cmd['resource_id'],'resource_kind':'project','container_id':'',
             'resource_revision':'1','authority_epoch':'1','principal_id':CORPUS['principals']['zod'],
             'binding_id':E.BINDINGS['zod'],'authentication':'fake-native/1',
             'authentication_strength':'synthetic-native-sender','accepted_at_ms':'1900000000000','git_commit_oid':''}
    after=state('1',journal=1,receipts=1,projects=1,grants=1)
    after.update(last_journal_record=journal,last_journal_digest=hashlib.sha256(b'stead.journal/1\0'+journal.encode()).hexdigest(),
                 revisions={'policy/'+project:'1','project/'+project:'1'})
    return result(receipt),after


class Adapter:
    def __init__(self,*steps):self.steps=list(steps);self.state=state();self.calls=[]
    def snapshot(self):return copy.deepcopy(self.state)
    def call(self,ship,mode,route='/',raw=b''):
        self.calls.append((ship,mode,route,raw));value,after=self.steps.pop(0)
        if isinstance(value,Exception):raise value
        if after is not None:self.state=copy.deepcopy(after)
        return copy.deepcopy(value)


def run(corpus,adapter,**kwargs):
    return E.run(corpus,adapter.call,adapter.snapshot,classification='host-mocked-v2-executor-only',**kwargs)


class CoreCasesV2HostTests(unittest.TestCase):
    def test_frozen_v1_bytes_and_all_original_case_names_remain(self):
        C.verify_freeze()
        derivation=CORPUS['derivation'];raw=(ROOT/derivation['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),derivation['sha256'])
        old=json.loads(raw)
        for lane in ('ordered_cases','real_expiry_continuation','source_review_continuation','separate_project_journal_lane'):
            a=old[lane] if isinstance(old[lane],list) else old[lane]['cases']
            b=CORPUS[lane] if isinstance(CORPUS[lane],list) else CORPUS[lane]['cases']
            self.assertEqual([x['name'] for x in a],[x['name'] for x in b])
        self.assertEqual(sum(len(CORPUS[k]['cases']) for k in ('real_expiry_continuation','source_review_continuation','separate_project_journal_lane'))+len(CORPUS['ordered_cases']),129)

    def test_all80_commands_and49_codec_vectors_match_v2_host_contract(self):
        self.assertEqual(len(CORPUS['commands']),80)
        for name,command in CORPUS['commands'].items():
            with self.subTest(command=name):self.assertEqual(C.parse(E.canonical(command)),command)
        vectors=json.loads((ROOT/CORPUS['codec_lane']['frozen_positive_vectors']).read_bytes())
        self.assertEqual(len(vectors),6)
        for vector in vectors:
            self.assertEqual(C.canonical(vector['request']).decode(),vector['canonical_utf8'])
            self.assertEqual(C.digest(vector['request']),vector['sha256'])
        new=CORPUS['codec_lane']['new_vectors'];self.assertEqual(len(new),43)
        for vector in new:
            if 'raw_hex' in vector:
                raw=bytes.fromhex(vector['raw_hex'])
            elif 'raw_utf8' in vector:
                raw=vector['raw_utf8'].encode()
            elif 'raw_recipe' in vector:
                recipe=vector['raw_recipe'];raw=(recipe['prefix']+recipe['append_utf8']*recipe['repeat']).encode()
            else:
                recipe=vector['command_recipe'];command=copy.deepcopy(CORPUS['commands'][recipe['base_command_ref']])
                command['request_id']=recipe['replace']['/request_id']
                repeat=recipe['repeat_string']['/payload/markdown'];command['payload']['markdown']=repeat['value']*repeat['repeat']
                raw=E.canonical(command)
            with self.subTest(vector=vector['name']):
                if vector['expected']['codec']=='reject':
                    with self.assertRaises(ValueError):C.parse(raw)
                else:
                    expected=vector['expected'];decoded=C.parse(raw)
                    self.assertEqual(decoded,expected['decoded_command'])
                    self.assertEqual(C.canonical(decoded).decode(),expected['canonical_utf8'])
                    self.assertEqual(C.digest(decoded),expected['sha256'])

    def test_scoped_collision_schedule_has9_explicit_acceptances_and_new_parent(self):
        collisions=CORPUS['ordered_cases'][54:63]
        self.assertEqual([x['expected']['journal_sequence'] for x in collisions],list(map(str,range(20,29))))
        self.assertTrue(all(x['expected']['result']=='accepted' and x.get('amendment') for x in collisions))
        a=CASES['edit-document-a-using-its-own-revision']['expected']
        self.assertEqual((a['journal_sequence'],a['container_commit_parent_from']),('29','document-resource-collides-with-work'))
        self.assertIn('document_resource_collides_with_work',a['reachable_file_refs'])
        self.assertEqual(CASES['administrator-cannot-move-another-owner-document']['expected']['error'],'revision_conflict')
        self.assertEqual(len(CORPUS['scoped_privacy_lane']['cases']),19)

    def test_revision_keys_keep_same_local_uuid_in_typed_scopes_distinct(self):
        project=copy.deepcopy(CORPUS['commands']['project_create'])
        work=copy.deepcopy(CORPUS['commands']['work_resource_collides_with_project'])
        policy=copy.deepcopy(CORPUS['commands']['grant_bus_contributor'])
        doc=copy.deepcopy(CORPUS['commands']['document_a_1'])
        other=copy.deepcopy(doc);other['payload']['container_id']=CORPUS['fixture_ids']['zod_container']
        keys=[E.revision_key(x) for x in (project,work,policy,doc,other)]
        self.assertEqual(len(set(keys)),5)
        self.assertTrue(keys[0].startswith('project/'));self.assertTrue(keys[1].startswith('work/'))

    def test_public_receipt_has_no_private_journal_fields_but_owner_chain_verified(self):
        receipt,after=creation();adapter=Adapter((receipt,after),(receipt,None))
        report=run(subset('create-project','duplicate-project-create'),adapter)
        self.assertEqual(report['status'],'passed',report['cases'])
        self.assertEqual(report['classification'],'host-mocked-v2-executor-only')
        self.assertTrue(any(x['name']=='private-owner-journal-hash' for x in report['checks']))
        self.assertTrue(adapter.calls[0][2].startswith('/v2/result/~zod/'))

    def test_public_journal_or_policy_metadata_wrong_kind_or_container_fails(self):
        for key,value in (('journal_sequence','1'),('journal_digest','a'*64),('policy_revision','0'),
                          ('resource_kind','document'),('container_id',CORPUS['fixture_ids']['bus_container'])):
            receipt,after=creation();receipt=result(dict(receipt['json'],**{key:value}))
            with self.subTest(key=key):self.assertEqual(run(subset('create-project'),Adapter((receipt,after)))['status'],'failed')

    def test_missing_actual_read_delivery_fails_current_gate_and_preserves_skip(self):
        denied=result(E.DENIAL)
        report=run(subset('empty-project-known-unknown'),Adapter((denied,None),(denied,None)))
        self.assertEqual(report['status'],'failed');self.assertEqual(report['functional_status'],'incomplete')
        self.assertEqual(report['check_counts']['skipped'],2)
        self.assertTrue(all(x['name']=='one-shot-request-duct-only' for x in report['checks'] if x['status']=='skipped'))

    def test_host_delivery_constants_cannot_green_native_read(self):
        denied=result(E.DENIAL)
        denied['native']['delivery']={'facts':1,'kicks':1,'other_subscriber_content_facts':0,'ongoing_subscription':False}
        report=run(subset('empty-project-known-unknown'),Adapter((denied,None)))
        self.assertEqual(report['status'],'failed')
        self.assertIn('ObservationError',report['cases'][0]['error'])

    def test_no_result_changed_denial_or_changed_duplicate_never_pass(self):
        for response,after in (({'raw':None,'json':None,'native':{'ack':True}},None),
                               (result(E.DENIAL),state('1'))):
            report=run(subset('nonadministrator-cannot-create'),Adapter((response,after)))
            self.assertEqual(report['status'],'failed')
        receipt,after=creation();changed=result(dict(receipt['json'],accepted_at_ms='1900000000001'))
        self.assertEqual(run(subset('create-project','duplicate-project-create'),Adapter((receipt,after),(changed,None)))['status'],'failed')

    def test_empty_or_unrun_required_continuation_fails(self):
        self.assertEqual(run(subset(),Adapter())['status'],'failed')
        corpus=subset('nonadministrator-cannot-create');corpus['real_expiry_continuation']=CORPUS['real_expiry_continuation']
        report=run(corpus,Adapter((result(E.DENIAL),None)))
        self.assertEqual(report['status'],'failed');self.assertEqual(report['case_counts']['not_run'],10)

    def test_historical_skip_mapping_matches_retained_report_exactly(self):
        manifest=json.loads((ROOT/'specs/urbit/v2/qualification-gate.json').read_bytes())
        source=manifest['historical_report'];compressed=(ROOT/source['path']).read_bytes()
        self.assertEqual(hashlib.sha256(compressed).hexdigest(),source['sha256'])
        raw=gzip.decompress(compressed);self.assertEqual(hashlib.sha256(raw).hexdigest(),source['uncompressed_sha256'])
        report=json.loads(raw)
        for entry in CORPUS['historical_skips']:
            item=report['qa']['checks'][int(entry['report_check_pointer'].rsplit('/',1)[1])]
            self.assertEqual((item['case'],item['name'],item['status']),(entry['case'],entry['check'],'skipped'))


if __name__=='__main__':
    unittest.main(verbosity=2)
