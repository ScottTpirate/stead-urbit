"""Exact Clay import for the disposable native development/acceptance lanes."""
from pathlib import Path
import shutil
import time
import core_conn
from digests import sha


def install(host, ship, command, check, native=Path('/native/core/desk')):
    sources = sorted(p for p in native.rglob('*') if p.is_file())
    if not sources:
        raise ValueError('Empty native input')
    for group in ([p for p in sources if p.suffix == '.hoon'],
                  [p for p in sources if p.suffix != '.hoon']):
        if not group:
            continue
        for source in group:
            target = host['LIVE'] / ship / 'base' / source.relative_to(native)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            check('installed:' + ship + ':' + str(source.relative_to(native)), sha(source) == sha(target))
        command(ship, '|commit %base')
        deadline = time.monotonic() + 60
        for source in group:
            literal = core_conn.atom(bytes.fromhex(sha(source))[::-1])
            parts = [*source.relative_to(native).with_suffix('').parts, source.suffix[1:]]
            path = '/' + '/'.join(parts)
            exists = f'=/  arc=arch  .^(arch %cy /=base={path})  ?=(^ -.arc)'
            while command(ship, exists).strip() != '%.y':
                host['execution_check']()
                if time.monotonic() > deadline:
                    raise TimeoutError('Clay import absent: ' + str(source.relative_to(native)))
                time.sleep(.2)
            expression = f'=/  raw=@t  .^(@t %cx /=base={path})  =({literal} (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))'
            command(ship, expression, '%.y')
    return {str(p.relative_to(native)): sha(p) for p in sources}
