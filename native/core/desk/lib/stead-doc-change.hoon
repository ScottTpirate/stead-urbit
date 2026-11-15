::  Reserved Doc Change preparation. No Home route or saved mold uses it.
::  Commit next AND the returned record in the one product timeline, or discard
::  both. Acceptance includes the preceding native Doc save in that same result.
::  Replay must recognize that adjacent pair before applying either member.
/+  stead-codec, stead-core, stead-git, stead-team, stead-team-codec, stead-principals, stead-product-codec, stead-product-state, stead-product-work, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state
=,  stead-codec
|%
+$  state
  [db=state:stead-team product=state:stead-product-state changes=state:stead-doc-change-state]
+$  authority  ?(%live %expired %revoked %unknown)
+$  run-resolver
  ::  Home-internal exact run/attempt/pin/lease resolver. Never wire data.
  $-([output=output:stead-doc-change-state now=@ud] authority)
+$  request-key  [project=@t principal=@t request=@t]
+$  budget
  ::  Other authoritative families, excluding native, Work and Doc attempts.
  ::  Owner-ledger lookup is global by request ID, regardless of the supplied
  ::  project/principal. Home must include it in request-used.
  [ordinary=@ud request-used=$-(request-key ?)]
+$  saved  [command=@t receipt=@t event=event:stead-product-state]
+$  decision  [next=state error=@t saved=(unit saved)]
+$  result  [response=@t next=state record=(unit @t)]
++  deny-run
  |=  [output=output:stead-doc-change-state now=@ud]
  ^-  authority
  %unknown
++  request-unused
  |=  key=request-key
  ^-  ?
  |
++  no-other
  ^-  budget
  [0 request-unused]
++  field-result
  |=  [raw=@t name=@t]
  ^-  @t
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  (field p.value name)
++  current-access
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud]
  ^-  ?
  ?&  (current:stead-team db.state actor now)
      (gte (role:stead-team db.state actor project.cmd now) 2)
      (subject:stead-team db.state actor project.cmd 'work' '' work.cmd now)
      ?=(^ (current-kind:stead-product-adapters db.state catalog project.cmd principal.identity.actor now))
  ==
++  human
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team project=@t now=@ud]
  ^-  ?
  &((current:stead-team db.state actor now) =((some %person) (current-kind:stead-product-adapters db.state catalog project principal.identity.actor now)))
++  accountable
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team project=@t work=@t now=@ud]
  ^-  ?
  ?.  (human state catalog actor project now)  |
  =/  current  (~(get by works.data.db.state) [project work])
  ?~  current  |
  ?|  (gte (role:stead-team db.state actor project now) 3)
      =(principal.identity.actor (field data.u.current 'owner_principal_id'))
  ==
++  visible-target
  |=  [state=state actor=authentication:stead-team project=@t target=json now=@ud]
  ^-  ?
  ?.  ?=([%o *] target)  |
  ?.  =('document' (field p.target 'kind'))  |
  =/  collection  (field p.target 'collection_id')
  =/  box  (~(get by boxes.db.state) collection)
  ?~  box  |
  ?&  =(project project.u.box)  =('shared' visibility.u.box)
      (box-access:stead-team db.state actor project collection now)
      !(~(has in tombs.db.state) [project 'document' collection (field p.target 'document_id')])
  ==
++  selected-grant
  |=  [db=state:stead-team project=@t principal=@t now=@ud]
  ^-  (unit [id=@t grant=grant-state:stead-core])
  =/  grants  ~(tap by grants.data.db)
  |-
  ?~  grants  ~
  =/  grant  q.i.grants
  ?:  ?&  =(project project.grant)  =(principal principal.grant)
          !revoked.grant  (gth expires.grant now)
          ?|(=('contributor' role.grant) =('maintainer' role.grant))
      ==
    (some [p.i.grants grant])
  $(grants t.grants)
