::  Reserved Doc proposals. These maps are not a second event journal.
::  A Home wrapper commits them with the one ordered product timeline.
/+  stead-codec, stead-core, stead-team, stead-doc-change-codec
=,  stead-codec
|%
+$  key  [project=@t change=@t]
+$  result-key  [project=@t change=@t revision=@ud]
+$  evidence
  [actor=authentication:stead-team request=@t recorded-at=@ud note=@t digest=@t]
+$  output
  $:  project=@t  work=@t  change=@t  revision=@ud  outcome=@t
      target=json  execution=@ud  execution-digest=@t  epoch=@ud
      ::  grant-id is the exact project/UUID scoped map key, not a local UUID.
      producer=authentication:stead-team  grant-id=@t  grant=grant-state:stead-core
      run=@t  attempt=@ud  markdown-sha256=@t  summary=@t
      submitted-at=@ud  digest=@t
  ==
+$  acceptance
  [actor=authentication:stead-team request=@t recorded-at=@ud revision=@ud receipt=@t event-digest=@t]
+$  head
  $:  work=@t  producer=@t  revision=@ud
      status=?(%submitted %changes-requested %approved %accepted %rejected %quarantined)
      output-revision=@ud  output-digest=@t
      approval=(unit evidence)  adoption=(unit evidence)  acceptance=(unit acceptance)
  ==
+$  attempt
  [digest=@t work=@t change=@t operation=@t command=@t receipt=@t]
+$  state
  $:  heads=(map key head)  results=(map result-key output)
      bodies=(map @t @t)  body-bytes=@ud
      attempts=(map [project=@t principal=@t request=@t] attempt)
  ==
++  empty  *state
++  grant-json
  |=  [id=@t grant=grant-state:stead-core]
  ^-  @t
  %-  canonical
  (object ~[['grant_key' id] ['project_id' project.grant] ['principal_id' principal.grant] ['role' role.grant] ['expires_at_ms' (decimal expires.grant)] ['revoked' ?:(revoked.grant 'yes' 'no')]])
++  output-bytes
  |=  output=output
  ^-  @t
  =/  fields
    %-  object
    :~  ['project_id' project.output]  ['work_id' work.output]  ['change_id' change.output]
        ['result_revision' (decimal revision.output)]  ['outcome_id' outcome.output]
        ['execution_contract_revision' (decimal execution.output)]
        ['execution_contract_digest' execution-digest.output]  ['authority_epoch' (decimal epoch.output)]
        ['producer_authentication' (authentication-json:stead-team producer.output)]
        ['producer_grant' (grant-json grant-id.output grant.output)]
        ['run_id' run.output]  ['attempt' (decimal attempt.output)]
        ['markdown_sha256' markdown-sha256.output]  ['summary' summary.output]
        ['submitted_at_ms' (decimal submitted-at.output)]
    ==
  ?>  ?=([%o *] fields)
  (canonical [%o (~(put by p.fields) 'target' target.output)])
++  output-digest
  |=  output=output
  ^-  @t
  (hash 'stead.doc-result/1' (output-bytes output))
++  evidence-bytes
  |=  evidence=(unit evidence)
  ^-  @t
  ?~  evidence  ''
  %-  canonical
  (object ~[['authentication_context' (authentication-json:stead-team actor.u.evidence)] ['request_id' request.u.evidence] ['recorded_at_ms' (decimal recorded-at.u.evidence)] ['note' note.u.evidence] ['result_digest' digest.u.evidence]])
++  internal-request
  ::  Preserve the accept request's UUIDv7 time prefix. The remaining bytes
  ::  are deterministic and domain-separated; no collision retry is allowed.
  |=  cmd=command:stead-doc-change-codec
  ^-  @t
  =/  seed
    %-  hash
    :-  'stead.doc-change-save-request/1'
    %-  canonical
    (object ~[['project_id' project.cmd] ['work_id' work.cmd] ['change_id' change.cmd] ['request_id' request.cmd] ['result_revision' (field payload.cmd 'result_revision')] ['result_digest' (field payload.cmd 'result_digest')]])
  =/  id
    (rap 3 ~[(cut 3 [0 14] request.cmd) '7' (cut 3 [0 3] seed) '-8' (cut 3 [3 3] seed) '-' (cut 3 [6 12] seed)])
  ?>  (uuid id)
  id
--
