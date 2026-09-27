from pathlib import Path
import datetime, hashlib, json, os, re, subprocess, time
root = Path.cwd()
head = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
assert head == 'fcac1c081c0dd021eebe8b3cabe754a906ebe8c4'
assert not subprocess.check_output(['git','status','--porcelain'])
base = Path('.runtime/phase02-sdk-20260926/source-fcac1c0')
base.mkdir(exist_ok=False)
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value): (base/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
def inputs():
    names = subprocess.check_output(['git','ls-files','-z','Makefile','scripts','native','specs','tests','.agents/skills','sdk','LICENSE','THIRD_PARTY_NOTICES.md','README.md','docs/urbit/DEV_FLOW.md','docs/urbit/ROADMAP.md']).decode().split('\0')
    return {n: {'bytes': (root/n).stat().st_size, 'sha256': digest(root/n)} for n in names if n}
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
before=inputs()
cgroup=Path('/proc/self/cgroup').read_text().strip().split('::',1)[1]
cpu_base=Path('/sys/fs/cgroup')/cgroup.lstrip('/')
limits={n:((cpu_base/n).read_text().strip() if (cpu_base/n).exists() else None) for n in ['cpu.max','cpuset.cpus.effective']}
started=now(); tick=time.monotonic()
with (base/'host.log').open('wb') as out:
    run=subprocess.run(['make','check'],stdout=out,stderr=subprocess.STDOUT)
finished=now(); elapsed=time.monotonic()-tick
after=inputs(); after_head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
log=(base/'host.log').read_text()
counts=re.findall(r'Ran ([0-9]+) tests in ([0-9.]+)s',log)
native_paths=['scripts/urbit','native','specs/urbit','tests/urbit/native_gall_schedule','tests/urbit/skill_evaluation']
native_same=subprocess.run(['git','diff','--quiet','dd0e8c0ce8d1d00f15de6b07e2e26d368c5c3774',head,'--',*native_paths]).returncode==0
report={'protocol':'stead.sdk-host-capture/1','source_commit':head,'source_after':after_head,'command':['make','check'],'classification':'host-static-and-mocked-suite','native_execution':False,'started_at':started,'finished_at':finished,'elapsed_seconds':elapsed,'exit_code':run.returncode,'unittest_summaries':[{'tests':int(n),'seconds':float(s)} for n,s in counts],'inputs_before':before,'inputs_after':after,'inputs_unchanged':before==after,'head_unchanged':head==after_head,'native_mounts_unchanged_from_dd0e8c0':native_same,'cpu_affinity':sorted(os.sched_getaffinity(0)),'cgroup_limits':limits,'log':{'path':'host.log','bytes':(base/'host.log').stat().st_size,'sha256':digest(base/'host.log')}}
save('host.json',report)
assert run.returncode==0 and before==after and head==after_head and native_same
artifact=base/'stead-sdk-v2.tar'
operations=[]
for op, flag in [('build','--output'),('verify','--archive')]:
    command=['python3','scripts/package_sdk.py',op,flag,str(artifact)]
    start=now(); tick=time.monotonic()
    result=subprocess.run(command,capture_output=True)
    elapsed_op=time.monotonic()-tick
    (base/(op+'.log')).write_bytes(result.stdout+result.stderr)
    operations.append({'command':command,'exit_code':result.returncode,'started_at':start,'elapsed_seconds':elapsed_op,'stdout':result.stdout.decode(),'stderr':result.stderr.decode(),'log_sha256':digest(base/(op+'.log'))})
    assert result.returncode==0
save('artifact.json',{'protocol':'stead.sdk-artifact-capture/1','source_commit':head,'native_execution':False,'classification':'real-host-offline-package','operations':operations,'artifact':{'path':'stead-sdk-v2.tar','bytes':artifact.stat().st_size,'sha256':digest(artifact)},'inputs_unchanged_after_cli':inputs()==before,'head_unchanged_after_cli':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head})
print(json.dumps({'source':head,'host_exit':run.returncode,'tests':counts,'elapsed_seconds':elapsed,'native_mounts_unchanged':native_same,'artifact_bytes':artifact.stat().st_size,'artifact_sha256':digest(artifact),'records':str(base)}),flush=True)
