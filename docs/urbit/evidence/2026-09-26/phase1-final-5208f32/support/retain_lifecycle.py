"""Retain a CLOSED synthetic native lifecycle, exact bytes only."""
import gzip,hashlib,json,pathlib,subprocess,sys
for flags in ([],['--push']):assert subprocess.check_output(['git','remote','get-url',*flags,'origin'],text=True).strip()=='https://github.com/ScottTpirate/stead-urbit.git'
assert subprocess.check_output(['git','remote','get-url','--push','upstream'],text=True).strip()=='DISABLED_UPSTREAM_PUSH'
label,destination=sys.argv[1:]
local=pathlib.Path('.runtime/phase01-20260926')/label
life=json.loads((local/'lifecycle.json').read_bytes())
def first_json(path):
    raw=path.read_text();return json.JSONDecoder().raw_decode(raw[raw.index('{'):])[0]
start=first_json(local/'start.log');result=first_json(local/(life['target']+'.log'))
source=pathlib.Path(result['evidence_file']);assert source.parent==pathlib.Path('.piers/fakes/logs')
native=json.loads(source.read_bytes());gid=start['execution_guard']['run_id']
assert native['source_commit']==life['source_commit']
if native.get('execution_guard'):assert native['execution_guard']['run_id']==gid
matches=[p for p in pathlib.Path('.runtime/execution-runs').glob('*/report.json') if json.loads(p.read_bytes()).get('run_id')==gid]
assert len(matches)==1
guard=matches[0];outer=json.loads(guard.read_bytes());assert outer['status'] in ('completed','failed','refused') and outer['exit_code'] is not None
assert json.loads((guard.parent/'control/source-context.json').read_bytes())['source_commit']==life['source_commit']
dest=pathlib.Path(destination);assert dest.is_relative_to('docs/urbit/evidence/2026-09-26') and '..' not in dest.parts
dest.mkdir(parents=True,exist_ok=False)
artifacts=[]
def keep(path,name,compress=True):
    assert path.is_file() and not path.is_symlink() and path.stat().st_size<=32*1024*1024
    raw=path.read_bytes();body=gzip.compress(raw,mtime=0) if compress else raw
    target=dest/(name+('.gz' if compress else ''));target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(body)
    artifacts.append({'path':str(target),'source':str(path),'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'original_bytes':len(raw),'original_sha256':hashlib.sha256(raw).hexdigest(),'encoding':'gzip' if compress else 'identity'})
keep(source,'native.json',False);keep(guard,'guard.json',False)
for path in sorted(guard.parent.rglob('*')):
    if path.is_file() and path!=guard:keep(path,'guard/'+path.relative_to(guard.parent).as_posix())
for path in sorted(local.iterdir()):
    if path.is_file():keep(path,'steps/'+path.name)
for ship in ('zod','bus','nec','bud','supervisor'):keep(source.parent/(ship+'.log'),'logs/'+ship+'.log')
if native.get('transport_artifact'):
    keep(source.parent/native['transport_artifact']['file'],native['transport_artifact']['file'],False)
marker=pathlib.Path('.piers/fakes/unclean-live.json')
if marker.exists():keep(marker,'unclean-live.json')
index={'protocol':'stead.native-retention/1','source_commit':life['source_commit'],'native_status':native['status'],'native_classification':native.get('classification'),'native_elapsed_seconds':native.get('elapsed_seconds'),'outer_guard_status':outer['status'],'outer_guard_exit':outer['exit_code'],'qualifies_phase':False,'scope':'Exact execution only; full manifest and independent review are separate.','transformations':'Exact copies or deterministic gzip of complete bytes.','artifacts':artifacts}
(dest/'index.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({key:value for key,value in index.items() if key!='artifacts'}));print('Retained '+str(len(artifacts))+' artifacts')