++  producer-authority
  |=  [state=state catalog=state:stead-principals output=output:stead-doc-change-state now=@ud runs=run-resolver]
  ^-  authority
  ::  Resolve original custody and grant, not a newly renewed session/grant.
  =/  principal  principal.identity.producer.output
  =/  kind  (native-kind:stead-principals catalog registry.db.state principal 0)
  ?~  kind  %revoked
  =/  original  (native-context:stead-team db.state ship.identity.producer.output 0)
  ?~  original  %revoked
  ?.  ?&  =(identity.producer.output identity.u.original)
          =(home.producer.output home.u.original)
          =(organization.producer.output organization.u.original)
          =(team.producer.output team.u.original)
          =(runtime.producer.output runtime.u.original)
      ==
    %revoked
  =/  grant  (~(get by grants.data.db.state) grant-id.output)
  ?~  grant  %revoked
  ?.  &(=(u.grant grant.output) !revoked.u.grant)  %revoked
  ?:  (closed:stead-core data.db.state project.output)  %revoked
  =/  run-authority=authority
    ?:  =('' run.output)  ?:(=(%person u.kind) %live %revoked)
    (runs output now)
  ?:  ?|  =(%revoked run-authority)  =(%unknown run-authority)
      ==
    run-authority
  ?:  ?|  (lte expires.producer.output now)
          (lte expires.identity.producer.output now)
          (lte expires.grant.output now)
      ==
    %expired
  run-authority
++  exact-contract
  |=  [state=state output=output:stead-doc-change-state]
  ^-  ?
  =/  key  [project.output work.output]
  =/  current  (~(get by works.data.db.state) key)
  =/  metadata  (~(get by works.product.state) key)
  ?.  &(?=(^ current) ?=(^ metadata))  |
  =/  outcomes  (object-field:stead-product-codec data.u.current 'required_outcomes')
  ?&  =(execution.output execution-revision.u.metadata)
      =(execution-digest.output execution-digest.u.metadata)
      =(execution-digest.u.metadata (contract-digest:stead-product-state key execution-revision.u.metadata data.u.current))
      =((some target.output) (~(get by outcomes) outcome.output))
      =(epoch.output epoch:(~(got by projects.data.db.state) project.output))
  ==
++  canonical-markdown
  |=  [target=json markdown=@t]
  ^-  ?
  ?.  ?=([%o *] target)  |
  =/  prefix  (header:stead-team (field p.target 'document_id') 'published')
  &((prose markdown 32.768) =(prefix (cut 3 [0 (met 3 prefix)] markdown)))
++  body-budget
  |=  state=state
  ^-  ?
  ?&  (lte (add object-bytes.data.db.state body-bytes.changes.state) 8.388.608)
      (lte (add (lent ~(tap by objects.data.db.state)) (lent ~(tap by bodies.changes.state))) 12.288)
      (lte (lent ~(tap by heads.changes.state)) 2.048)
      (lte (lent ~(tap by results.changes.state)) 4.096)
  ==
++  uint64
  |=  value=@ud
  ^-  ?
  (lte value 18.446.744.073.709.551.615)
++  scoped-grant-key
  |=  [project=@t key=@t]
  ^-  ?
  ?&  =(73 (met 3 key))
      =/  id  (cut 3 [37 36] key)
      &((uuid id) =(key (scope-key:stead-core project id)))
  ==
++  authentication-bounded
  |=  actor=authentication:stead-team
  ^-  ?
  ?&  (lte (met 0 ship.identity.actor) 128)  (lte (met 0 home.actor) 128)
      (uuid principal.identity.actor)  (uuid binding.identity.actor)
      (uuid organization.actor)  (uuid team.actor)
      (uint64 revision.identity.actor)  (uint64 expires.identity.actor)  (uint64 expires.actor)
      (lte (met 3 method.actor) 64)  (lte (met 3 strength.actor) 64)
      (lte (met 3 audit.actor) 64)  (lte (met 3 runtime.actor) 64)
      =(actor (decode-authentication:stead-team (authentication-json:stead-team actor)))
  ==
++  evidence-bounded
  |=  evidence=(unit evidence:stead-doc-change-state)
  ^-  ?
  ?~  evidence  &
  ?&  (authentication-bounded actor.u.evidence)  (uuid request.u.evidence)
      (gth recorded-at.u.evidence 0)  (uint64 recorded-at.u.evidence)
      (prose note.u.evidence 2.048)  (opaque:stead-team-codec digest.u.evidence)
  ==
