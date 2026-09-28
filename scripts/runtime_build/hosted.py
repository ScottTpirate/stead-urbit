#!/usr/bin/env python3
"""Build the fixed experimental Vere repair on a disposable hosted runner.

The root controller only fetches/verifies data and manages owned containers.
All compiler/build execution is offline, capability-free and unprivileged in
an empty container. No runtime pin, fake ship or native acceptance is changed.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import stat
import subprocess
import sys
import tarfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / '.runtime/vere-build'
OUT = ROOT / 'runtime-build-evidence'
sys.path.insert(0, str(Path(__file__).parent))
import inputs


def require(condition, message):
    if not condition: raise ValueError(message)


def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(argv, timeout=120, data=None):
    result = subprocess.run(argv, input=data, capture_output=True, timeout=timeout,
        env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null',
             'GIT_TERMINAL_PROMPT':'0','GIT_NO_REPLACE_OBJECTS':'1'})
    require(result.returncode == 0, 'Command failed: ' + argv[0] + ': ' + result.stderr.decode(errors='replace')[:2048])
    require(len(result.stdout) < 2*1024*1024, 'Command output bound')
    return result.stdout


def fetch(row, destination):
    url = row.get('download_url', row['url'])
    require(url.startswith('https://'), 'HTTPS download required')
    path = destination / row['file']
    require(path.parent == destination and re.fullmatch(r'[a-z0-9.-]+', row['file']), 'Download filename')
    with urllib.request.urlopen(url, timeout=60) as response, path.open('xb') as output:
        total = 0
        while block := response.read(1024*1024):
            total += len(block)
            require(total <= 80*1024*1024, 'Download size bound')
            output.write(block)
    require(path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], 'Downloaded bytes differ')
    return path


def extract(path, destination):
    destination.mkdir(mode=0o755)
    with tarfile.open(path) as archive:
        members = archive.getmembers()
        require(len(members) < 30000 and sum(m.size for m in members) < 800*1024*1024, 'Archive bounds')
        archive.extractall(destination, filter='data')
    children = list(destination.iterdir())
    require(len(children) == 1 and children[0].is_dir() and not children[0].is_symlink(), 'One archive root required')
    return children[0]


def verify_inputs(source, compiler, downloads, pin):
    original = inputs.archive(downloads / 'vere-4.6.tar.gz')
    require(original[pin['patch_file']] == {'sha256':'f18f203e823ad64433e2fb57a5959189c6cdec624a2a1d448738ee8354e0a833'}, 'Original newt source differs')
    original[pin['patch_file']] = {'sha256':pin['patch_sha256']}
    require(inputs.tree(source, ignore_git=True) == original, 'Source differs beyond approved patch')
    expected_compiler = inputs.archive(downloads / 'zig-0.15.2.tar.xz')
    require(inputs.tree(compiler) == expected_compiler, 'Extracted compiler differs')
    return {'source':original,'compiler':expected_compiler,'git_head_log':sha(source/'.git/logs/HEAD')}


def policy(inspect, mounts):
    config, host = inspect['Config'], inspect['HostConfig']
    require(config['User'] == '65534:65534' and host['NetworkMode'] == 'none'
        and host['ReadonlyRootfs'] is True and host['Privileged'] is False
        and host.get('CapAdd') in (None,[]) and host['CapDrop'] == ['ALL'] and host['CpuPeriod'] == 10000 and host['CpuQuota'] == 20000
        and host['Memory'] == 4294967296 and host['MemorySwap'] == 4294967296 and host['PidsLimit'] == 256
        and host['RestartPolicy']['Name'] == 'no' and host['Init'] is True
        and host['PidMode'] == '' and host['IpcMode'] == 'private'
        and host['SecurityOpt'] in (['no-new-privileges'], ['no-new-privileges=true']), 'Container isolation/resource readback differs')
    bindings=[m for m in inspect['Mounts'] if m['Type']=='bind']
    actual = {(m['Destination'],m['Source'],m['RW']) for m in bindings}
    require(len(bindings)==len(mounts) and actual == {(target,str(path),writable) for path,target,writable in mounts}, 'Container mounts differ')
    other=[m for m in inspect['Mounts'] if m['Type']!='bind']
    require(not other or (len(other)==1 and other[0]['Type']=='tmpfs' and other[0]['Destination']=='/tmp'
        and other[0].get('Source','')=='' and other[0]['RW'] is True),'Unexpected container mount')
    require(set(config['Env'] or []) == {'LANG=C.UTF-8','PATH=/usr/bin:/bin'}, 'Unexpected build environment')
    require(host['Tmpfs']=={'/tmp':'rw,nosuid,nodev,noexec,size=268435456'},'Temporary filesystem bounds differ')


def container(image, name, argv, mounts, workflow, deadline):
    command = ['docker','create','--name',name,'--label','stead.runtime.workflow='+workflow,
        '--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges',
        '--user=65534:65534','--cpu-period=10000','--cpu-quota=20000',
        '--memory=4294967296','--memory-swap=4294967296','--pids-limit=256',
        '--restart=no','--init','--stop-timeout=10','--workdir=/source','--env=LANG=C.UTF-8','--env=PATH=/usr/bin:/bin',
        '--tmpfs=/tmp:rw,nosuid,nodev,noexec,size=268435456',
        '--log-driver=local','--log-opt=max-size=4m','--log-opt=max-file=1','--log-opt=compress=false']
    for path,target,writable in mounts:
        command += ['--mount','type=bind,src='+str(path)+',dst='+target+('' if writable else ',readonly')]
    cid = run(command+[image,*argv]).decode().strip()
    require(re.fullmatch(r'[0-9a-f]{64}',cid), 'Owned container identity')
    record = {'id':cid,'name':name,'argv':argv,'status':'fail','cleanup':False}
    log_path=OUT/(name+'.log')
    process=None; selector=None; primary=None; record_error=None; result=bytearray(); start=time.monotonic()
    try:
        observation=json.loads(run(['docker','inspect',cid]))[0]
        policy(observation,mounts)
        record['before']=observation
        process=subprocess.Popen(['docker','start','--attach',cid],stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
        with log_path.open('xb') as log:
            while selector.get_map():
                require(time.monotonic()-start < deadline, 'Build command deadline')
                for key,_ in selector.select(timeout=.5):
                    block=os.read(key.fileobj.fileno(),65536)
                    if not block: selector.unregister(key.fileobj);break
                    result.extend(block);require(len(result)<=4*1024*1024,'Build output bound');log.write(block)
        require(process.wait(timeout=10)==0,'Attached container failed')
        after=json.loads(run(['docker','inspect',cid]))[0]
        policy(after,mounts);record['after']=after['State']
        require(after['State']['Running'] is False and after['State']['ExitCode']==0
                and after['State']['OOMKilled'] is False and after['State']['Pid']==0,'Build exit differs')
        record['status']='pass'
    except BaseException as error:
        primary=error
        record['error']=type(error).__name__+': '+str(error)
    finally:
        record['cleanup_errors']=[]
        try:
            run(['docker','rm','--force',cid],timeout=20)
        except Exception as error:
            record['cleanup_errors'].append('remove: '+type(error).__name__+': '+str(error))
        try:
            gone=subprocess.run(['docker','inspect',cid],capture_output=True,timeout=10)
            record['cleanup']=gone.returncode==1 and b'No such' in gone.stderr
        except Exception as error:
            record['cleanup_errors'].append('inspect: '+type(error).__name__+': '+str(error))
        try:
            if process is not None and process.poll() is None:
                process.terminate()
                try: process.wait(timeout=10)
                except subprocess.TimeoutExpired: process.kill();process.wait(timeout=5)
        except Exception as error:
            record['cleanup_errors'].append('attach: '+type(error).__name__+': '+str(error))
        try:
            if selector is not None: selector.close()
        except Exception as error:
            record['cleanup_errors'].append('selector: '+type(error).__name__+': '+str(error))
        try:
            if process is not None and process.stdout is not None: process.stdout.close()
        except Exception as error:
            record['cleanup_errors'].append('stdout: '+type(error).__name__+': '+str(error))
        if record['cleanup_errors'] or not record['cleanup']:record['status']='fail'
        record['elapsed_seconds']=round(time.monotonic()-start,3)
        try: (OUT/(name+'.json')).write_text(json.dumps(record,sort_keys=True)+'\n')
        except Exception as error: record_error=error
    if primary is not None:raise primary
    if record_error is not None:raise record_error
    require(record['cleanup'] and not record['cleanup_errors'],'Owned container cleanup incomplete')
    return result.decode('utf-8'),record


def main():
    require(os.getuid()==0 and sys.flags.isolated and sys.dont_write_bytecode,'Root isolated hosted controller required')
    workflow=os.environ['STEAD_WORKFLOW'];run_id=os.environ['STEAD_RUN_ID'];attempt=os.environ['STEAD_ATTEMPT']
    require(re.fullmatch(r'[0-9a-f]{40}',workflow) and re.fullmatch(r'[0-9]+',run_id) and re.fullmatch(r'[1-9][0-9]*',attempt),'Immutable hosted identity required')
    require(run(['git','-C',str(ROOT),'remote','get-url','origin']).decode().strip()=='https://github.com/ScottTpirate/stead-urbit.git','Derivative origin required')
    require(run(['git','-C',str(ROOT),'rev-parse','HEAD']).decode().strip()==workflow,'Workflow checkout differs')
    require(not run(['git','-C',str(ROOT),'status','--porcelain']),'Clean reviewed workflow source required')
    BASE.mkdir(mode=0o755,parents=True);OUT.mkdir(mode=0o755)
    pin_path=ROOT/'specs/urbit/runtime-source-build.json';pin=json.loads(pin_path.read_text())
    require(pin['format']=='stead.vere-source-build/1' and pin['target']=='x86_64-linux-musl','Fixed build profile required')
    downloads=BASE/'inputs';downloads.mkdir(mode=0o755)
    report={'format':'stead.hosted-runtime-build/1','status':'fail','qualifies_phase':False,
            'workflow':workflow,'run_id':run_id,'attempt':attempt,'manifest_sha256':sha(pin_path),'containers':[]}
    mounted=[]
    try:
        for row in pin['downloads']+pin['packages']: fetch(row,downloads)
        compiler=extract(downloads/'zig-0.15.2.tar.xz',BASE/'compiler')
        source=extract(downloads/'vere-4.6.tar.gz',BASE/'source')
        run(['git','init','-q',str(source)])
        run(['git','-C',str(source),'fetch','--depth=1','https://github.com/urbit/vere.git',pin['base_commit']])
        run(['git','-C',str(source),'reset','--mixed','FETCH_HEAD'])
        run(['git','-C',str(source),'apply',str(ROOT/'scripts/runtime_build/upstream-newt.patch')])
        before=verify_inputs(source,compiler,downloads,pin)
        report['input_identity_before']=before
        empty=io.BytesIO()
        with tarfile.open(fileobj=empty,mode='w'):pass
        image=run(['docker','import','-'],data=empty.getvalue()).decode().strip()
        require(re.fullmatch(r'sha256:[0-9a-f]{64}',image),'Empty root image identity')
        report['empty_image']=image
        common=[(compiler,'/zig',False),(source,'/source',False),(downloads,'/inputs',False)]
        state=BASE/'import-state';state.mkdir(mode=0o755)
        run(['mount','-t','tmpfs','-o','size=536870912,nodev,nosuid','tmpfs',str(state)]);mounted.append(state)
        os.chown(state,65534,65534)
        for i,row in enumerate(pin['packages']):
            output,record=container(image,'stead-runtime-'+run_id+'-'+attempt+'-fetch-'+str(i),
                ['/zig/zig','fetch','--global-cache-dir','/state/global-cache','/inputs/'+row['file']],
                common+[(state,'/state',True)],workflow,120)
            require(output.strip()==row['zig_hash'],'Pinned package hash differs')
            report['containers'].append(record)
        packages=inputs.tree(state/'global-cache/p');report['packages_before']=packages
        build=BASE/'build-state';build.mkdir(mode=0o755)
        run(['mount','-t','tmpfs','-o','size=3221225472,nodev,nosuid','tmpfs',str(build)]);mounted.append(build)
        (build/'global-cache/p').mkdir(parents=True)
        for path in [build,*build.rglob('*')]: os.chown(path,65534,65534)
        output,record=container(image,'stead-runtime-'+run_id+'-'+attempt+'-build',
            ['/zig/zig','build','--cache-dir','/state/cache','--global-cache-dir','/state/global-cache',
             '--prefix','/state/install','-Drelease','-Dtarget=x86_64-linux-musl','-j2','--summary','all'],
            common+[(build,'/state',True),(state/'global-cache/p','/state/global-cache/p',False)],workflow,2400)
        report['containers'].append(record)
        binary=build/'install/x86_64-linux-musl/urbit'
        for part in (binary,binary.parent,binary.parent.parent): require(not part.is_symlink(),'Redirected output')
        info=binary.stat();require(stat.S_ISREG(info.st_mode) and info.st_nlink==1 and 1_000_000<info.st_size<512*1024*1024,'Bounded regular runtime output required')
        report['input_identity_after']=verify_inputs(source,compiler,downloads,pin)
        report['packages_after']=inputs.tree(state/'global-cache/p')
        require(report['input_identity_after']==before and report['packages_after']==packages,'Build inputs changed')
        shutil.copyfile(binary,OUT/'vere-v4.6-newt-candidate')
        report['binary']={'file':'vere-v4.6-newt-candidate','sha256':sha(OUT/'vere-v4.6-newt-candidate'),'bytes':info.st_size}
        # Retain complete corresponding source, compiler and notices with the
        # experimental binary; this is not a production release artifact.
        with tarfile.open(OUT/'build-inputs.tar','w') as archive:
            for path in sorted(downloads.iterdir()):archive.add(path,arcname='inputs/'+path.name)
            for name in ('upstream-newt.patch','UPSTREAM_LICENSE.txt','hosted.py','inputs.py'):
                archive.add(ROOT/'scripts/runtime_build'/name,arcname='recipe/'+name)
            archive.add(pin_path,arcname='runtime-source-build.json')
            archive.add(source/'.git/logs/HEAD',arcname='recipe/source-git-head-log')
        report['source_bundle_sha256']=sha(OUT/'build-inputs.tar')
        report['status']='pass'
    except BaseException as error:
        report['error']=type(error).__name__+': '+str(error)
        raise
    finally:
        cleanup=[]
        for path in reversed(mounted):
            try: run(['umount',str(path)],timeout=10);cleanup.append({'path':path.name,'unmounted':True})
            except Exception as error:cleanup.append({'path':path.name,'unmounted':False});report['status']='fail'
        report['tmpfs_cleanup']=cleanup
        (OUT/'report.json').write_text(json.dumps(report,sort_keys=True)+'\n')
        print(json.dumps({'status':report['status'],'binary':report.get('binary'),'error':report.get('error')}),flush=True)
    require(report['status']=='pass','Runtime build did not complete cleanly')


if __name__=='__main__': main()
