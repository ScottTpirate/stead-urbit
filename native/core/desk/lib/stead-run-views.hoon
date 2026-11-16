::  Reserved native run reads. Home must admit bounded state and reconstruct
::  its history first. This is neither a verifier nor a dispatch authority.
::  Lease observation is separate from durable phase and current Work pins.
/+  stead-codec, stead-core, stead-team, stead-team-codec, stead-session, stead-views, stead-principals, stead-actor, stead-run-state, stead-run, stead-run-adapters, stead-run-query
=,  stead-codec
|%
+$  result  [response=@t next=state:stead-views]
++  error
  |=  [query=query:stead-run-query reason=@t]
  ^-  @t
  (canonical (object ~[['protocol' 'stead.run-query-result/1'] ['status' 'rejected'] ['request_id' request.query] ['error' reason]]))
++  member
  |=  [state=snapshot:stead-run-adapters actor=authentication:stead-team query=query:stead-run-query now=@ud]
  ^-  ?
  ?&  ?=(^ (verify-native:stead-actor db.state catalog.state actor now))
      (gth (role:stead-team db.state actor project.query now) 0)
      (subject:stead-team db.state actor project.query 'work' '' work.query now)
      =/  kind  (native-kind:stead-principals catalog.state registry.db.state principal.identity.actor now)
      ?~(kind | ?=(?(%person %agent) u.kind))
  ==
++  display
  |=  [catalog=state:stead-principals principal=@t]
  ^-  @t
  =/  found  (~(get by principals.catalog) principal)
  ?~  found  ''
  ?>  ?|(=('' display.u.found) (title display.u.found))
  display.u.found
++  lease
  |=  [runs=state:stead-run-state book=live:stead-run-state key=run-key:stead-run-state row=head:stead-run-state now=@ud]
  ^-  [state=@t until=@ud]
  ?:  =(0 attempt.row)  ['none' 0]
  =/  attempt  (~(got by attempts.runs) [key attempt.row])
  ?:  ?=(?(%submitted %failed %canceled) phase.row)  ['terminal' until.attempt]
  =/  current  (~(get by leases.book) key)
  ?~  current  ['unknown-book' until.attempt]
  ?.  &(=(attempt.row attempt.u.current) =(incarnation.book incarnation.u.current))
    ['unknown-book' until.attempt]
  ?:  (lte until.attempt now)  ['expired' until.attempt]
  ?.  &((lte heartbeat.attempt now) ?=(?(%running %waiting) disposition.attempt))
    ['unknown-book' until.attempt]
  ['live' until.attempt]
++  attempt-view
  |=  [catalog=state:stead-principals runs=state:stead-run-state key=run-key:stead-run-state number=@ud]
  ^-  @t
  ?:  =(0 number)  ''
  =/  row  (~(got by attempts.runs) [key number])
  (canonical (object ~[['attempt' (decimal number)] ['principal_id' principal.row] ['display_name' (display catalog principal.row)] ['started_at_ms' (decimal started.row)] ['heartbeat_at_ms' (decimal heartbeat.row)] ['lease_until_ms' (decimal until.row)] ['disposition' (scot %tas disposition.row)]]))
++  question-view
  |=  [catalog=state:stead-principals runs=state:stead-run-state key=run-key:stead-run-state sequence=@ud]
  ^-  @t
  ?:  =(0 sequence)  ''
  =/  row  (~(got by questions.runs) [key sequence])
  ?>  (prose text.row 2.048)
  =/  answer
    ?~  answer.row  ''
    ?>  (prose text.u.answer.row 2.048)
    (canonical (object ~[['text' text.u.answer.row] ['principal_id' principal.u.answer.row] ['display_name' (display catalog principal.u.answer.row)] ['recorded_at_ms' (decimal at.u.answer.row)]]))
  (canonical (object ~[['sequence' (decimal sequence)] ['text' text.row] ['principal_id' principal.row] ['display_name' (display catalog principal.row)] ['recorded_at_ms' (decimal at.row)] ['answer' answer]]))
