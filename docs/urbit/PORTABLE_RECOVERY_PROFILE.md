# Portable current Work and Docs

`scripts/urbit/portable_recovery.py` captures one project's **currently readable
records** through the existing configured-team HTTPS query API. The result is a
portable ZIP of JSON and Markdown that can be inspected without Urbit. Its
offline verifier and extractor do not start a ship, execute commands from the
archive, import records, or grant authority.

This is one bounded Phase 4 data-recovery slice. It does not close URB-100,
URB-230, URB-240 or M4. The current capture path has host tests with synthetic
responses and a verified local native HTTPS capture with an individual member.
Restoring accepted records into the authority remains separate.

## Existing authority boundary

Configured homes support `stead.query/3` at `/stead/api/query`. The current
`stead-http` and `stead-browser` boundary requires the configured HTTPS
Host/Origin, an individual `__Host-stead-session` cookie, current CSRF token,
current member binding and current resource permissions. This client calls only
that query endpoint. It does not resume a session, approve a login, use an owner
cookie, query Khan/Lens, or access private state.

The supported query views expose complete Work descriptions in the individual
`work` query and exact canonical Markdown in the individual `document` query.
List views contain abbreviated text; the exporter reads every individual
record. Collection heads are observable metadata. The configured-team API does
**not** expose complete Git objects or history. The legacy `core_export.py`
routes and `team_git.py` observation hooks are fixture-specific and are not a
production export adapter. See [the configured-team contract](PHASE2_CONTRACT.md)
and the current `stead-views.hoon`, `stead-browser.hoon` and `stead-http.hoon`.

## Capture contract

The operator supplies an existing individual session using `--session-file`.
The file must be a regular file owned by the current user, with no group/other
permissions and no other hard links; leaf symlinks are refused. It has exactly
four string fields:

```json
{
  "origin": "https://configured-home.example",
  "principal_id": "<expected UUIDv7 principal>",
  "session": "<existing 64-character lowercase hex member cookie value>",
  "csrf": "<current 64-character lowercase hex CSRF value>"
}
```

Supply session material through a private file, not shell arguments or history.
The command does not obtain browser credentials automatically. A dedicated
browser export workflow remains future product work. The existing short-lived
session and CSRF rotation rules remain in force; concurrent session refreshes
can cause capture to fail. The tool leaves the input file under the operator's
control and never copies its secrets into the artifact or diagnostics.

```sh
python3 scripts/urbit/portable_recovery.py capture \
  --session-file /private/path/member-session.json \
  --project 019939ba-4000-7000-8000-000000000001 \
  --output /private/path/project.stead.zip
```

All connections verify the TLS certificate and hostname. `--ca-file` may supply
an explicitly trusted development CA; there is no insecure mode. Requests go
directly to the configured origin without environment proxy discovery and
never follow redirects. Only the specific member cookie is sent. HTTP error
bodies and transport exceptions are not printed. The local native test uses a
disposable Home and its pinned private CA.

Capture reads identity, all visible collections, project metadata, Work lists
and full records, document lists and full records, and visible relations. It
then rechecks project metadata, the full collection walk, and identity. Every
response must match its generated request ID, query kind and exact scope.
Continuation pages must retain their authority epoch and generation. Detail
reads must match their list revision/metadata; page heads must match their
collection. Duplicate IDs, dangling relations and malformed rows fail closed.

The collection query's current generation includes the project's readable
shared/private scopes and principal access generation. Matching that generation
and epoch before and after the walk prevents publication of a mixed view when
visible data or permissions change. This depends on the current v3 generation
contract; it is not a separately signed export snapshot. The entire capture is
discarded on a rejected query, stale cursor, changed generation, expired session
or exceeded bound. No partial artifact is published. A new paginated query in
another tab may invalidate this actor's ongoing walk; retry after it finishes.

| Limit | Bound |
| --- | ---: |
| Selected projects | 1 |
| Work records | 128 |
| Collections | 32 |
| Pages per collection | 32 |
| Relations | 256 |
| Query response | 262,144 bytes |
| Aggregate query responses | 32 MiB |
| Requests / elapsed capture deadline | 1,400 / 300 seconds |
| Work description / page Markdown | 8,192 / 32,768 UTF-8 bytes |
| Portable archive | 64 MiB; stored entries only |