++  changes-bounded
  ::  Public early-admission gate. The integrator first applies its shared noun
  ::  and legacy-core bounds, then this gate before any semantic history replay.
  ::  This validates sizes and content keys; full regeneration proves authority.
  |=  state=state
  ^-  ?
  =/  checked  (mule |.((changes-bounded-check state)))
  ?:  ?=(%| -.checked)  |
  p.checked
++  changes-bounded-check
  |=  state=state
  ^-  ?
  ?.  ?&  (body-budget state)
          (lte (lent ~(tap by bodies.changes.state)) 4.096)
          (lte (lent ~(tap by attempts.changes.state)) 4.096)
      ==
    |
  =/  bytes=@ud
    (roll ~(tap by bodies.changes.state) |=([pair=[@t @t] sum=@ud] (add sum (met 3 +.pair))))
  ?&  =(bytes body-bytes.changes.state)
      %+  levy  ~(tap by bodies.changes.state)
      |=  [sha=@t body=@t]
      ?&  (opaque:stead-team-codec sha)  (prose body 32.768)
          =(sha (markdown-sha256:stead-product-adapters [(met 3 body) body]))
      ==
      %+  levy  ~(tap by heads.changes.state)
      |=  [key=key:stead-doc-change-state head=head:stead-doc-change-state]
      ?&  (uuid project.key)  (uuid change.key)  (uuid work.head)  (uuid producer.head)
          (gth revision.head 0)  (uint64 revision.head)
          (gth output-revision.head 0)  (uint64 output-revision.head)
          (opaque:stead-team-codec output-digest.head)
          (evidence-bounded approval.head)  (evidence-bounded adoption.head)
          ?~  acceptance.head  &
          =/  saved  u.acceptance.head
          ?&  (authentication-bounded actor.saved)  (uuid request.saved)
              (gth recorded-at.saved 0)  (uint64 recorded-at.saved)
              (gth revision.saved 0)  (uint64 revision.saved)
              (gth (met 3 receipt.saved) 0)  (lte (met 3 receipt.saved) 8.192)
              (opaque:stead-team-codec event-digest.saved)
          ==
      ==
      %+  levy  ~(tap by results.changes.state)
      |=  [key=result-key:stead-doc-change-state output=output:stead-doc-change-state]
      ?&  (uuid project.key)  (uuid change.key)  (gth revision.key 0)  (uint64 revision.key)
          =([project.key change.key revision.key] [project.output change.output revision.output])
          (uuid work.output)  (uuid outcome.output)  (scoped-grant-key project.output grant-id.output)
          (gth execution.output 0)  (uint64 execution.output)
          (gth epoch.output 0)  (uint64 epoch.output)
          (opaque:stead-team-codec execution-digest.output)
          (authentication-bounded producer.output)
          (outcome:stead-product-codec project.output work.output target.output)
          ?>  ?=([%o *] target.output)
          =('document' (field p.target.output 'kind'))
          =(project.output project.grant.output)
          =(principal.identity.producer.output principal.grant.output)
          ?|(=('contributor' role.grant.output) =('maintainer' role.grant.output))
          !revoked.grant.output  (gth expires.grant.output 0)  (uint64 expires.grant.output)
          (uint64 attempt.output)
          ?:(=('' run.output) =(0 attempt.output) &((uuid run.output) (gth attempt.output 0)))
          (opaque:stead-team-codec markdown-sha256.output)
          (~(has by bodies.changes.state) markdown-sha256.output)
          (comment-body:stead-team-codec summary.output)
          (gth submitted-at.output 0)  (uint64 submitted-at.output)
          (opaque:stead-team-codec digest.output)
          =(digest.output (output-digest:stead-doc-change-state output))
      ==
      %+  levy  ~(tap by attempts.changes.state)
      |=  [key=request-key item=attempt:stead-doc-change-state]
      ?&  (uuid project.key)  (uuid principal.key)  (uuid request.key)
          (uuid work.item)  (uuid change.item)  (opaque:stead-team-codec digest.item)
          (lte (met 3 operation.item) 64)
          (gth (met 3 command.item) 0)  (lte (met 3 command.item) 65.536)
          (gth (met 3 receipt.item) 0)  (lte (met 3 receipt.item) 8.192)
      ==
  ==
