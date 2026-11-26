#!/usr/bin/env python3
"""Verify the Git identity of the built-in Handbook README. Use --update after editing it."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


APP = Path(__file__).resolve().parent
PROJECT = "019a0000-0000-7000-8000-000000000001"
IDENTITY = "Stead Handbook <handbook@stead.invalid> 1795651200 +0000"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def repository(directory):
    def git(*arguments, data=None):
        return subprocess.check_output(
            ["git", "-c", "pack.threads=1", *arguments], cwd=directory, input=data,
            env={"PATH": os.environ["PATH"], "GIT_CONFIG_NOSYSTEM": "1",
                 "GIT_CONFIG_GLOBAL": os.devnull, "LC_ALL": "C"},
        )

    def write_object(kind, content):
        return git("hash-object", "-w", "-t", kind, "--stdin", data=content).decode().strip()

    git("init", "-q", "--bare", "--template=", "--object-format=sha1", "-b", "main", ".")
    blob = write_object("blob", (APP / "src/handbook/README.md").read_bytes())
    tree = git("mktree", data=f"100644 blob {blob}\tREADME.md\n".encode()).decode().strip()
    commit = write_object("commit", (
        f"tree {tree}\nauthor {IDENTITY}\ncommitter {IDENTITY}\n\nRead the Stead Handbook\n"
    ).encode())
    git("update-ref", "refs/heads/main", commit)
    git("fsck", "--full", "--strict")
    pack = git("pack-objects", "--compression=0", "--window=0", "--stdout", "--revs",
               data=b"refs/heads/main\n")
    ids = sorted([blob, tree, commit])
    head = b"refs/heads/main".hex()
    manifest = {
        "format": "stead.git-pack-snapshot/1", "object_format": "sha1",
        "scope": {"home": "~zod", "project_id": PROJECT, "repository_id": PROJECT, "authority_epoch": 1},
        "head": head, "refs": {head: commit}, "pack_bytes": len(pack), "pack_sha256": sha(pack),
        "object_count": len(ids), "object_bytes": sum(int(git("cat-file", "-s", oid)) for oid in ids),
        "object_ids_sha256": sha(("\n".join(ids) + "\n").encode("ascii")),
    }
    snapshot = sha((json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n").encode())
    return {"readmeBlob": blob, "commit": commit, "snapshot": snapshot}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()
    path = APP / "src/handbookRepository.ts"
    original = path.read_text()
    next_source = original
    with tempfile.TemporaryDirectory() as directory:
        for name, oid in repository(directory).items():
            pattern = rf"^const {name} = '[0-9a-f]+';$"
            if len(re.findall(pattern, next_source, flags=re.MULTILINE)) != 1:
                raise SystemExit(f"Missing unique Git fixture field {name}")
            next_source = re.sub(pattern, f"const {name} = '{oid}';", next_source, flags=re.MULTILINE)
    if next_source != original:
        if not args.update:
            raise SystemExit("Run python3 web/app/handbook-repository.py --update after editing the Handbook README")
        path.write_text(next_source)


if __name__ == "__main__":
    main()
