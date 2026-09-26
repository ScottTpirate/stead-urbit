import datetime,json,pathlib,subprocess,sys,time
root=pathlib.Path.cwd()
label,target=sys.argv[1:]
assert label.replace('-','').isalnum() and target in ('delivery-check','core-test','gall-schedule')
for flags in ([],['--push']):assert subprocess.check_output(['git','remote','get-url',*flags,'origin'],text=True).strip()=='https://github.com/ScottTpirate/stead-urbit.git'
assert subprocess.check_output(['git','remote','get-url','--push','upstream'],text=True).strip()=='DISABLED_UPSTREAM_PUSH'
out=root/'.runtime/phase01-20260926'/label
out.mkdir(exist_ok=False)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
start=time.monotonic()
report={'source_commit':head,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'target':target,'steps':[]}
def step(command):
    begin=time.monotonic()
    with (out/(command+'.log')).open('x') as stream:
        result=subprocess.run(['make',command],stdout=stream,stderr=subprocess.STDOUT)
    row={'command':['make',command],'exit':result.returncode,'elapsed_seconds':time.monotonic()-begin}
    report['steps'].append(row)
    (out/(command+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps(row),flush=True)
    print((out/(command+'.log')).read_text()[-3000:],flush=True)
    return result.returncode
try:
    if step('start')==0 and step('wait-ready')==0:
        step(target)
finally:
    step('stop')
    report.update(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,
                  all_steps_exit_zero=all(row['exit']==0 for row in report['steps']))
    (out/'lifecycle.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
sys.exit(0 if report['all_steps_exit_zero'] else 1)