++  put-head
  |=  [state=state cmd=command:stead-doc-change-codec head=head:stead-doc-change-state]
  ^-  state
  state(changes changes.state(heads (~(put by heads.changes.state) [project.cmd change.cmd] head)))
++  deny
  |=  [state=state cmd=command:stead-doc-change-codec error=@t]
  ^-  result
  :*  (canonical (object ~[['protocol' 'stead.doc-change-receipt/1'] ['status' 'rejected'] ['request_id' request.cmd] ['canonical_sha256' digest.cmd] ['error' error]]))
      state  ~
  ==
++  prepare
  |=  [chosen=decision actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud]
  ^-  result
  =/  next  next.chosen
  =/  head  (~(get by heads.changes.next) [project.cmd change.cmd])
  =/  response
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.doc-change-receipt/1']  ['status' ?:(=('' error.chosen) 'accepted' 'rejected')]
        ['request_id' request.cmd]  ['canonical_sha256' digest.cmd]
        ['project_id' project.cmd]  ['work_id' work.cmd]  ['change_id' change.cmd]
        ['authority_epoch' (decimal epoch.cmd)]  ['operation' operation.cmd]
        ['expected_revision' (decimal expected.cmd)]
        ['resulting_revision' (decimal ?~(head 0 revision.u.head))]
        ['result_revision' (decimal ?~(head 0 output-revision.u.head))]
        ['result_digest' ?~(head '' output-digest.u.head)]
        ['change_status' ?~(head '' (scot %tas status.u.head))]
        ['recorded_at_ms' (decimal now)]  ['error' error.chosen]
    ==
  ?>  (lte (met 3 response) 8.192)
  =/  output
    ?~  head  ''
    (output-bytes:stead-doc-change-state (~(got by results.changes.next) [project.cmd change.cmd output-revision.u.head]))
  =/  record
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.doc-change-journal/1']
        ['canonical_command' canonical-bytes.cmd]  ['receipt' response]
        ['authentication_context' (authentication-json:stead-team actor)]  ['result' output]
        ['approval' ?~(head '' (evidence-bytes:stead-doc-change-state approval.u.head))]
        ['adoption' ?~(head '' (evidence-bytes:stead-doc-change-state adoption.u.head))]
        ['save_command' ?~(saved.chosen '' command.u.saved.chosen)]
        ['save_receipt' ?~(saved.chosen '' receipt.u.saved.chosen)]
        ['save_event' ?~(saved.chosen '' bytes.event.u.saved.chosen)]
        ['save_event_digest' ?~(saved.chosen '' digest.event.u.saved.chosen)]
    ==
  ::  Preflight the exact outer timeline encoding without creating another
  ::  journal. The Home wrapper must append this exact body or discard next.
  =/  boundary  (need migration.product.next)
  =/  previous  ?~(events.product.next fingerprint.boundary digest.i.events.product.next)
  =/  envelope
    (canonical (object ~[['protocol' 'stead.product-event/1'] ['sequence' (decimal +((lent events.product.next)))] ['previous_digest' previous] ['family' 'stead.doc-change/1'] ['body' record]]))
  ?>  &((lth (lent events.product.next) 6.144) (lte (met 3 envelope) 262.144))
  =/  stored=attempt:stead-doc-change-state  [digest.cmd work.cmd change.cmd operation.cmd canonical-bytes.cmd response]
  =/  changes  changes.next(attempts (~(put by attempts.changes.next) [project.cmd principal.identity.actor request.cmd] stored))
  [response next(changes changes) (some record)]
++  recorded-rejection
  |=  [state=state actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud error=@t]
  ^-  result
  =/  result  (mule |.((prepare [state error ~] actor cmd now)))
  ?:  ?=(%| -.result)  (deny state cmd 'capacity_exceeded')
  p.result
++  occupied
  |=  [state=state key=request-key other=budget]
  ^-  ?
  ?|  (~(has by receipts.data.db.state) key)
      (~(has by attempts.product.state) key)
      (~(has by attempts.changes.state) key)
      (request-used.other key)
  ==
++  ordinary-count
  |=  [state=state project=@t other=budget]
  ^-  @ud
  (add ordinary.other (add (event-count:stead-team db.state project |) (add (lent ~(tap by attempts.product.state)) (lent ~(tap by attempts.changes.state)))))
