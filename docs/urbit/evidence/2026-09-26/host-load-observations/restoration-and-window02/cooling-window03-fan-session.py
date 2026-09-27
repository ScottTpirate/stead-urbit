#!/usr/bin/env python3
"""Temporary, host-specific ASUS fan boost; restore the initial curves on exit."""
import json
import os
from pathlib import Path
import signal
import sys
import time

BASE = Path('/home/skilgore/stead-urbit/.runtime/phase01-20260926/cooling-window03')
STOP = BASE / 'stop'
PROFILE = Path('/sys/firmware/acpi/platform_profile')
TEMPS = (35, 40, 50, 60, 70, 80, 90, 100)
PWMS = (255, 255, 255, 255, 255, 255, 255, 255)


def locate(name):
    matches = [p for p in Path('/sys/class/hwmon').glob('hwmon*')
               if (p / 'name').read_text().strip() == name]
    if len(matches) != 1:
        raise RuntimeError('Expected exactly one ' + name)
    return matches[0]


def emit(event, **values):
    record = {'time': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'event': event, **values}
    print(json.dumps(record), flush=True)


def run():
    if os.geteuid() != 0:
        raise RuntimeError('Local administrator authentication is required')
    if Path('/sys/class/dmi/id/product_name').read_text().strip() != 'ROG Strix G733ZS_G733ZS':
        raise RuntimeError('This temporary helper is only for the inspected laptop')
    if PROFILE.read_text().strip() != 'performance':
        raise RuntimeError('Power profile changed; inspect before applying')
    if STOP.exists():
        raise RuntimeError('Stop marker already exists')
    curve = locate('asus_custom_fan_curve')
    fans = locate('asus')
    names = [f'pwm{fan}_auto_point{point}_{kind}' for fan in (1, 2)
             for point in range(1, 9) for kind in ('temp', 'pwm')]
    names += ['pwm1_enable', 'pwm2_enable']
    original = {name: int((curve / name).read_text()) for name in names}
    if any(original[f'pwm{fan}_enable'] != 2 for fan in (1, 2)):
        raise RuntimeError('Custom curves already active; refusing to replace them')
    with (BASE / 'original.json').open('x') as file:
        json.dump({'product': 'ROG Strix G733ZS_G733ZS', 'profile': 'performance',
                   'curve_path': str(curve), 'values': original}, file, indent=2)
        file.write('\n')
    started = time.monotonic()
    changed = False
    def stop_requested(*_):
        raise KeyboardInterrupt('Stop requested')
    signal.signal(signal.SIGTERM, stop_requested)
    signal.signal(signal.SIGINT, stop_requested)
    try:
        changed = True
        for fan in (1, 2):
            for point, (temp, pwm) in enumerate(zip(TEMPS, PWMS), 1):
                (curve / f'pwm{fan}_auto_point{point}_temp').write_text(str(temp))
                (curve / f'pwm{fan}_auto_point{point}_pwm').write_text(str(pwm))
            (curve / f'pwm{fan}_enable').write_text('1')
        for fan in (1, 2):
            assert (curve / f'pwm{fan}_enable').read_text().strip() == '1'
            for point, (temp, pwm) in enumerate(zip(TEMPS, PWMS), 1):
                assert int((curve / f'pwm{fan}_auto_point{point}_temp').read_text()) == temp
                assert int((curve / f'pwm{fan}_auto_point{point}_pwm').read_text()) == pwm
        emit('applied', temperatures_c=TEMPS, pwm_255=PWMS, max_seconds=3600)
        while time.monotonic() - started < 3600 and not STOP.exists():
            if PROFILE.read_text().strip() != 'performance':
                raise RuntimeError('Power profile changed during cooling session')
            emit('sample', cpu_fan_rpm=int((fans / 'fan1_input').read_text()),
                 gpu_fan_rpm=int((fans / 'fan2_input').read_text()))
            time.sleep(5)
    finally:
        if changed:
            # Disable all custom fans before restoring stored data. A disable
            # resets the shared firmware mode; none of the original curves was active.
            failures = []
            for fan in (1, 2):
                try:
                    (curve / f'pwm{fan}_enable').write_text('2')
                except OSError as error:
                    failures.append(str(error))
            for name in names:
                if name.endswith('_enable'):
                    continue
                try:
                    (curve / name).write_text(str(original[name]))
                except OSError as error:
                    failures.append(str(error))
            actual = {name: int((curve / name).read_text()) for name in names}
            emit('restored', exact_original_values=(actual == original), failures=failures)
            if failures or actual != original:
                raise RuntimeError('Fan restoration incomplete; inspect original.json')


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        emit('stopped')
    except Exception as error:
        emit('failed', error=str(error))
        sys.exit(1)
