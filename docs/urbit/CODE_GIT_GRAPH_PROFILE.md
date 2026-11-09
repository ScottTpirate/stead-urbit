# Derived Git object graph profile

`native/core/desk/lib/stead-code-git-graph.hoon` derives conservative structural
facts from exact SHA-1 objects. It supplies a bounded closure walk and an exact
commit/path read helper. Original object bodies and OIDs remain unchanged.
This library does not own objects, credentials, repository policy or refs.

## Public integration boundary

- `inspect(item: object) -> (each facts @tas)` rehashes the complete typed body,
  validates its OID and derives blob, tree, commit or annotated-tag facts.
- `start(roots: (list edge)) -> closure` initializes a bounded traversal.
  An edge is `[oid=@ux type=object-kind]`.
- `walk(work: closure, load: reader) -> closure` processes one queued item.
  The caller repeats only while the result is `%checking`. `%verified` supplies
  the reachable OID-to-kind map; `%invalid` supplies a reason. Terminal results
  are unchanged by subsequent calls.
- `read-path(revision: @ux, path: (list @t), allowed: (map @ux object-kind),
  load: reader) -> (each object @tas)` returns an exact blob from an exact commit
  and validated path. Every selected object is checked against the supplied
  reachable map, loaded by exact OID and rehashed. Missing, forbidden, corrupt
  or mismatched selections return `%unavailable`; invalid paths return
  `%path-bound`.

`reader` is a pure `@ux -> (unit object)` callback. The authoritative home must
supply a loader restricted to the current principal's authorized repository,
including only admissible quarantine objects when validating an import. Never
provide a global OID store. The home must choose permitted ref/proposal roots,
reauthorize the principal and roots on every read, and derive `allowed` from a
verified closure for that policy. This module does not authenticate the caller,
validate policy epochs or turn an arbitrary caller-supplied map into authority.

Preserve the closure produced by `start`/`walk`; accepting client-authored work
state would bypass its budget and reachability invariants. Integration must
schedule repeated steps with a bounded job budget and handle `%invalid` without
publishing objects or updating refs.

## Supported structure and limits

| Input or work | Bound / accepted profile |
| --- | --- |
| Object | Existing object helper: exact width and SHA-1, at most 8 MiB |
| Initial roots | At most 256 |
| Graph traversal | 32,768 visit actions, queue at most 32,768 items, 64 MiB unique object bodies |
| Tree | At most 4,096 entries; exact modes `40000`, `100644`, `100755` |
| Tree entry name | 1–255 bytes; unchanged in output |
| Commit or tag header scan | First 65,536 bytes, newline terminated with a blank header separator |
| Commit parents | At most 64 unique OIDs |
| File read | 1–32 valid path segments; final target must be a blob |

Trees reject duplicate names, out-of-order entries, zero or truncated OIDs,
unsupported modes and invalid names. Directory sorting uses a trailing `/` in
the comparison key. Symlinks (`120000`) and submodules (`160000`) are outside
this first profile. Names reject `.`/`..`, ASCII-casefolded `.git`/`git~1`, a
trailing dot or space, control bytes, DEL, slash, backslash and colon. Names
are not normalized, and this is not a complete filesystem portability policy.

Commits require a tree line, bounded unique parent lines, nonempty author and
committer lines in that order, then an eventual blank separator. Annotated tags
require object, supported type and nonempty tag lines, then a blank separator.
The graph walk checks required target types, missing objects, OID/body mismatch,
active-path cycles, queue/visit limits and aggregate body bytes. Duplicate
reachable OIDs are checked for consistent kinds without charging their bodies
again. Leave actions unwind the active path; each distinct visited object adds
one such action.

## Qualification boundary

This is derived-structure validation, **not `git fsck --strict` equivalence**.
Author/committer identity and timestamp syntax, optional headers, tag naming and
all upstream object diagnostics are not fully validated here. Complete Git
acceptance needs separately reviewed object-validity rules, authorized delta
base selection, quarantine, final atomic ref authorization and durable receipt
handling. No route, storage mutation, pack decoder or server was added by this
slice.

The [retained native evidence](evidence/2026-11-08/code-git-graph/README.md)
records 29 passing native arms plus two failing controls. Cases include closure,
type/missing/corrupt-object rejection, exact file reads, forbidden/unreachable
selections, unsupported modes, duplicate/order checks and selected boundary
states. Maximum repository capacity, all malformed metadata combinations,
complete filesystem portability and service-level revocation/restart behavior
were not qualified by those checks.
