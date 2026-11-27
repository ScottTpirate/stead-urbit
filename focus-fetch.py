"""Admit immutable public runtime inputs before isolating the native worker."""
import hashlib
import json
import pathlib
import subprocess
import tarfile

lock = json.loads(pathlib.Path('specs/urbit/toolchain.lock.json').read_text())
root = pathlib.Path('/runtime')
for group in ('runtime', 'kernel', 'boot_artifact'):
    obj = lock[group]
    path = root/'downloads'/obj['archive']
    subprocess.run(['curl', '-fsSL', '--retry', '3', '--max-time', '300', obj['url'], '-o', str(path)], check=True)
    assert hashlib.file_digest(path.open('rb'), 'sha256').hexdigest() == obj['sha256'], group
    if group != 'boot_artifact':
        with tarfile.open(path) as archive:
            archive.extractall(root/'bin' if group == 'runtime' else root, filter='data')
assert hashlib.file_digest((root/lock['runtime']['binary']).open('rb'), 'sha256').hexdigest() == lock['runtime']['binary_sha256']
