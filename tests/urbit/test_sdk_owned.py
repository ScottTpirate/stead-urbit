"""Actual Linux namespace/process controls, separate from native Hoon tests."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts/sdk_native'), str(ROOT / 'scripts/urbit')]
import owned_child
SPEC = importlib.util.spec_from_file_location('sdk_run', ROOT / 'scripts/sdk_native/run.py')
RUN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUN)

PROOF = '''import json, os
from pathlib import Path
fields=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
proof={'uid':os.getuid(),'gid':os.getgid(),'uid_map':Path('/proc/self/uid_map').read_text().split(),
       'gid_map':Path('/proc/self/gid_map').read_text().split(),
       'caps':{k:fields[k].strip() for k in ('CapInh','CapPrm','CapEff','CapBnd','CapAmb','NoNewPrivs')},
       'ns':{k:os.readlink('/proc/self/ns/'+k) for k in ('user','net','pid','mnt')}}
assert all(v=='0000000000000000' for k,v in proof['caps'].items() if k!='NoNewPrivs')
assert proof['caps']['NoNewPrivs']=='1'
'''

PARENT_LOSS = '''import ctypes, signal, time
assert ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0)==0
child_source=''' + repr(PROOF + "\nimport signal\nprint(json.dumps({'pid':os.getpid(),'proof':proof}),flush=True)\nsignal.pause()") + '''
creator_source="import sys,subprocess;sys.path.insert(0,'/helpers');import owned_child;subprocess.Popen(owned_child.command(['/usr/bin/python3','-c',"+repr(child_source)+"])).wait()"
creator=subprocess.Popen(['/usr/bin/python3','-c',creator_source],stdout=subprocess.PIPE,text=True)
loss=json.loads(creator.stdout.readline())
creator.kill()
creator.wait(timeout=2)
deadline=time.monotonic()+2
while True:
    reaped,status=os.waitpid(loss['pid'],os.WNOHANG)
    if reaped:
        assert os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL
        break
    assert time.monotonic()<deadline,'Owned evaluator outlived its creator'
    time.sleep(.01)
creator.stdout.close()
loss['reaped_after_creator_loss']=True
'''


class SDKOwnedTests(unittest.TestCase):
    def test_new_mode_cannot_bypass_configured_uid_requirement(self):
        with patch.dict(os.environ, {'STEAD_CONFIGURED': '1', 'STEAD_OWNED_EVALUATORS': '1'}), patch.object(os, 'getuid', return_value=1000):
            with self.assertRaises(ValueError):
                owned_child.fixture_command(['/usr/bin/true'])

    def test_actual_nested_flags_and_zero_capability_evaluator(self):
        with tempfile.TemporaryDirectory(prefix='sdk-namespace-control-', dir=ROOT / '.runtime') as temporary:
            root = Path(temporary)
            for name in ('runner', 'public', 'runtime', 'kernel', 'state', 'state/consumer'):
                (root / name).mkdir(mode=0o700)
            (root / 'state/consumer-context.json').write_text('{}')
            shutil.copyfile(ROOT / 'scripts/urbit/owned_child.py', root / 'runner/owned_child.py')
            inner = (PROOF + '''import owned_child, subprocess
Path('/state/mapped-owner').write_text('disposable namespace control')
evaluator=json.loads(subprocess.check_output(owned_child.fixture_command(['/usr/bin/python3','-c', ''' + repr(PROOF + '\nprint(json.dumps(proof))') + '''])))
assert evaluator['uid']==0 and evaluator['ns']==proof['ns']
print(json.dumps({'controller':proof,'evaluator':evaluator}))
''')
            (root / 'runner/namespace-probe.py').write_text(inner)
            outer = (PROOF + '''import subprocess, sys
sys.path[:0]=['/controller','/helpers']
from controller import consumer_command
import owned_child
Path('/state/mapped-owner').write_text('disposable outer namespace control')
args=consumer_command()
assert args[-1]=='/runner/consumer.py'
args[-1]='/runner/namespace-probe.py'
inner=json.loads(subprocess.check_output(args,timeout=10))
assert proof['uid']!=0 and inner['controller']['uid']==0
assert inner['controller']['uid_map']==['0','0','1']
assert inner['controller']['gid_map']==['0','0','1']
assert all(proof['ns'][k]!=inner['controller']['ns'][k] for k in proof['ns'])
evaluator=json.loads(subprocess.check_output(owned_child.fixture_command(['/usr/bin/python3','-c', ''' + repr(PROOF + '\nprint(json.dumps(proof))') + '''])))
assert evaluator['uid']==proof['uid'] and evaluator['ns']==proof['ns']
''' + PARENT_LOSS + '''
print(json.dumps({'outer':proof,'outer_evaluator':evaluator,'inner':inner,'parent_loss':loss}))
''')
            command = RUN.system_mounts()
            for name in ('runner', 'public', 'runtime', 'kernel'):
                command += ['--ro-bind', str(root / name), '/' + name]
            command += ['--ro-bind', str(ROOT / 'scripts/sdk_native'), '/controller',
                '--ro-bind', str(ROOT / 'scripts/urbit'), '/helpers',
                '--ro-bind', str(ROOT / 'specs/urbit/toolchain.lock.json'), '/toolchain.json',
                '--bind', str(root / 'state'), '/state', '--clearenv', '--setenv', 'PATH', '/usr/bin:/bin',
                '--setenv', 'STEAD_OWNED_EVALUATORS', '1', '--', '/usr/bin/python3', '-B', '-c', outer]
            run = subprocess.run(command, capture_output=True, timeout=15)
            self.assertEqual(run.returncode, 0, run.stderr.decode())
            proof = json.loads(run.stdout)
            self.assertEqual(proof['outer']['uid'], os.getuid())
            # Bubblewrap's final namespaces map through an intermediate root
            # namespace. The host inode owners verify the composed mapping.
            self.assertEqual(proof['outer']['uid_map'], [str(os.getuid()), '0', '1'])
            self.assertEqual(proof['outer']['gid_map'], [str(os.getgid()), '0', '1'])
            self.assertEqual((root / 'state/mapped-owner').stat().st_uid, os.getuid())
            self.assertEqual((root / 'state/mapped-owner').stat().st_gid, os.getgid())
            self.assertEqual((root / 'state/consumer/mapped-owner').stat().st_uid, os.getuid())
            self.assertEqual((root / 'state/consumer/mapped-owner').stat().st_gid, os.getgid())
            print(json.dumps({'classification': 'actual-linux-namespace-and-owned-evaluator-control', 'proof': proof}))


if __name__ == '__main__':
    unittest.main()