The deadline is checked between reads and response chunks, with bounded socket
timeouts. It is an application I/O limit, not an external hard process deadline.

## Artifact and offline recovery

The artifact contains:

- `records.json`: complete current Work fields, collection metadata, relations,
  project metadata, and page metadata with exact file/hash references.
- `docs/<collection>/<page>.md`: canonical Markdown bytes, unchanged.
- `work/<item>.md` and `index.json`: deterministic readable views rebuilt from
  the captured records. They are not independent writable masters.
- `capture.json`: origin, principal/binding/home scope, authority epoch,
  generation, client observation times, correlated read hashes and counts.
  Cookies, CSRF values, pagination tokens and session audit IDs are omitted.
- `losses.json`, `README.txt`, and a manifest of every payload's length and
  SHA-256.

The command prints the archive's SHA-256. Retaining this digest in a separately
trusted location allows a later check of the exact original archive:

```sh
python3 scripts/urbit/portable_recovery.py verify /private/path/project.stead.zip
python3 scripts/urbit/portable_recovery.py verify /private/path/project.stead.zip \
  --sha256 '<previously retained archive SHA-256>'
python3 scripts/urbit/portable_recovery.py extract /private/path/project.stead.zip \
  --output /private/path/recovered-project
```

Verification checks archive inventory, file hashes, supported row schemas,
scope/reference consistency, and deterministic reconstruction of derived
Markdown/index files. It rejects compressed entries, symlinks, duplicate names,
traversal paths and unexpected entries. Extraction creates a new private
directory with private regular files. Existing output files or directories are
never replaced. Writes use held directory descriptors; a concurrent output
rename/replacement fails the final binding check. Interrupted extraction leaves
its private partial files for inspection; it never recursively deletes a
pathname that another process might have replaced. Ordinary ZIP tools can also read the archive, but do not perform
these application checks.

An intact archive proves **internal integrity**, not that the data came from a
particular home. Read hashes are client observations, not independently signed
accepted receipts. A person who changes the contents and recalculates every hash
can produce a different internally valid archive. The verifier always reports
that authentication is not independently verifiable offline, including when
capture recorded verified HTTPS. Synthetic test artifacts remain explicitly
labeled `synthetic-test-only`; they never become native evidence.

## Explicit losses and remaining gates

This export omits unreadable/deleted records, previous revisions, complete Git
history, Code repositories, attachments, accepted journal and command receipts,
historical attribution, activity and inbox. It omits grants, credentials,
sessions, identity keys and restore authority. A page's Git blob OID is computed
from its exact bytes; without the commit/tree graph, the observed collection
head does not independently prove those bytes belong to that commit.

