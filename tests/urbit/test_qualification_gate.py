"""Mock proof documents test reconciliation failures, never qualify a runtime."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/urbit'))
import qualification_gate as G


def fixture(kind='native'):
    bindings={key:('a'*40 if key=='source_commit' else 'b'*64) for key in G.NATIVE_BINDINGS}
    bindings['source_files']={'fixture.hoon':'c'*64}
    identifier='no-effect-subsystem' if kind=='not_applicable' else 'fixture-claim'
    status=G.DISPOSITION[kind]
    manifest={'scope':'AUTHORED MOCK FORMAT TEST','historical_skips':[{'historical_status':'skipped'}],
              'required':[{'id':identifier,'kind':kind,'assertions':['fixture-assertion'],'scope':'bounded mock proof'}]}
    proof={'kind':kind,'status':status,'bindings':bindings,'assertions':[{'name':'fixture-assertion','status':status}],
           'classification':'real-native-fake-ships','native':[{'AUTHORED MOCK':'not an actual native command'}],
           'guard_status':'completed','reviewer':'/root/qa_review','scope':'bounded mock source disposition',
           'reviewed_source_files':{'fixture.hoon':'c'*64},
           'reason':'External-effect execution is absent; no future replay safety claimed.'}
    def build(value):
        raw=json.dumps({'proof':value}).encode()
        evidence=[{'id':identifier,'kind':kind,'status':status,'bindings':copy.deepcopy(bindings),
                   'artifact':{'path':'fixture.json','sha256':hashlib.sha256(raw).hexdigest(),'pointer':'/proof'}}]
        return evidence,lambda path:raw
    evidence,reader=build(proof)
    return manifest,bindings,proof,build,evidence,reader


class QualificationGateHostTests(unittest.TestCase):
    def test_nonempty_complete_mock_format_is_not_relabelled(self):
        manifest,bindings,proof,build,evidence,reader=fixture()
        result=G.evaluate(manifest,evidence,bindings,read_artifact=reader)
        self.assertEqual(result['status'],'passed')
        self.assertEqual(result['scope'],'AUTHORED MOCK FORMAT TEST')
        self.assertEqual(result['historical_skips'],manifest['historical_skips'])

    def test_missing_current_native_evidence_is_failed_not_green_incomplete(self):
        manifest,bindings,*_=fixture()
        result=G.evaluate(manifest,[],bindings)
        self.assertEqual(result['status'],'failed');self.assertEqual(result['counts'],{'missing':1})

    def test_wrong_source_lock_corpus_or_loaded_closure_fails(self):
        for key in G.NATIVE_BINDINGS:
            manifest,bindings,proof,build,evidence,reader=fixture()
            evidence[0]['bindings'][key]='0'*(40 if key=='source_commit' else 64)
            with self.subTest(key=key):self.assertEqual(G.evaluate(manifest,evidence,bindings,read_artifact=reader)['status'],'failed')

    def test_native_proof_cannot_be_mocked_unexecuted_guard_stopped_or_zero_assertion(self):
        changes=[('classification','host-mocked'),('native',[]),('guard_status','failed'),('assertions',[]),
                 ('status','incomplete'),('assertions',[{'name':'fixture-assertion','status':'skipped'}]),
                 ('assertions',[{'name':'different-name','status':'passed'}])]
        for key,value in changes:
            manifest,bindings,proof,build,_,_=fixture();proof[key]=value;evidence,reader=build(proof)
            with self.subTest(key=key,value=value):self.assertEqual(G.evaluate(manifest,evidence,bindings,read_artifact=reader)['status'],'failed')

    def test_digest_pointer_proof_binding_and_missing_reader_fail(self):
        for damage in ('digest','pointer','proof-binding','missing-reader'):
            manifest,bindings,proof,build,evidence,reader=fixture()
            if damage=='digest':evidence[0]['artifact']['sha256']='0'*64
            elif damage=='pointer':evidence[0]['artifact']['pointer']='/absent'
            elif damage=='proof-binding':proof['bindings']=dict(bindings,corpus_sha256='0'*64);evidence,reader=build(proof)
            else:reader=None
            with self.subTest(damage=damage):self.assertEqual(G.evaluate(manifest,evidence,bindings,read_artifact=reader)['status'],'failed')

    def test_empty_duplicate_unknown_and_optionalized_native_names_fail(self):
        manifest,bindings,proof,build,evidence,reader=fixture()
        for changed,supplied in ((dict(manifest,required=[]),evidence),(manifest,evidence+evidence),
                                 (dict(manifest,required=manifest['required']*2),evidence),
                                 (manifest,evidence+[dict(evidence[0],id='unknown')])):
            self.assertEqual(G.evaluate(changed,supplied,bindings,read_artifact=reader)['status'],'failed')
        # No optional flag can bypass a required item.
        manifest['required'][0]['optional']=True
        self.assertEqual(G.evaluate(manifest,[],bindings)['status'],'failed')

    def test_source_and_absent_effect_dispositions_stay_distinct(self):
        for kind,status in (('source_review','reviewed'),('not_applicable','not_applicable')):
            manifest,bindings,proof,build,evidence,reader=fixture(kind)
            result=G.evaluate(manifest,evidence,bindings,read_artifact=reader)
            self.assertEqual(result['items'][0]['status'],status)
            proof['reviewer']='/root';evidence,reader=build(proof)
            self.assertEqual(G.evaluate(manifest,evidence,bindings,read_artifact=reader)['status'],'failed')
        manifest,bindings,proof,build,evidence,reader=fixture('not_applicable')
        manifest['required'][0]['id']='native-migration';evidence[0]['id']='native-migration'
        self.assertEqual(G.evaluate(manifest,evidence,bindings,read_artifact=reader)['status'],'failed')

    def test_artifact_reader_rejects_outside_symlink_and_nonfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';root.mkdir();outside=Path(tmp)/'outside';outside.write_text('{}')
            (root/'escape').symlink_to(outside)
            reader=G.artifact_reader(root)
            for path in ('../outside','escape','.',str(outside)):
                with self.subTest(path=path),self.assertRaises(ValueError):reader(path)

    def test_real_manifest_retains_all25_skips_and_explicit_gate_names(self):
        manifest=json.loads((ROOT/'specs/urbit/v2/qualification-gate.json').read_bytes())
        self.assertEqual(len(manifest['historical_skips']),25)
        self.assertEqual(sum(x['check']=='one-shot-request-duct-only' for x in manifest['historical_skips']),22)
        ids={x['id'] for x in manifest['required']}
        self.assertTrue({'delivery-expired-same-path-reregistration','legacy-revocation-exhaustion-reproduced',
                         'migration-actual-v1-vase','v2-cross-container-local-id','boundary-object-bytes'}<=ids)
        result=G.evaluate(manifest,[],{})
        self.assertEqual((result['status'],result['native_passed']),('failed',0))
        self.assertEqual(result['native_required'],66)


if __name__=='__main__':
    unittest.main(verbosity=2)
