# Exact Git worker profile

`scripts/urbit/code_build_worker.py` is an offline command for an
unprivileged Linux worker. Use a separately provisioned worker for product
jobs. The local synthetic proof uses a static recipe which never runs
repository code, hooks, shell commands, or deployments.

The initial allowlist contains `stead.build.git-tree-manifest/1`. The recipe
pin is the SHA-256 of that exact ASCII identifier with no trailing newline.
The version identifies the static recipe semantics. An incompatible recipe
change needs a new identifier and matching Home allowlist entry. The
receipt also records the exact worker script and Git binary hashes.

```text
9dfe50f0b7df0c270bff4c06a67251eac3e94476c034e4e3d0209fa8aa96fc6e
```

## Inputs

Obtain a job from the Home and a sealed SHA-1 Git bundle through a currently
authorized source transfer. The worker needs the trusted job digest and
Git binary digest. The job record uses protocol `stead.build-job/1` and
contains these exact fields.

| Field | Meaning |
| --- | --- |
| `project_id`, `proposal_id`, `job_id` | Exact UUIDv7 authority identifiers |
| `proposal_revision`, `attempt` | Positive integer review revision and leased attempt |
| `commit` | Original lowercase 40-digit Git commit OID |
| `source` | SHA-256 source binding supplied by the Home |
| `recipe` | Allowlisted recipe SHA-256 |
| `bundle_sha256` | SHA-256 of the complete supplied Git bundle bytes |

The source binding is opaque to the offline worker. Its independent source
readback uses the exact Git commit and object graph. Authority must bind the
source digest, object graph, job and attempt when authorizing the effect.

Use a private working directory and private regular job and bundle files.
Bubblewrap must be able to start unprivileged namespaces. The command never
fetches the source. It accepts a self-contained Git bundle v2 of at most
2 MiB, with SHA-1 identities. No credentials or SSH agent sockets are needed.

```sh
python3 -B scripts/urbit/code_build_worker.py describe
python3 -B scripts/urbit/code_build_worker.py run \
  --job "$JOB" --job-sha256 "$TRUSTED_JOB_SHA256" \
  --bundle "$BUNDLE" --git-binary "$GIT" --git-sha256 "$TRUSTED_GIT_SHA256" \
  --output "$PRIVATE_WORKER_DIRECTORY/result"
```

## Execution and evidence

The command verifies the inputs before staging them. Bubblewrap starts
separate network, mount, PID and user namespaces with loopback only, clears
the environment, drops capabilities, and presents the staged inputs
read-only. Only the system runtime and sealed inputs are mounted from the
worker host. The job has bounded temporary storage, memory, process CPU
time and an outer elapsed-time limit. It imports into a new bare temporary
repository, runs strict stock Git verification and reads the exact commit's
tree without a checkout. Symlinks and submodule entries are outside this
recipe profile.

The canonical `tree-manifest.json` artifact is limited to 8 KiB. It binds
the original commit and tree IDs, file paths and modes, blob OIDs, byte
lengths, and SHA-256 hashes. It contains no file bodies. The command then
writes `result.json` with the exact job and digests plus an attestation
containing `source`, `recipe`, `output`, and `outcome`. The result is
written last in a new private output directory. Existing outputs are
preserved and an interrupted publication without a complete result is
ineligible for admission.

The result is evidence from this worker process. The Home must independently
authenticate the assigned worker and validate its current lease, attempt,
exact source, allowed recipe and artifact bytes before accepting any build
outcome. The worker never advances refs, grants roles, or deploys.

## Home admission

The configured Code API at `/stead/api/code` uses the existing authenticated
individual session and CSRF header. All fields in `stead.code/1` are strings.
The Home derives the current actor, project role and proposal scope. Include
`protocol`, `project_id` and `action` in each call.

| Action | Additional fields |
| --- | --- |
| `build-queue` | `job_id`, `proposal_id`, `revision`, `worker_ship`, `recipe` |
| `build-job` | `job_id` |
| `build-claim` | `job_id`, `expected_attempt` |
| `build-finish` | `job_id`, `attempt`, `source`, `recipe`, `output`, `outcome`, `artifact_base64` |
| `build-cancel` | `job_id` |
| `build-release` | `job_id`, `request_id` |

A maintainer assigns a current member with project read access. The author
and requester cannot run that job. The lease and exact proposal revision bind
the job. A worker submits canonical Base64 of the actual artifact. The Home
recomputes its SHA-256 and stores the bytes with the accepted evidence.
For a successful outcome it also reconstructs the pinned recipe's exact
manifest from the approved commit, including paths, modes, blob IDs, lengths
and byte digests. A failed result remains a bounded worker attestation.
Only a separate authorized release principal can record a release intent
after the approved ref is accepted. The intent records authority and has no
deployment effect.

## Local synthetic check

The isolated recipe ran twice against the same verified Git 2.55.0 bundle
and produced byte-identical 355-byte manifests. The commit was
`10d569c3f931dfd3b194917a23b9d771d05245fd` and the artifact SHA-256 was
`1aebd7445c1fc86a904407d4fce596e3f57506d88b108e249663197d5f46b80e`.
A job pinned to a missing commit failed without publishing an output.
The private fixture receipt is
`.runtime/code-build-worker-smoke-LjuItMNG/final-result/result.json`
with SHA-256 `0dd68e98a000ea7183cbc2441236c45c53ccf1e07e3ca9e4db8054f5338b58bc`.
The worker script SHA-256 was
`86c4c1b9948b75059e0556e0c8df0debe3c92a9842418a876561c322297a2cc7`.