++  apply
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud runs=run-resolver other=budget]
  ^-  result
  ?.  (current-access state catalog actor cmd now)  (deny state cmd 'denied_or_not_found')
  ?~  migration.product.state  (deny state cmd 'migration_required')
  ?.  &((gth now 0) (lte now 18.446.744.073.709.551.615))  (deny state cmd 'invalid_time')
  =/  head  (~(get by heads.changes.state) [project.cmd change.cmd])
  ?^  head
    ?.  =(work.cmd work.u.head)  (deny state cmd 'denied_or_not_found')
    =/  output  (~(got by results.changes.state) [project.cmd change.cmd output-revision.u.head])
    ?.  (visible-target state actor project.cmd target.output now)  (deny state cmd 'denied_or_not_found')
    (apply-current state catalog actor cmd now runs other head)
  ?.  =('change.submit' operation.cmd)  (deny state cmd 'denied_or_not_found')
  ?.  (visible-target state actor project.cmd (~(got by payload.cmd) 'target') now)  (deny state cmd 'denied_or_not_found')
  (apply-current state catalog actor cmd now runs other head)
++  apply-current
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud runs=run-resolver other=budget head=(unit head:stead-doc-change-state)]
  ^-  result
  =/  key=request-key  [project.cmd principal.identity.actor request.cmd]
  =/  epoch  epoch:(~(got by projects.data.db.state) project.cmd)
  =/  previous  (~(get by attempts.changes.state) key)
  ?^  previous
    ?.  =(epoch.cmd epoch)  (deny state cmd 'authority_epoch_conflict')
    ?.  =(digest.cmd digest.u.previous)  (deny state cmd 'request_id_reuse')
    [receipt.u.previous state ~]
  ?:  (occupied state key other)  (deny state cmd 'request_id_reuse')
  ?:  (gte (ordinary-count state project.cmd other) 4.096)  (deny state cmd 'capacity_exceeded')
  ?.  =(epoch.cmd epoch)  (recorded-rejection state actor cmd now 'authority_epoch_conflict')
  ?.  =(expected.cmd ?~(head 0 revision.u.head))  (recorded-rejection state actor cmd now 'revision_conflict')
  ?:  ?~(head | =(revision.u.head 18.446.744.073.709.551.615))
    (recorded-rejection state actor cmd now 'capacity_exceeded')
  =/  attempted
    %-  mule
    |.
    =/  chosen
      ?:  =('change.submit' operation.cmd)  (submit state catalog actor cmd now runs head)
      ?>  ?=(^ head)
      (review state catalog actor cmd now runs other u.head)
    (prepare chosen actor cmd now)
  ?:  ?=(%| -.attempted)  (recorded-rejection state actor cmd now 'capacity_exceeded')
  p.attempted
++  submit
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud runs=run-resolver head=(unit head:stead-doc-change-state)]
  ^-  decision
  ?^  head
    ?.  =(principal.identity.actor producer.u.head)  [state 'producer_mismatch' ~]
    ?:  ?|  =(%accepted status.u.head)  =(%rejected status.u.head)  =(%quarantined status.u.head)
        ==
      [state 'change_closed' ~]
    (submit-result state catalog actor cmd now runs head)
  (submit-result state catalog actor cmd now runs head)
