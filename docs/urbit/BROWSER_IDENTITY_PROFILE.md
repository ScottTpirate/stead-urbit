# Browser-only organization sign-in

URB-160 chooses an implementation profile. The current Home and the first
live synthetic pilot use individual native ship approvals. The browser-only
profile below requires new verifier, Home and browser code before operators
can enable it. A browser-only employee will need an organization IdP account
and a browser. The organization still operates its Urbit Home.

## Feasibility decision

Use OpenID Connect Authorization Code with PKCE S256 through a dedicated
identity verifier. Deploy the verifier at a distinct HTTPS origin with one
configured Home and one allowlisted issuer for the first profile. Use a
maintained OIDC library for token exchange and validation. Keep Stead
sessions, grants, documents, repository contents and mutation authority on the
Home. The browser sends Stead API requests directly to Home. The verifier
receives login transactions and can assert authentication for pre-enrolled
accounts within its configured Home. Treat its signing key and the chosen IdP
as trusted for those accounts. The verifier gets no ship-owner credential,
project data credential or permission to grant, delegate, review or merge.
[OIDC Core §3.1](https://openid.net/specs/openid-connect-core-1_0.html#CodeFlowAuth)
and [OAuth Security BCP §2.1](https://www.rfc-editor.org/rfc/rfc9700.html#section-2.1).

The present [configuration](../../native/core/desk/lib/stead-team-config.hoon)
indexes members by ship, and the [Home authorization library](../../native/core/desk/lib/stead-team.hoon)
resolves browser sessions through that same index. The
[credential](../../native/core/desk/lib/stead-code-credentials.hoon) and
[delivery](../../native/core/desk/lib/stead-code-delivery.hoon) reducers also
recheck ship-bound actors. Browser-only identity needs a tagged binding and a
common current-binding resolver through those paths. Keep Gall's authenticated
sender as the input to the native binding resolver. Keep the Home's native TLS,
cookie, scope and final authorization checks. Verify one fixed Ed25519 proof
profile in Hoon. The pinned 408k kernel source at
`5a187fededc4582a34fcd6055c67bb63e0917b94` exposes `veri-octs:ed:crypto`.
The inspected `pkg/arvo/sys/zuse.hoon` SHA-256 is
`eeb392d750757ec91aa3848d5a35ad4ba20557be85e62293fc63f72933343d73`.
This establishes a candidate native primitive. Native interoperability,
canonical signature handling and bounded verification cost need execution
before enabling the profile.
[Kernel source](https://github.com/urbit/urbit/blob/5a187fededc4582a34fcd6055c67bb63e0917b94/pkg/arvo/sys/zuse.hoon#L1259)
and [RFC 8032 §5.1.7](https://www.rfc-editor.org/rfc/rfc8032.html#section-5.1.7).

Support passkeys initially through the organization's IdP. Record the method
as OIDC and record only assurance that follows from configured, verified
issuer policy. An unrecognized or missing authentication-method claim carries
ordinary OIDC assurance. Apply any stronger required assurance before the Home
issues a session. For a future Stead-operated WebAuthn verifier, bind a
credential ID and public key to a pre-enrolled principal. Use an opaque user
handle, exact HTTPS origin and RP ID, fresh one-use challenges, verified
signatures and required user verification. Enrollment and recovery require
explicit authorization. Counter changes are a risk signal and the policy
must account for authenticators that return zero and for backed-up credentials.
Keep a stable RP domain across Home moves or require re-enrollment after the
origin changes. Direct WebAuthn, verifier selection and issuer migrations
each require their own qualification. [WebAuthn registration](https://www.w3.org/TR/webauthn-3/#sctn-registering-a-new-credential)
and [assertion verification](https://www.w3.org/TR/webauthn-3/#sctn-verifying-assertion).

## Browser login and proof

1. From Home, choose organization sign-in. A same-origin, bounded request
   creates a two-minute Home challenge tied to the pending browser cookie,
   Home, organization, exact origin, current Home incarnation, configured
   verifier, verifier revision and member configuration revision. Home
   generates a 256-bit random challenge ID. Apply the existing global pending
   limit, allow one open OIDC challenge per pending browser cookie, and require
   logout before beginning sign-in if the browser has a live Stead session.
2. The browser submits the challenge ID and incarnation by top-level HTTPS
   form POST to the configured verifier. Use a dedicated Home handoff
   document with `form-action` limited to the verifier and a
   `strict-origin` referrer policy so the verifier can check the exact
   Home Origin. Keep normal Home pages' restrictions. The verifier accepts
   only that origin and route, bounds and rate-limits attempts, creates an
   independent one-time transaction, and binds random OAuth state and nonce
   plus the server-held PKCE verifier to a separate host-only, Secure,
   HttpOnly, SameSite=Lax transaction cookie. Its only redirect URI is a
   fixed HTTPS GET callback registered with the configured IdP. Both origins
   use fixed redirect targets. [Fetch Origin rules](https://fetch.spec.whatwg.org/#append-a-request-origin-header).
3. The verifier checks the cookie, state, selected issuer and transaction expiry,
   atomically claims the transaction, and exchanges the code once. Pin
   issuer and provider endpoints in reviewed configuration. Validate TLS,
   the ID-token signature with the issuer's current keys and allowed
   algorithm, exact `iss`, expected `aud` and `azp` where applicable,
   `sub`, `nonce`, `exp` and `iat`. Reject ambiguous keys and
   claims, enforce bounded clocks and use `max_age` with verified
   `auth_time` for policies requiring fresh authentication. Bound key
   refresh to the configured key endpoint. Retain no provider refresh
   token. Erase transient codes and tokens after exchange, redact query
   strings and tokens from logs, and redirect to a fixed return page on Home
   with no claims, codes or tokens in the URL.
4. The verifier uses exact issuer/subject bytes to derive the subject tag
   below and POSTs a signed proof directly to Home. Home checks native TLS,
   exact Host, route, media type and body limits. This route admits a
   configured verifier signature in place of browser authentication, and
   accepts no cookies or forwarding headers. No cross-origin browser
   access is needed. Home checks the configured verifier, matching challenge
   and its current revisions, active enrolled binding and proof age using its
   own clock. The first valid proof stages an approval. Identical retries
   are idempotent while the approval and proof remain valid. A different proof
   for the same challenge cannot replace it.
   No proof may create or edit a principal or grant.
5. The same browser returns to Home and explicitly confirms the approved
   identity shown from Home's enrollment record. The same-origin consume
   endpoint checks the pending cookie, challenge, binding revision, verifier
   and member configuration revisions, expiry and incarnation again. In one
   transition, consume the challenge and rotate to the Stead session and CSRF
   pair, with the session expiring no later than thirty minutes, the binding
   expiration or the configured assurance lifetime. Home records the method
   `oidc-verified-browser/1`, verifier revision and policy assurance in its
   private actor context, without a member ship field. Home grants business
   access only through existing authorization. Wrong browsers, expired
   pending requests and replays receive an opaque denial.

Home records explicit pending and approved states. A verifier proof can
advance pending to approved, and only browser confirmation can advance
approved to consumed. Expiry, restart and relevant configuration changes
retire both pending and approved challenges. Keep the verifier transaction
separate, with pending, claimed and finished states. After a failed code
exchange, a new login creates a new transaction.

Use a JSON object with exactly `protocol`, `home`, `origin`,
`organization_id`, `verifier_id`, `verifier_revision`, `issuer_id`,
`challenge_id`, `incarnation`, `subject_tag`, `assurance`,
`issued_at_ms`, `expires_at_ms` and `signature`. Fields are bounded ASCII
strings using [Stead canonical JSON](CONTRACTS.md#limits-and-serialization).
Use canonical ship and origin strings, UUIDs for organization, verifier and
issuer IDs, canonical unsigned 64-bit decimals for revisions and times,
and 64 lowercase hex characters for challenge, incarnation and subject tag.
The initial assurance enum is `oidc` and `oidc-policy-verified`, with the
second value scoped to the configured verifier and policy revision.
`protocol` is `stead.oidc-proof/1`. Sign the ASCII protocol plus a zero byte
plus the canonical JSON without `signature` using standard Ed25519.
`signature` is 128 lowercase hex characters. Home uses the public key from
its own configuration, with the key ID implicit in verifier ID and revision.
Require an admitted, validated 32-byte public key and canonical signature
encoding and scalar. Bound the entire message to 2 KiB before decoding and
check cheap predicates and live challenge capacity before signature
verification. Proof life is at most 30 seconds, `issued_at_ms` can be at
most five seconds ahead of the Home clock, and expired proofs always fail.
Reject malformed or duplicate fields, unknown versions and unsupported
assurance. The proof lifetime never extends the Home challenge.

Use a separate random 32-byte tag key per Home organization at the verifier.
The tag is lowercase hex HMAC-SHA-256 over
`stead.oidc-subject/1` followed by a zero byte and the issuer and subject
encoded as UTF-8 with each byte length prefixed by a 32-bit big-endian
integer. Use the exact verified `iss` and `sub` without case changes or
Unicode normalization. Home receives the opaque tag and configured issuer ID.
For enrollment, the operator independently confirms the IdP subject for the
person and provisions its derived tag to the existing or explicitly created
principal. IdP display name, email, email domain and group claims cannot
establish a binding or grant a role. [OIDC ID-token validation](https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation)
and [claim stability](https://openid.net/specs/openid-connect-core-1_0.html#ClaimStability).

### Host test vector

Use tag key bytes `00` through `1f`, issuer `https://idp.example.test` and
subject `alice`. Set `home` to `~zod`, `origin` to
`https://home.example.test` and `verifier_revision` to `1`. Use UUIDs
`00000000-0000-4000-8000-000000000001`, `00000000-0000-4000-8000-000000000002`
and `00000000-0000-4000-8000-000000000003` for organization, verifier and issuer
respectively. Repeat `11` 32 times for the challenge and `22` 32 times for the
incarnation. Set assurance to `oidc`, issued time to `1000000` and expiration
to `1030000`. Use the Ed25519 test 1 key. [RFC 8032 §7.1](https://www.rfc-editor.org/rfc/rfc8032.html#section-7.1).

Python produced the tag and 602-byte signing input. OpenSSL 3.6.5 verified the
resulting signature and rejected separate changes to the origin, tag and
challenge. The v7 native follow-up verified the same signed bytes and rejected
separate changes to the origin and challenge using pinned Vere on an isolated
Home. The native probe exercised the signature primitive. The browser-only
sign-in flow and remaining qualification cases below are still open.
[Native evidence](PHASE5_LOCAL_20261110.md#home-v7-and-full-history-readback)

```text
Subject tag   3fd14320b0de7d6bb5f48da4c8d558ab8658c9b24a7d5a41305cdc82b346c4d8
Input SHA-256 5a8117dfc33b6fddfae133ef811116e9fec5d6f517e481440a8d767f7c57a3f9
Signature     21baf7a271d9d2c1c163f5ef35413c5c8da94c7b2b7663967d80164c119caef1671dd34df4e439dfd4819f08af10a2aca29032183ba300bf4abcf731d6009e04
```

## Enrollment, revocation and Home migration

Use an owner-authorized, compare-and-set configuration transition. A binding
has a unique ID, immutable principal owner, mechanism, verification reference,
revision, expiry and active status. Keep one active binding per principal in
the first profile. Use separate indices for Gall sender and OIDC issuer/tag.
Keep binding and subject ownership tombstones so an old external identity
cannot be silently reassigned to a different principal. Cap entries, retain
revision high-water marks and reject exhausted or inconsistent updates
atomically. Upgrade existing native bindings without changing principal IDs,
binding IDs, revisions, grants or original actor records. Prior versions with
no valid migration remain fenced. Store the new tagged registry and actor
schema in a versioned saved envelope and discard ephemeral sessions and
pending approvals on load and startup.

A verified person may move from native approval to OIDC or replace a provider
subject. Confirm control of both current and proposed identity when possible.
For lost identity, use documented organization recovery and independent
operator review before replacing it. Record who approved, when and why.
Atomically replace the active binding with a higher revision and retire the
old one. Retain the person's principal ID, current project grants and historical
authorship. Cancel live sessions, challenges, watches, cursors and pending
delivery for the retired revision. Retire unbound OIDC challenges on any binding
configuration change, so approval cannot cross an offboarding or rebind. Git
credentials, pending Git accepts,
reviews that still require current approval, and agent delegations bound to
the retired revision lose eligibility. An authorized current binding can
explicitly issue fresh credentials or reapprove eligible work through current
policy. Retain previous proposal, delegation, review, receipt and Git author
records with their original actor and revision. A new session can read
historical receipts where current grants permit. No operation reattributes
accepted work or renews an old delegation automatically.

Home removal or suspension takes effect at the next authorization decision,
including final write acceptance. Offboarding uses the Home transition as
well as removal at the IdP. Browser signout revokes the local session.
IdP-only logout does not shorten an already issued Home session in this
profile. An installation that needs provider-driven session revocation must
separately qualify [OIDC Back-Channel Logout](https://openid.net/specs/openid-connect-backchannel-1_0.html)
or an equivalent verified notification with local revocation semantics. Verifier
rotation or compromise retires the old key/configuration revision and all
sessions derived under it. Tag-key rotation and issuer changes use explicit
re-enrollment with unchanged principal IDs. Do not copy verifier keys as
part of a project replica.

During a Home move, fence both sides until the new authority and binding
registry are verified against the latest accepted checkpoint. Move eligible
private binding metadata under explicit custody approval or re-enroll
principals on the destination with their same IDs. Restore the revocation
high-water marks from a trusted source before enabling the profile. If the
latest binding state is uncertain, keep sign-in disabled until independently
reviewed re-enrollment is complete. Update the verifier's configured
Home/origin and key revision, discard prior authentication transactions,
and require fresh sign-in at the new Home. Every operation still checks the
current project's authority epoch. A replica never acts as an identity issuer.

## Verification required to enable the profile

| Boundary | Required proof |
| --- | --- |
| Browser and IdP | Two enrolled users and one outsider in separate browsers. Exercise the cross-origin form, the callback cookie, account confirmation, duplicate/mixed redirects, login CSRF, stolen-code rejection and wrong-browser consumption. Use a test IdP, and test the exact candidate provider before claiming support. |
| Verifier | Reject expired and duplicated transactions, wrong issuer/nonce/audience, key and algorithm confusion, stale assurance, provider endpoint drift and untrusted redirects. Inspect verifier logs and Home wire captures for raw provider tokens, credentials and content. |
| Native Home | Run host/native byte and signature parity vectors including zero bytes, tampering, noncanonical signatures, malformed keys and verifier/key rotation. Measure verification latency and Home responsiveness under a bounded rejected-proof load. Test wrong Home, organization, incarnation, browser and binding revision, repeated consume, account suspension during sign-in, and no post-restart replay. |
| Policy and data | Compare two users' Work and Docs permissions and receipts before and after binding change. Verify unchanged authorship and principal IDs, denied old sessions, Git credentials, pending approvals and agent delegations, and independent role enforcement on new ones. Exercise private docs, raw Eyre access, supported upgrade, stale backup rejection and fenced Home move. |

The design review covers the pinned kernel and current Stead authority
paths, plus the cited protocol standards. The enablement tests above are
future implementation gates. The standalone native synthetic pilot uses its
existing individual member ships.