The copied project role, binding IDs and head OIDs are observations only. They
must never become permissions or trusted history during an import. The archive
recovers readable records. A pier backup or authority restore has a different
scope. The local [create-only import](#local-create-only-import) below uses
the target member's current authority and creates fresh receipts.
Complete history export needs a bounded currently authorized Git object API.
Restoring an authority additionally needs single-writer fencing, current epoch
handling, session invalidation, interrupted-recovery tests and independent
operator qualification. No such capability is implied by successful extraction.

Authorized export creates another readable copy of project data. File modes
restrict local access; the archive is not encrypted and revocation cannot erase
copies already captured.

## Verification performed

`python3 -m unittest discover -s tests/urbit -p 'test_portable_recovery.py'`
passes 20 host tests. These use independent synthetic v3 responses and a mocked
HTTP transport, with real ZIP/filesystem operations. They cover pagination,
complete text/byte recovery, scope and identity correlation, changing revisions,
epochs/generations/heads, denial, bounds, private session files, verified-TLS
context configuration, redirect rejection, tampering, unsafe archive entries,
derived-index reconstruction, CLI verify/extract, no overwrite, and concurrent
output rename/replacement preservation. The initial directory-mode failure and
independently found pathname-cleanup race were corrected and the suite rerun.
These checks do not prove a real TLS
handshake, home authorization, native execution or Phase 4 qualification.

On November 9, the real Firefox/native fixture supplied a current individual
member session to the CLI. It verified native TLS, captured two Work items and
three Docs pages, verified the archive digest and extracted the current files.
The extracted Work record and three Markdown files matched browser-accepted
content. The temporary export credential was deleted. See the
[local acceptance record](LOCAL_ACCEPTANCE_20261109.md#corrected-real-browser-journey).

## Local create-only import

`scripts/urbit/portable_import.py` imports one verified current-record ZIP into
a **new** general project on a disposable `home.localhost` Home. The client
opens TCP on numeric loopback, verifies the TLS certificate for `home.localhost`
and checks the Home's configured fake runtime capability. Use a synthetic
archive and the importing member's own private session file. The target member
needs project-creation permission. Keep the test project under that member's
sole control throughout the import. The client checks its authority epoch and
initial policy revision before further writes. This is an observation before
each command, while the Home enforces current authorization at acceptance.

1. Prepare a private operator directory with mode 0700. Retain the separately
   trusted source archive SHA-256. Plan checks the target member without writing
   to the Home. Review the target Home and project, remapped IDs, exact command
   digests and loss report in the plan before proceeding.

   ```sh
   python3 scripts/urbit/portable_import.py plan \
     --archive "$archive" --archive-sha256 "$archive_sha" \
     --session-file "$member_session" --ca-file "$local_ca" \
     --target-home '~zod' --project-key IMPORT --title 'Imported project' \
     --output "$private_dir/plan.json"
   ```

2. Use the printed plan SHA-256 and confirm the new project ID explicitly.
   The progress directory must already exist with mode 0700. Apply reconstructs
   every command from the verified ZIP and plan. It submits up to 16 commands
   per invocation, starting with project creation. Reuse the original plan,
   archive and progress directory on every invocation.

   ```sh
   python3 scripts/urbit/portable_import.py apply \
     --archive "$archive" --session-file "$member_session" --ca-file "$local_ca" \
     --plan "$private_dir/plan.json" --plan-sha256 "$plan_sha" \
     --confirm-project "$new_project" --progress "$private_dir"
   ```

3. When the phase is `complete`, run the same arguments with `verify` in place
   of `apply`. Verification reads the current authorized target records and
   compares every Work field, collection, page body, relation and scope to the
   import plan. Verify before sharing the project or editing its contents.

Progress is explicitly `ready`, `awaiting-receipt`, or `complete`. A private
directory lock serializes the operator process. Before sending a command it
persists the request ID and a hash of the session audit ID. A correlated native
receipt is required to advance. A lost or rejected response leaves the same
request awaiting receipt and stops the batch with exit 2. Explicitly rerun the
same command to reconcile it. A fresh session for the same member binding can
recover a prior receipt because the original attempt's audit hash is retained.
Changing origin, Home, principal or binding stops the import. The progress file
is trusted local operator state and contains no session cookie or CSRF token.

The import preserves Work content and statuses, collection visibility, page
body bytes and typed relations. It rewrites the canonical page header ID and
relation endpoints. Embedded Markdown links remain byte-exact and can refer to
old IDs. The target Home creates fresh resource IDs, owner grants, revisions,
receipts and document Git commits. Private collections remain private to the
importing member. The original grant list, owner history, revisions and Git
ancestry remain outside the import. Planning and verification are read-only.
Each applied command commits individually, so a stopped import can leave a
partial project. Keep the plan and progress to resume it. Whole-project
rollback and import into an existing project remain separate work.

The host regression suite exercises exact remapping, loss after acceptance,
resume with an unchanged request across sessions, grant/binding changes,
receipt mismatch, locking, and content readback against a simulated authority.
The native Firefox fixture can run a separately reported import probe after
real member export, including a two-command batch, a fresh client process and
authorized readback. An optional probe failure leaves the independent Work and
Docs browser result intact. Check `portable_import` in the browser report for
the actual outcome. This local profile covers portable Work/Docs ZIP input.