++  metadata
  |=  [state=snapshot:stead-run-adapters runs=state:stead-run-state book=live:stead-run-state key=run-key:stead-run-state row=head:stead-run-state full=? now=@ud]
  ^-  object-map
  =/  item  contract.row
  ?>  &(=(project.key project.item) (lte attempt.row 3) (lte question.row 4.096))
  ?>  =(digest.row (hash 'stead.run-contract/1' (contract-bytes:stead-run-state item)))
  ?>  ?~(result.row !?=(%submitted phase.row) &(?=(%submitted phase.row) (result-valid:stead-run-state u.result.row)))
  =/  observed  (lease runs book key row now)
  =/  reference
    ?~  result.row  ''
    ?>  &(=(%submitted phase.row) (result-valid:stead-run-state u.result.row))
    (result-bytes:stead-run-state u.result.row)
  ::  Exactly19 preview fields; no context, grants, audits or provider data.
  =/  fields
    %-  fields:stead-views
    :~  ['kind' 'run']  ['project_id' project.key]  ['work_id' work.item]  ['run_id' run.key]
        ['run_revision' (decimal revision.row)]  ['phase' (scot %tas phase.row)]
        ['issued_at_ms' (decimal issued.row)]  ['deadline_ms' (decimal deadline.item)]
        ['requester_principal_id' requester.item]  ['requester_display_name' (display catalog.state requester.item)]
        ['owner_principal_id' owner.item]  ['owner_display_name' (display catalog.state owner.item)]
        ['worker_principal_id' worker.item]  ['worker_display_name' (display catalog.state worker.item)]
        ['current_attempt' (decimal attempt.row)]  ['question_sequence' (decimal question.row)]
        ['lease_state' state.observed]  ['lease_until_ms' (decimal until.observed)]  ['result' reference]
    ==
  ?.  full  fields
  =/  gates  (current:stead-run-adapters state runs book key)
  =/  versions
    (canonical (object ~[['definition_id' definition.item] ['definition_revision' (decimal definition-revision.item)] ['runtime_id' runtime.item] ['runtime_revision' (decimal runtime-revision.item)]]))
  ::  Exactly25 detail fields. execution_current is advisory pin freshness,
  ::  never permission to dispatch, renew, resume, approve or accept anything.
  %-  ~(uni by fields)
  %-  fields:stead-views
  :~  ['execution_contract_revision' (decimal execution-revision.item)]
      ['execution_contract_digest' execution-digest.item]  ['agent_version' versions]
      ['execution_current' ?:((pins.gates item %execute now) 'yes' 'no')]
      ['current_attempt_detail' (attempt-view catalog.state runs key attempt.row)]
      ['latest_question' (question-view catalog.state runs key question.row)]
  ==
++  rows
  |=  [state=snapshot:stead-run-adapters runs=state:stead-run-state book=live:stead-run-state actor=authentication:stead-team query=query:stead-run-query now=@ud]
  ^-  (unit (list row:stead-views))
  ?>  (lte (lent ~(tap by heads.runs)) 512)
  =/  items
    %+  skim  ~(tap by heads.runs)
    |=  [key=run-key:stead-run-state row=head:stead-run-state]
    =(project.query project.key)
  ?>  (lte (lent items) 32)
  =/  exact  =('run' kind.query)
  =/  found=(list row:stead-views)  ~
  |-
  ?~  items
    ?:  &(exact ?=(~ found))  ~
    (some (sort found |=([a=row:stead-views b=row:stead-views] (aor id.a id.b))))
  =/  key  p.i.items
  =/  row  q.i.items
  ?.  &(=(work.query work.contract.row) ?|(!exact =(run.query run.key)))  $(items t.items)
  =/  gates  (current:stead-run-adapters state runs book key)
  ?.  ?&  ?=(^ (member.gates [%native actor] contract.row now))
          (policy.gates [%native actor] contract.row %read now)
          (pins.gates contract.row %read now)
      ==
    $(items t.items)
  $(items t.items, found [[run.key (metadata state runs book key row exact now)] found])
