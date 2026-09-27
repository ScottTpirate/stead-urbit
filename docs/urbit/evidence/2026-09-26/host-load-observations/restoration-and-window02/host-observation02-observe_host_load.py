"""Read-only bounded host-load/temperature correlation; no native execution."""
import datetime,json,os,time
from pathlib import Path
BASE=Path(__file__).parent
STOP=BASE/'observe-host-load.stop'
OUT=BASE/'observe-host-load.jsonl'
HZ=os.sysconf('SC_CLK_TCK')
def processes():
    rows={}
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            raw=(path/'stat').read_text(); end=raw.rindex(')'); parts=raw[end+2:].split()
            rows[int(path.name)]={'comm':raw[raw.index('(')+1:end], 'ticks':int(parts[11])+int(parts[12]), 'start':int(parts[19])}
        except (OSError,ValueError,IndexError):continue
    return rows
def sensors():
    result={}
    for path in Path('/sys/class/thermal').glob('thermal_zone*'):
        try:
            kind=(path/'type').read_text().strip()
            if kind in ('TCPU','x86_pkg_temp'):result[kind]=int((path/'temp').read_text())/1000
        except (OSError,ValueError):pass
    return result
assert not STOP.exists()
previous=processes();before=time.monotonic();start=before
with OUT.open('x') as out:
    while time.monotonic()-start<3600 and not STOP.exists():
        time.sleep(1); now=time.monotonic(); current=processes(); delta=now-before; top=[]
        for pid,row in current.items():
            old=previous.get(pid)
            if old and old['start']==row['start']:
                cpu=(row['ticks']-old['ticks'])/HZ/delta*100
                if cpu>=1:top.append({'pid':pid,'comm':row['comm'],'cpu_percent_of_one_core':round(cpu,1)})
        top=sorted(top,key=lambda row:row['cpu_percent_of_one_core'],reverse=True)[:8]
        out.write(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(now-start,3),'sample_seconds':round(delta,3),'cpu_temperatures_c':sensors(),'process_deltas':top,'limitations':'Process CPU deltas are sampled, miss exited short-lived processes, and establish correlation only; no process arguments or environment captured.'})+'\n');out.flush();previous=current;before=now