++  submit-result
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud runs=run-resolver head=(unit head:stead-doc-change-state)]
  ^-  decision
  =/  grant  (selected-grant db.state project.cmd principal.identity.actor now)
  ?~  grant  [state 'producer_unavailable' ~]
  =/  target  (~(got by payload.cmd) 'target')
  =/  markdown  (field payload.cmd 'markdown')
  ?.  (canonical-markdown target markdown)  [state 'invalid_document' ~]
  =/  sha  (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])
  =/  revision  ?~(head 1 +(output-revision.u.head))
  ?>  (lte revision 18.446.744.073.709.551.615)
  =/  output=output:stead-doc-change-state
    :*  project.cmd  work.cmd  change.cmd  revision  (field payload.cmd 'outcome_id')
        target  (uint (field payload.cmd 'execution_contract_revision'))
        (field payload.cmd 'execution_contract_digest')  epoch.cmd
        actor  id.u.grant  grant.u.grant  (field payload.cmd 'run_id')
        (uint (field payload.cmd 'attempt'))  sha  (field payload.cmd 'summary')  now  ''
    ==
  =.  digest.output  (output-digest:stead-doc-change-state output)
  ?.  (exact-contract state output)  [state 'execution_contract_conflict' ~]
  ?.  (current-target:stead-product-adapters db.state actor project.cmd work.cmd principal.identity.actor target now)
    [state 'target_base_conflict' ~]
  ?.  =(%live (producer-authority state catalog output now runs))  [state 'producer_unavailable' ~]
  =/  body  (~(get by bodies.changes.state) sha)
  ?.  ?~(body & =(u.body markdown))  [state 'content_collision' ~]
  =/  changes  changes.state
  =.  changes
    changes(bodies (~(put by bodies.changes) sha markdown), body-bytes (add body-bytes.changes ?~(body (met 3 markdown) 0)))
  =.  results.changes  (~(put by results.changes) [project.cmd change.cmd revision] output)
  =/  next=state  state(changes changes)
  =/  new=head:stead-doc-change-state
    [work.cmd principal.identity.actor ?~(head 1 +(revision.u.head)) %submitted revision digest.output ~ ~ ~]
  =.  next  (put-head next cmd new)
  ?.  (body-budget next)  [state 'capacity_exceeded' ~]
  [next '' ~]
++  evidence-current
  |=  [state=state catalog=state:stead-principals evidence=(unit evidence:stead-doc-change-state) output=output:stead-doc-change-state now=@ud require-accountable=?]
  ^-  ?
  ?~  evidence  |
  ?&  =(digest.output digest.u.evidence)
      !=(principal.identity.producer.output principal.identity.actor.u.evidence)
      (human state catalog actor.u.evidence project.output now)
      (subject:stead-team db.state actor.u.evidence project.output 'work' '' work.output now)
      ?:  require-accountable
        (accountable state catalog actor.u.evidence project.output work.output now)
      &
  ==
++  review
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud runs=run-resolver other=budget head=head:stead-doc-change-state]
  ^-  decision
  ?.  ?&  =(output-revision.head (uint (field payload.cmd 'result_revision')))
          =(output-digest.head (field payload.cmd 'result_digest'))
      ==
    [state 'result_conflict' ~]
  =/  output  (~(got by results.changes.state) [project.cmd change.cmd output-revision.head])
  ?.  &(=(digest.output output-digest.head) =(digest.output (output-digest:stead-doc-change-state output)))
    [state 'invalid_result' ~]
  ?.  (human state catalog actor project.cmd now)  [state 'human_review_required' ~]
  ?:  =('change.quarantine' operation.cmd)
    ?.  (accountable state catalog actor project.cmd work.cmd now)  [state 'accountable_human_required' ~]
    ::  Already accepted output stays an immutable historical business outcome;
    ::  later correction needs a new Change, never a retroactive Doc rollback.
    ?:  ?|  =(%accepted status.head)  =(%rejected status.head)  =(%quarantined status.head)
        ==
      [state 'change_closed' ~]
    [(put-head state cmd head(revision +(revision.head), status %quarantined, approval ~, adoption ~)) '' ~]
  ?:  ?|  =(%accepted status.head)  =(%rejected status.head)  =(%quarantined status.head)
      ==
    [state 'change_closed' ~]
  ?.  (exact-contract state output)  [state 'execution_contract_conflict' ~]
  ?.  (current-target:stead-product-adapters db.state actor project.cmd work.cmd principal.identity.actor target.output now)
    [state 'target_base_conflict' ~]
  =/  authority  (producer-authority state catalog output now runs)
  ?:  ?|  =(%revoked authority)  =(%unknown authority)
      ==
    ::  A rejected publication/review can fence the retained result. This
    ::  security transition and its rejection receipt are recorded together.
    [(put-head state cmd head(revision +(revision.head), status %quarantined, approval ~, adoption ~)) 'producer_quarantined' ~]
  =/  evidence=evidence:stead-doc-change-state
    [actor request.cmd now (field payload.cmd 'note') digest.output]
  ?:  =('change.adopt' operation.cmd)
    ?.  =(%expired authority)  [state 'adoption_requires_expiry' ~]
    ?.  (accountable state catalog actor project.cmd work.cmd now)  [state 'accountable_human_required' ~]
    ?:  =(principal.identity.actor producer.head)  [state 'independent_adopter_required' ~]
    [(put-head state cmd head(revision +(revision.head), adoption (some evidence))) '' ~]
  ?:  =('change.accept' operation.cmd)
    (accept-result state catalog actor cmd now other head output authority)
  ?:  =(principal.identity.actor producer.head)  [state 'self_review_denied' ~]
  ?:  =('change.approve' operation.cmd)
    [(put-head state cmd head(revision +(revision.head), status %approved, approval (some evidence))) '' ~]
  ?:  =('change.request-changes' operation.cmd)
    [(put-head state cmd head(revision +(revision.head), status %changes-requested, approval ~)) '' ~]
  ?:  =('change.reject' operation.cmd)
    [(put-head state cmd head(revision +(revision.head), status %rejected, approval ~, adoption ~)) '' ~]
  [state 'invalid_command' ~]