++  execute
  |=  [state=snapshot:stead-run-adapters runs=state:stead-run-state book=live:stead-run-state prior=state:stead-views actor=authentication:stead-team query=query:stead-run-query now=@ud entropy=@]
  ^-  result
  ?.  (valid:stead-run-query query)  [(error query 'invalid_request') prior]
  ?.  (member state actor query now)  [(error query 'denied_or_not_found') prior]
  ?~  migration.product.state  [(error query 'migration_required') prior]
  =/  attempted  (mule |.((rows state runs book actor query now)))
  ?:  ?=(%| -.attempted)  [(error query 'invalid_product_state') prior]
  =/  found  p.attempted
  ?~  found  [(error query 'denied_or_not_found') prior]
  =/  all  u.found
  =/  rank  (role:stead-team db.state actor project.query now)
  =/  epoch  epoch:(~(got by projects.data.db.state) project.query)
  =/  filter  (bytes:stead-run-query query(request '', cursor ''))
  =/  generation  (hash 'stead.run-view-generation/1' (bytes-hex (jam [actor filter rank epoch all])))
  =/  next=state:stead-views  prior(cursors (malt (skim ~(tap by cursors.prior) |=([key=@t row=cursor-record:stead-views] (gth expires.row now)))))
  =/  continuation=(unit cursor-record:stead-views)  (~(get by cursors.next) cursor.query)
  ?:  &(!=('' cursor.query) ?=(~ continuation))  [(error query 'stale_cursor') prior]
  ?.  ?~  continuation  &
      ?&  =('run-query' purpose.u.continuation)  =(actor actor.u.continuation)
          =(filter owner.u.continuation)  =(generation generation.u.continuation)
          =(rank rank.u.continuation)  =(epoch epoch.u.continuation)
      ==
    [(error query 'stale_cursor') prior]
  =/  offset  ?~(continuation 0 offset.u.continuation)
  ?:  (gth offset (lent all))  [(error query 'stale_cursor') prior]
  =.  cursors.next  (~(del by cursors.next) cursor.query)
  =/  remaining  (slag offset all)
  =/  page  (scag 20 remaining)
  =/  more  (gth (lent remaining) 20)
  =?  cursors.next  &(more =('' cursor.query))
    (malt (skip ~(tap by cursors.next) |=([key=@t row=cursor-record:stead-views] &(=('run-query' purpose.row) =(actor actor.row)))))
  ?:  &(more ?|(=(0 entropy) (gte counter.next 18.446.744.073.709.551.615) (gte (lent ~(tap by cursors.next)) 64) (gte (lent (skim ~(tap by cursors.next) |=([key=@t row=cursor-record:stead-views] =(principal.identity.actor principal.identity.actor.row)))) 4)))
    [(error query 'capacity_exceeded') prior]
  =?  next  more  next(counter +(counter.next))
  =/  token  ?:(more (token:stead-session entropy counter.next 'stead.run-cursor/1') '')
  ?:  &(more (~(has by cursors.prior) token))  [(error query 'capacity_exceeded') prior]
  =?  cursors.next  more
    (~(put by cursors.next) token [actor *query:stead-team-codec generation rank epoch (add offset (lent page)) (min expires.actor (add now 300.000)) 'run-query' filter ''])
  =/  fields
    %-  fields:stead-views
    :~  ['protocol' 'stead.run-query-result/1']  ['status' 'read']  ['request_id' request.query]
        ['kind' kind.query]  ['project_id' project.query]  ['work_id' work.query]  ['run_id' run.query]
        ['authority_epoch' (decimal epoch)]  ['generation' generation]  ['cursor' token]
    ==
  =/  index=@ud  0
  =/  output=object-map  ~
  |-
  ?~  page
    =/  encoded  (canonical [%o (~(put by fields) 'rows' [%o output])])
    ?:  (gth (met 3 encoded) 262.144)  [(error query 'capacity_exceeded') prior]
    [encoded next]
  $(page t.page, index +(index), output (~(put by output) (decimal index) [%o fields.i.page]))
--
