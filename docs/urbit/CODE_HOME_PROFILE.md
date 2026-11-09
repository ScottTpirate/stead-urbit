# Native Home Git development profile

A project maintainer can enable one SHA-1 repository through the project
overview. The Code view appears after explicit enablement. A reader can issue
a read credential. A contributor or maintainer can issue a write credential.
The Home authorizes current role, member binding, repository and authority
epoch on each Git request. Grant removal takes effect on the next request,
including a push that had started sending bytes before removal.

Use the clone URL shown in Code. When a stock client prompts, use the username
`stead` and the individually issued credential as the password. Keep the URL
credential-free. The credential expires at the earliest of 15 minutes,
the issuing session expiry and the member expiry. The Home stores only its
digest while running. The Code view exposes its revocation handle separately.
Startup/bootstrap and team reconfiguration retire all device credentials.

The Git path has a separate binary request boundary and uses the same native
Eyre ownership and secure-origin checks as the Home. It rejects browser
cookies, proxy overrides and cross-origin authorization. The configured Home
owns objects, refs and accepted receipts in a single Gall transition.
Upload decoding and validation execute within one bounded event under the
initial profile. The response reports success only with that accepted state.
Receive checks current reachability, pack structure, exact SHA-1 object IDs,
graph and branch ancestry, policy, quota and prior OIDs. A protected branch
rejects direct writes. The exact-revision review path has its own integration
gate.

The development bounds are four repositories per Home, 64 objects and
256 KiB of accepted object bodies per repository, 16 refs, 32 accepted push
receipts, eight ref commands, and 64 KiB per incoming request. This is a small
synthetic test profile. Durable resumable quarantine, measured larger
repository limits, and receipt/retention management remain development work.
This profile handles SHA-1 Smart HTTP v0, full clone/fetch, fast-forward
updates, branch creation/deletion and tags. SHA-256, LFS, shallow and partial
clone, arbitrary ref namespaces and unqualified Git object shapes are outside
the initial profile. [Git HTTP protocol](https://git-scm.com/docs/gitprotocol-http)

## State and verification

Work/Docs-only Home state stays on v3. Enabling Code saves an outer v4 envelope
with the existing team state plus its repository map. Load checks scope,
capacity, object hashes and graph closure, then reconstructs current refs from
the ordered accepted receipt history before serving a new incarnation.
The Work/Docs journal and views keep their existing independent restore
checks. The [local populated recovery](LOCAL_CODE_IMPORT_20261109.md#saved-home-state)
checked both state fingerprints and original Git objects, refs, and protection
after reload and bootstrap of a stopped v4 copy.

The native browser lane invokes a separate stock-client diagnostic after
the team workflow. It uses the same disposable member, verified native TLS
and pinned Git executable and HTTP helper. The diagnostic reports native
branch/tag push, clone/fetch and denial observations independently of the
Work/Docs acceptance count. See the [release packaging profile](RELEASE_PACKAGING.md)
for the declared saved-state versions.
