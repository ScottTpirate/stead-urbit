"""Compile the candidate and exercise focused suites on a fresh offline synthetic ship."""
import json
from pathlib import Path
import re
import sys
import time

sys.path[:0] = ['/src/scripts/sdk_native', '/src/scripts/urbit']
from native import Native
import native_units

native = Native('zod', 31337, lambda: None)
expected = json.loads(Path('/src/focus-files.json').read_text())
try:
    print('Booting synthetic ~zod', flush=True)
    native.start()
    imports = Path('/state/source')
    for name in expected:
        source = Path('/src/native/core/desk') / name
        target = imports / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    # A minimal generator forces both actual Gall agents through Ford.
    probe = imports / 'gen' / 'stead-signin-build.hoon'
    probe.parent.mkdir(exist_ok=True)
    probe.write_text("/=  home  /app/stead-home\n/=  identity  /app/stead-identity\n:-  %say\n|=  *\n[%noun %stead-signin-built]\n")
    print('Verifying imported source bytes', flush=True)
    native.install(imports)
    failure = False
    for name in ('stead-invitations', 'stead-identity', 'stead-session', 'stead-home-v8-rehearsal', 'stead-unit-failure'):
        negative = name == 'stead-unit-failure'
        path = ('/controls/' if negative else '/tests/') + name
        source = imports / (path.lstrip('/') + '.hoon')
        arms = re.findall(r'^\+\+  (test-[a-z0-9-]+)$', source.read_text(), re.M)
        if not arms:
            raise ValueError('Missing test arms for '+path)
        offset = native.logpath.stat().st_size
        print('Testing', name, len(arms), flush=True)
        try:
            beam = native.dojo('`path`%' + path).strip()
            observed = native_units.run(native.binary, native.pier / '.urb/conn.sock', beam, timeout=180)
            with native.logpath.open('rb') as stream:
                stream.seek(offset)
                raw = stream.read(262145).decode()
            assert len(raw) <= 262144
            print(native_units.verify_output(raw+'\n'+observed['stdout'], path=path, expected=arms,
                succeeds=not negative, failure_marker='stead-intentional-native-unit-failure' if negative else None), flush=True)
        except Exception as exc:
            failure = True
            print(name, type(exc).__name__, str(exc)[:600], flush=True)
            print(native.logpath.read_text(errors='replace')[max(0,offset):][-8000:], flush=True)
    try:
        compiled = native.dojo('+stead-signin-build', timeout=180).strip()
        print('Gall build', repr(compiled[:3000]), flush=True)
        assert compiled == '%stead-signin-built'
    except Exception:
        print(native.logpath.read_text(errors='replace')[-8000:], flush=True)
        raise
    if failure:
        raise ValueError('A focused suite failed')
finally:
    native.stop()
