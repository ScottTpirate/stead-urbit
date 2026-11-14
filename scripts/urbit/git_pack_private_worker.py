"""Private host-side Git worker. Requests never contain uploader credentials."""
from __future__ import annotations

import math
import os
from pathlib import Path
import stat
import time

from execution_policy import directory_fd
import git_pack_proof as proof
from git_pack_receive_adapter import Admission, proof_snapshot, within
from portable_code import private_directory
from portable_recovery import require, same_entry, same_path


class PrivatePackWorker:
    """Use one operator-selected, private store and exact stock Git executable.

    The instance belongs to a trusted worker. A carrier must authenticate the
    instance's reply independently. Neither a digest nor this type authenticates
    a remote worker. Admission and request paths are selected by that carrier.
    """

    def __init__(self, storage: Path, git: Path, *, clock=None):
        storage, git = Path(storage), Path(git)
        require(storage.is_absolute() and storage.resolve(strict=True) == storage
                and git.is_absolute() and git.resolve(strict=True) == git, 'worker-private-paths')
        require(stat.S_ISREG(git.stat().st_mode) and os.access(git, os.X_OK), 'worker-git-executable')
        self.storage = storage
        self.git = git
        self.clock = clock if clock is not None else lambda: time.time_ns() // 1_000_000
        with directory_fd(storage) as directory:
            self.store_binding = private_directory(directory)
        self.git_binding = git.stat()

    def __call__(self, admitted: Admission, wire_path: Path, deadline: float) -> bytes:
        require(isinstance(admitted, Admission), 'worker-admission-type')
        require(type(deadline) in (int, float) and math.isfinite(deadline), 'worker-deadline')
        wire_path = Path(wire_path)
        require(wire_path.is_absolute(), 'worker-private-paths')

        def checked_clock():
            within(deadline)
            require(same_path(self.storage, self.store_binding), 'worker-store-binding')
            with directory_fd(self.git.parent) as parent:
                require(same_entry(parent, self.git.name, self.git_binding), 'worker-git-binding')
            executable = self.git.stat()
            require(executable.st_mtime_ns == self.git_binding.st_mtime_ns
                    and executable.st_ctime_ns == self.git_binding.st_ctime_ns, 'worker-git-binding')
            return self.clock()

        claim = proof.admission(admitted.raw, admitted.sha256, checked_clock())
        raw = proof.prepare(admitted.raw, admitted.sha256, self.storage, wire_path, str(self.git),
                            now_ms=checked_clock, deadline=deadline)
        proof_snapshot(raw, admitted, claim)
        checked_clock()
        return raw
