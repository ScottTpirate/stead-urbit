import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/runtime_build'))
import hosted
import inputs


class ContainerAdmission(unittest.TestCase):
    def setUp(self):
        self.mounts=[(Path('/job/inputs'),'/inputs',False),(Path('/job/state'),'/state',True)]
        self.value={'Config':{'User':'65534:65534','Env':['LANG=C.UTF-8','PATH=/usr/bin:/bin']},
            'HostConfig':{'NetworkMode':'none','ReadonlyRootfs':True,'Privileged':False,
                'CapDrop':['ALL'],'CpuPeriod':10000,'CpuQuota':20000,'Memory':4294967296,
                'MemorySwap':4294967296,'PidsLimit':256,'RestartPolicy':{'Name':'no'},'Init':True,
                'PidMode':'','IpcMode':'private','SecurityOpt':['no-new-privileges'],
                'Tmpfs':{'/tmp':'rw,nosuid,nodev,noexec,size=268435456'}},
            'Mounts':[{'Type':'bind','Destination':target,'Source':str(source),'RW':writable}
                      for source,target,writable in self.mounts]}

    def test_admitted_fixed_profile(self):
        hosted.policy(self.value,self.mounts)

    def test_rejects_each_weakened_boundary(self):
        for key,value in {'NetworkMode':'host','ReadonlyRootfs':False,'Privileged':True,
                          'CapDrop':[],'CapAdd':['SYS_ADMIN'],'CpuQuota':40000,'Memory':0,'MemorySwap':-1,'PidsLimit':0,
                          'PidMode':'host','IpcMode':'host','SecurityOpt':[],'Tmpfs':{}}.items():
            with self.subTest(key=key):
                changed=copy.deepcopy(self.value);changed['HostConfig'][key]=value
                with self.assertRaises(ValueError):hosted.policy(changed,self.mounts)

    def test_rejects_privileged_user_and_leaked_environment(self):
        for key,value in (('User','0'),('Env',['LANG=C.UTF-8','PATH=/usr/bin:/bin','TOKEN=fixture'])):
            with self.subTest(key=key):
                changed=copy.deepcopy(self.value);changed['Config'][key]=value
                with self.assertRaises(ValueError):hosted.policy(changed,self.mounts)

    def test_rejects_writable_input_or_extra_host_mount(self):
        changed=copy.deepcopy(self.value);changed['Mounts'][0]['RW']=True
        with self.assertRaises(ValueError):hosted.policy(changed,self.mounts)

    def test_rejects_undeclared_volume_and_tmpfs(self):
        for kind,target in (('volume','/extra'),('tmpfs','/extra')):
            changed=copy.deepcopy(self.value)
            changed['Mounts'].append({'Type':kind,'Source':'','Destination':target,'RW':True})
            with self.assertRaises(ValueError):hosted.policy(changed,self.mounts)
        changed=copy.deepcopy(self.value)
        changed['Mounts'].append({'Type':'tmpfs','Source':'','Destination':'/tmp','RW':True})
        hosted.policy(changed,self.mounts)
        changed=copy.deepcopy(self.value)
        changed['Mounts'].append({'Type':'bind','Destination':'/socket','Source':'/var/run/docker.sock','RW':True})
        with self.assertRaises(ValueError):hosted.policy(changed,self.mounts)

    def test_primary_refusal_survives_cleanup_failure_and_is_recorded(self):
        from unittest.mock import patch
        import json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def command(argv,**kwargs):
                if argv[1]=='create':return ('a'*64+'\n').encode()
                if argv[1]=='inspect':return b'[{"Config":{}}]'
                if argv[1]=='rm':raise RuntimeError('cleanup failed')
                raise AssertionError(argv)
            with patch.object(hosted,'OUT',root),patch.object(hosted,'run',side_effect=command), \
                 patch.object(hosted,'policy',side_effect=ValueError('primary boundary refusal')), \
                 patch.object(hosted.subprocess,'run',side_effect=RuntimeError('inspect failed')):
                with self.assertRaisesRegex(ValueError,'primary boundary refusal'):
                    hosted.container('sha256:'+'b'*64,'test-owned',['/zig/zig'],[], 'c'*40,10)
            report=json.loads((root/'test-owned.json').read_text())
            self.assertEqual(report['status'],'fail');self.assertFalse(report['cleanup'])
            self.assertEqual(len(report['cleanup_errors']),2)
            self.assertIn('primary boundary refusal',report['error'])


class SourceCustody(unittest.TestCase):
    def test_tree_records_untracked_bytes_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'source.c').write_bytes(b'fixed source')
            before=inputs.tree(root)
            (root/'untracked.h').write_bytes(b'changes compilation')
            self.assertNotEqual(before,inputs.tree(root))
            (root/'escape').symlink_to('/etc/passwd')
            with self.assertRaises(AssertionError):inputs.tree(root)

    def test_download_hash_mismatch_does_not_execute(self):
        from unittest.mock import patch
        import io
        with tempfile.TemporaryDirectory() as directory:
            row={'url':'https://example.invalid/source.tar.gz','file':'source.tar.gz','bytes':5,'sha256':'0'*64}
            with patch.object(hosted.urllib.request,'urlopen',return_value=io.BytesIO(b'wrong')):
                with self.assertRaisesRegex(ValueError,'Downloaded bytes differ'):
                    hosted.fetch(row,Path(directory))


if __name__=='__main__':unittest.main()
