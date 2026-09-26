"""Executed inside the harness sandbox; any isolation failure is fatal."""
import json
from pathlib import Path
import socket
import subprocess

interfaces = subprocess.check_output(['ip', '-j', 'address'], text=True)
assert {item['ifname'] for item in json.loads(interfaces)} == {'lo'}
assert not Path('/home/skilgore').exists()
assert not Path('/run/docker.sock').exists()
assert not Path('/var/run/docker.sock').exists()
assert not Path('/root/.gitconfig').exists()
with socket.socket() as connection:
    connection.settimeout(.2)
    assert connection.connect_ex(('1.1.1.1', 443)) != 0
print('PASS private network (loopback only, no internet route), no host home or Docker socket')
