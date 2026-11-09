# Receive staging and ref decisions

The code repository receive path is split into wire decoding, quarantine and a
final home transaction. These helpers are native and pure. This increment
does not add a Smart HTTP route or write repository refs.

1. Parse the bounded command block and admit only the transport capabilities
   actually advertised. Hold the remaining bytes in quarantine.
2. Verify pack framing, expand bounded objects and deltas, verify exact object
   IDs, and validate object graph and reachability within the repository.
   Resolve targets only from validated objects or the same authorized store.
3. Recompute authorization from the current member or delegation, epoch and
   repository policy. Pass that current policy and verified graph facts into
   `decide:stead-code-receive`.
4. The home commits the successful candidate ref map together with its objects
   and receipt in one authoritative transition. It publishes accepted status
   after that transition.

The decision helper checks the prior OIDs against the same original ref map,
allows at most 32 changes, and returns an entire candidate map or one error.
It recognizes full branch and tag refs, checks their final path namespace,
rejects protected deletion, tag replacement and non-fast-forward branch
updates, and requires branch targets to be commits. The allowed callback is
evaluated before a ref lookup and must represent the current effective policy.
The current ref map comes from validated repository state with nonzero SHA-1
OIDs and valid names under the configured repository profile.
A caller cannot supply authorization, object existence or ancestry assertions
as trusted wire input. Keep protected ref/review policy and receipt acceptance
in the authoritative home.

The outer pack checksum alone says nothing about the contents of its entries.
The independent test oracle in `scripts/urbit/git_pack_oracle.py` expands
self-contained SHA-1 packs and both delta forms against bounded budgets. Its
tests compare original bytes and IDs with stock Git-generated packs and strict
indexing, including malformed entries with valid trailers. The oracle does not
serve requests, verify a project graph, or replace a native quarantine
implementation. [Git pack format](https://git-scm.com/docs/gitformat-pack)

Still required before a usable Git endpoint: native bounded pack expansion
and graph validation, scoped per-device credentials, Smart HTTP discovery and
responses, one state-owning transaction, and real stock clone/fetch/push with
mid-upload revocation and conflict cases.