++  save-command
  |=  [cmd=command:stead-doc-change-codec output=output:stead-doc-change-state markdown=@t]
  ^-  command:stead-codec
  ?>  ?=([%o *] target.output)
  =/  fields
    %-  object
    :~  ['protocol' 'stead.command/3']  ['request_id' (internal-request:stead-doc-change-state cmd)]
        ['project_id' project.cmd]  ['resource_id' (field p.target.output 'document_id')]
        ['authority_epoch' (decimal epoch.cmd)]
        ['expected_revision' (field p.target.output 'expected_revision')]
        ['operation' 'document.save']
    ==
  ?>  ?=([%o *] fields)
  =/  payload  (object ~[['container_id' (field p.target.output 'collection_id')] ['markdown' markdown]])
  (decode:stead-team-codec (canonical [%o (~(put by p.fields) 'payload' payload)]))
++  accept-result
  |=  [state=state catalog=state:stead-principals actor=authentication:stead-team cmd=command:stead-doc-change-codec now=@ud other=budget head=head:stead-doc-change-state output=output:stead-doc-change-state authority=authority]
  ^-  decision
  ?.  (accountable state catalog actor project.cmd work.cmd now)  [state 'accountable_human_required' ~]
  ?.  &(?=(%approved status.head) (evidence-current state catalog approval.head output now |))
    [state 'independent_review_required' ~]
  ?.  ?|  =(%live authority)
          &(?=(%expired authority) (evidence-current state catalog adoption.head output now &))
      ==
    [state 'explicit_adoption_required' ~]
  =/  markdown  (~(got by bodies.changes.state) markdown-sha256.output)
  ?>  ?=([%o *] target.output)
  ?.  ?&  (canonical-markdown target.output markdown)
          =(markdown-sha256.output (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown]))
      ==
    [state 'invalid_document' ~]
  =/  save  (save-command cmd output markdown)
  ?:  (occupied state [project.cmd principal.identity.actor request.save] other)
    [state 'internal_request_id_collision' ~]
  ?.  &((lte (add 2 (ordinary-count state project.cmd other)) 4.096) (lte (add 2 (lent events.product.state)) 6.144))
    [state 'capacity_exceeded' ~]
  =/  saved  (apply-legacy:stead-product-work db.state product.state actor save now)
  ?.  =('accepted' (field-result response.saved 'status'))  [state 'document_save_rejected' ~]
  ?>  ?=(^ events.product.saved)
  ?>  &(=(events.product.state t.events.product.saved) =(%v3 family.i.events.product.saved))
  =/  next  state(db db.saved, product product.saved)
  ?.  (body-budget next)  [state 'capacity_exceeded' ~]
  =/  evidence=acceptance:stead-doc-change-state
    [actor request.cmd now +((uint (field p.target.output 'expected_revision'))) response.saved digest.i.events.product.saved]
  =/  next  (put-head next cmd head(revision +(revision.head), status %accepted, acceptance (some evidence)))
  [next '' (some [canonical-bytes.save response.saved i.events.product.saved])]
--
