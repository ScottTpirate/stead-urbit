# Protected branch review

The Home owns proposal revisions, approvals, delegations, and the relation
between a merged proposal and its exact repository receipt. The saved review
board is scoped to one repository and authority epoch. A review command uses
the authenticated caller's current membership and project and Work permissions.

A contributor can propose a reachable commit against the exact current target
OID. The Home reads the target and the reachable commit graph from its own
repository. A proposal carries a Work ID, target ref, prior OID, head OID,
proposal ID, and explicit revision. An edit preserves the previous revision and
requires its own review. The merge step rechecks author eligibility, current
reviewer and merger authority, exact approval, branch protection, and the
target OID. The author can neither approve nor merge their own proposal.

The private merge path changes exactly one protected branch to an existing
reachable commit. It uses the same ref compare-and-swap, ancestry, closure,
and repository receipt rules as a stock push. A successful transition stores
the branch update, receipt, and merge link together. Ordinary pushes still
require current Git authorization and reject protected branch updates.

A merge request ID identifies one exact proposal revision and stable merger
binding. An authorized exact retry returns the original receipt after later
accepted changes. An ID reused for different inputs or a request whose current
authority has been removed fails without a write. Reload validates board bounds,
contiguous revisions, exact approval records, delegation history, and merge
links to repository receipts. A reader can look up a specific revision only
while the Home authorizes current access to its Work and ref scope.

A maintainer may grant an individual agent permission to propose against one
Work item and target branch. The grant is bounded by the two current member
bindings and a maximum of 24 hours. Revocation, expiry, scope change, or loss
of either member's required permissions removes eligibility. A delegation
carries proposal authority only. The Home still checks a separate review and
merge decision.

The browser carrier admits typed proposal, review, merge, delegation, and
lookup operations. Code shows the exact target and both original OIDs, with
a Work picker for new proposals. A merge that loses its response keeps the
original request ID and revision in the authenticated browser tab. A later
explicit retry requires a correlated confirmation from the Home. Signout,
identity changes, and workspace access invalidation clear the tab's retained
merge requests. Isolated worker admission, build execution and artifact
verification use their own gates.
