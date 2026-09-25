"""Fixed fake-only bootstrap and exact native baseline observations."""
import urgit_seed


def verify_work(path, baseline):
    if baseline.get('mode') != 'verified-stopped-fake-seed' or urgit_seed.tree(path) != baseline.get('copied'):
        raise ValueError('Actual audit boot tree differs from verified stopped seed')


def argv(mode, loom):
    command = ['/runtime/vere', '-t', '-L', '--loom', str(loom), '--no-dock',
               '--http-port', '8080', '-b', '127.0.0.1']
    if mode == 'cold':
        command += ['-F', 'zod', '-B', '/runtime/pill', '-A', '/kernel/pkg/arvo', '-c']
    elif mode != 'verified-stopped-fake-seed':
        raise ValueError('Unknown bootstrap mode')
    return command + ['/work/zod']


def validate(identity, kelvin, clean):
    if (identity.strip(), kelvin.strip(), clean.strip()) != ('~zod', '%408', '%.y'):
        raise ValueError('Native fake identity, Kelvin or clean Urgit baseline failed')
