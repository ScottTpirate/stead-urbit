# Exact proposal reviews

`stead-code-review` is a pure helper for the future authoritative proposal
store. A proposal identifies its author, project, repository, Work item,
target branch, authority epoch, revision number, expected prior commit and
proposed commit. The home supplies the authenticated actor and looks up each
record through its current policy.

`approve` checks the reviewer's scoped permission and the current epoch,
then binds the entire proposal to the reviewer. A proposer cannot approve
their own change. This proof belongs in the home's accepted review store.

`check-merge` takes that stored proof and the current target commit. It
requires an independently authorized merger, rechecks the reviewer's current
permission, and compares the proof with the current proposal and authority
epoch. One person other than the author can hold both permissions. An edit,
ref change, scope change or revoked reviewer invalidates the
proof for acceptance. The resulting ref update still goes through the native
receive decision and authoritative commit, including object and ancestry
validation. A proposal receipt alone cannot grant merge or release authority.

The helper does not store proposals, expose an API, run a build, or approve
a release. The home must bind Work item and repository IDs to actual current
records and persist proposal revisions and reviews before a product workflow
can use these checks.
