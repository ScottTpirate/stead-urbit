# Experimental Vere source build

The pinned Vere 4.6 binary crashed after the native CI control disconnected from
a pending two-second Khan timer. This lane prepares 4.6 with only Urbit's official
`c0a35c6f6302baf536a13522afd1ac89ea8c7776` fix in `pkg/vere/newt.c`. Its MIT notice
and the exact patch are retained here. The project toolchain pin is unchanged.

The manual **Experimental runtime build** workflow runs only from this
repository's `main` on a standard disposable public GitHub runner. It captures
the immutable workflow commit and executes its reviewed controller. There are
no caller-selected source URLs, build commands, patches or candidate branches.

The controller downloads the fixed source/compiler/package archives in
`specs/urbit/runtime-source-build.json`, verifies their byte hashes and bounds,
and prepares data outside the build sandbox. It checks the complete extracted
source and Zig trees; only the pinned upstream newt hunk may differ from 4.6.
Two retired OpenBSD mirror URLs are replaced by GNU's official archives, still
requiring the original Zig package hashes. The nested zlib package is explicit.

Every compiler invocation runs as UID/GID 65534 with no capabilities or network
inside an empty Docker image, with read-only source/compiler/archive mounts,
a private PID namespace, no-new-privileges, two CPU cores, 4 GiB memory including
swap, and 256 tasks. Writable import/build storage is bounded to 512 MiB/3 GiB
tmpfs; `/tmp` is bounded to 256 MiB. The dependency cache becomes read-only for
the build. The controller reads back the container limits/mounts, bounds output
and execution time, removes only captured container IDs and verifies removal.
The workflow's final cleanup handles an interrupted controller. None of these
containers receives a host credential, authority ship, application source or
Docker socket. This lane is not run on the workstation.

The artifact includes the experimental binary, exact compiler and corresponding
dependency/source archives, patch/license, recipe, hashes and actual build and
cleanup records. A successful compile is build evidence only. Before adoption,
verify the actual GitHub run/commit and artifact bytes, run the unchanged native
disconnect/recovery control on the resulting binary, and rerun affected native
qualification against its exact identity. Never transfer historical qualification
to a new runtime merely because its version string remains 4.6.

Host controls (synthetic container observations and small filesystem inputs):

```sh
python3 -B -m unittest discover -s tests/runtime_build -p 'test_*.py'
```
