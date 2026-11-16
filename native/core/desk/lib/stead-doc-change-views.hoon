::  Reserved current-authorized Doc Change reads. No serving route uses this.
::  These reads never return raw authentication, grant snapshots or receipts.
/+  stead-codec, stead-core, stead-team, stead-team-codec, stead-session, stead-views, stead-principals, stead-product-state, stead-product-adapters, stead-doc-change-codec, stead-doc-change-state, stead-doc-change, stead-doc-change-query
=,  stead-codec
|%
+$  result  [response=@t next=state:stead-views]
+$  body  [status=@t markdown=@t digest=@t]
++  error
  |=  [query=query:stead-doc-change-query reason=@t]
  ^-  @t
  (canonical (object ~[['protocol' 'stead.doc-change-query-result/1'] ['status' 'rejected'] ['request_id' request.query] ['error' reason]]))
++  member
  |=  [state=state:stead-doc-change catalog=state:stead-principals actor=authentication:stead-team query=query:stead-doc-change-query now=@ud]
  ^-  ?
  ?&  (current:stead-team db.state actor now)
      (gth (role:stead-team db.state actor project.query now) 0)
      (subject:stead-team db.state actor project.query 'work' '' work.query now)
      =/  principal  (~(get by principals.catalog) principal.identity.actor)
      ?~(principal | active.u.principal)
  ==
++  display
  |=  [catalog=state:stead-principals principal=@t]
  ^-  @t
  =/  row  (~(get by principals.catalog) principal)
  ?~(row '' display.u.row)
++  target-body
  ::  A historical base must be proved by this exact Doc's accepted save.
  ::  A matching blob in the global object store is not a scoped history proof.
  |=  [state=state:stead-doc-change output=output:stead-doc-change-state]
  ^-  body
  ?>  ?=([%o *] target.output)
  =/  target  p.target.output
  =/  revision  (uint (field target 'expected_revision'))
  ?:  =(0 revision)  ['new-document' '' '']
  =/  sha  (field target 'base_markdown_sha256')
  =/  collection  (field target 'collection_id')
  =/  document  (field target 'document_id')
  =/  journal  journal.data.db.state
  ?>  (lte (lent journal) 6.144)
  |-
  ?~  journal  ['unavailable' '' sha]
  ?.  =(project.output project.i.journal)  $(journal t.journal)
  =/  value  (need (parse-result bytes.i.journal))
  ?>  ?=([%o *] value)
  =/  record  p.value
  ?.  =(revision (uint (field record 'new_revision')))  $(journal t.journal)
  =/  cmd  (decode:stead-team-codec (field record 'canonical_command'))
  ?.  &(=('document.save' operation.cmd) =(project.output project.cmd) =(document resource.cmd))
    $(journal t.journal)
  ?.  =(collection (field payload.cmd 'container_id'))  $(journal t.journal)
  =/  markdown  (field payload.cmd 'markdown')
  ?.  =(sha (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown]))
    $(journal t.journal)
  ['ready' markdown sha]
++  result-body
  |=  [state=state:stead-doc-change output=output:stead-doc-change-state side=@t]
  ^-  body
  ?:  =('before' side)  (target-body state output)
  ?>  =('after' side)
  =/  markdown  (~(got by bodies.changes.state) markdown-sha256.output)
  ?>  &(=(markdown-sha256.output (markdown-sha256:stead-product-adapters [(met 3 markdown) markdown])) (canonical-markdown:stead-doc-change target.output markdown))
  ['ready' markdown markdown-sha256.output]
++  evidence-view
  |=  [catalog=state:stead-principals evidence=(unit evidence:stead-doc-change-state)]
  ^-  @t
  ?~  evidence  ''
  %-  canonical
  (object ~[['principal_id' principal.identity.actor.u.evidence] ['display_name' (display catalog principal.identity.actor.u.evidence)] ['recorded_at_ms' (decimal recorded-at.u.evidence)] ['note' note.u.evidence] ['result_digest' digest.u.evidence]])
++  acceptance-view
  |=  [catalog=state:stead-principals accepted=(unit acceptance:stead-doc-change-state) digest=@t]
  ^-  @t
  ?~  accepted  ''
  %-  canonical
  (object ~[['principal_id' principal.identity.actor.u.accepted] ['display_name' (display catalog principal.identity.actor.u.accepted)] ['recorded_at_ms' (decimal recorded-at.u.accepted)] ['document_revision' (decimal revision.u.accepted)] ['result_digest' digest]])
++  feedback
  ::  One bounded scan only for an opened result, never per list preview.
  ::  Retained accepted decision receipts bind notes to their original result.
  |=  [state=state:stead-doc-change catalog=state:stead-principals output=output:stead-doc-change-state]
  ^-  @t
  =/  items  ~(tap by attempts.changes.state)
  ?>  (lte (lent items) 4.096)
  =/  latest=@ud  0
  =/  selected=@t  ''
  |-
  ?~  items  selected
  =/  key  p.i.items
  =/  item  q.i.items
  ?.  &(=(project.output project.key) =(work.output work.item) =(change.output change.item) !=('change.submit' operation.item))
    $(items t.items)
  =/  raw  (need (parse-result receipt.item))
  ?>  ?=([%o *] raw)
  =/  row  p.raw
  =/  accepted  =('accepted' (field row 'status'))
  =/  quarantined  =('producer_quarantined' (field row 'error'))
  ?.  ?|(accepted quarantined)  $(items t.items)
  ?.  &(=(digest.output (field row 'result_digest')) =(revision.output (uint (field row 'result_revision'))))
    $(items t.items)
  =/  revision  (uint (field row 'resulting_revision'))
  ?.  (gth revision latest)  $(items t.items)
  =/  command  (decode:stead-doc-change-codec command.item)
  ?>  ?&  =(request.key request.command)  =(digest.item digest.command)  =(operation.item operation.command)
          =(project.output project.command)  =(work.output work.command)  =(change.output change.command)
          =(digest.output (field payload.command 'result_digest'))
          =(revision.output (uint (field payload.command 'result_revision')))
      ==
  =/  next
    %-  canonical
    (object ~[['operation' operation.item] ['outcome' ?:(quarantined 'producer_quarantined' 'accepted')] ['principal_id' principal.key] ['display_name' (display catalog principal.key)] ['recorded_at_ms' (field row 'recorded_at_ms')] ['note' (field payload.command 'note')] ['result_revision' (decimal revision.output)] ['result_digest' digest.output] ['change_revision' (decimal revision)]])
  $(items t.items, latest revision, selected next)
++  action-reason
  ::  Advisory current preconditions only. The real reducer still rechecks
  ::  request identity, capacity, evidence and final acceptance atomically.
  |=  [state=state:stead-doc-change catalog=state:stead-principals actor=authentication:stead-team head=head:stead-doc-change-state output=output:stead-doc-change-state operation=@t now=@ud runs=run-resolver:stead-doc-change]
  ^-  @t
  ?.  &(=(output-revision.head revision.output) =(output-digest.head digest.output))  'superseded_result'
  ?.  (gte (role:stead-team db.state actor project.output now) 2)  'read_only'
  ?.  (human:stead-doc-change state catalog actor project.output now)  'human_review_required'
  ?:  ?|  =(%accepted status.head)  =(%rejected status.head)  =(%quarantined status.head)
      ==
    'change_closed'
  ?:  =('change.quarantine' operation)
    ?:((accountable:stead-doc-change state catalog actor project.output work.output now) '' 'accountable_human_required')
  ?.  (exact-contract:stead-doc-change state output)  'execution_contract_conflict'
  ?.  (current-target:stead-product-adapters db.state actor project.output work.output principal.identity.actor target.output now)
    'target_base_conflict'
  =/  authority  (producer-authority:stead-doc-change state catalog output now runs)
  ?:  ?|  =(%revoked authority)  =(%unknown authority)
      ==
    'producer_quarantined'
  ?:  =('change.adopt' operation)
    ?.  =(%expired authority)  'adoption_requires_expiry'
    ?.  (accountable:stead-doc-change state catalog actor project.output work.output now)  'accountable_human_required'
    ?:(=(principal.identity.actor producer.head) 'independent_adopter_required' '')
  ?:  =('change.accept' operation)
    ?.  (accountable:stead-doc-change state catalog actor project.output work.output now)  'accountable_human_required'
    ?.  &(?=(%approved status.head) (evidence-current:stead-doc-change state catalog approval.head output now |))
      'independent_review_required'
    ?.  ?|  =(%live authority)
            &(?=(%expired authority) (evidence-current:stead-doc-change state catalog adoption.head output now &))
        ==
      'explicit_adoption_required'
    ''
  ?:(=(principal.identity.actor producer.head) 'self_review_denied' '')
++  actions
  |=  [state=state:stead-doc-change catalog=state:stead-principals actor=authentication:stead-team head=head:stead-doc-change-state output=output:stead-doc-change-state now=@ud runs=run-resolver:stead-doc-change]
  ^-  @t
  =/  names  ~['change.request-changes' 'change.approve' 'change.adopt' 'change.accept' 'change.reject' 'change.quarantine']
  =/  rows
    %+  turn  names
    |=  name=@t
    =/  reason  (action-reason state catalog actor head output name now runs)
    [name (object ~[['status' ?:(=('' reason) 'eligible' 'blocked')] ['reason' reason]])]
  (canonical [%o (malt rows)])
++  metadata
  |=  [state=state:stead-doc-change catalog=state:stead-principals actor=authentication:stead-team head=head:stead-doc-change-state output=output:stead-doc-change-state full=? now=@ud runs=run-resolver:stead-doc-change]
  ^-  object-map
  ?>  =(digest.output (output-digest:stead-doc-change-state output))
  =/  current  &(=(output-revision.head revision.output) =(output-digest.head digest.output))
  =/  rows
    %-  fields:stead-views
    :~  ['kind' 'doc-change']  ['project_id' project.output]  ['work_id' work.output]  ['change_id' change.output]
        ['change_revision' (decimal revision.head)]  ['change_status' (scot %tas status.head)]
        ['current_result_revision' (decimal output-revision.head)]  ['current_result_digest' output-digest.head]
        ['result_revision' (decimal revision.output)]  ['result_digest' digest.output]  ['is_current_result' ?:(current 'yes' 'no')]
        ['outcome_id' outcome.output]  ['target' (canonical target.output)]
        ['execution_contract_revision' (decimal execution.output)]  ['execution_contract_digest' execution-digest.output]
        ['producer_principal_id' principal.identity.producer.output]  ['producer_display_name' (display catalog principal.identity.producer.output)]
        ['summary' summary.output]  ['markdown_sha256' markdown-sha256.output]
        ['run_id' run.output]  ['attempt' (decimal attempt.output)]  ['submitted_at_ms' (decimal submitted-at.output)]
    ==
  ?.  full  rows
  %-  ~(uni by rows)
  %-  fields:stead-views
  :~  ['producer_binding_id' binding.identity.producer.output]  ['producer_binding_revision' (decimal revision.identity.producer.output)]
      ['approval' ?:(current (evidence-view catalog approval.head) '')]
      ['adoption' ?:(current (evidence-view catalog adoption.head) '')]
      ['acceptance' ?:(current (acceptance-view catalog acceptance.head digest.output) '')]
      ['latest_decision' (feedback state catalog output)]
      ['producer_authority' (scot %tas (producer-authority:stead-doc-change state catalog output now runs))]
      ['contract_current' ?:((exact-contract:stead-doc-change state output) 'yes' 'no')]
      ['actions' (actions state catalog actor head output now runs)]
  ==
++  output-visible
  |=  [state=state:stead-doc-change actor=authentication:stead-team query=query:stead-doc-change-query output=output:stead-doc-change-state now=@ud]
  ^-  ?
  ?&  =(project.query project.output)  =(work.query work.output)
      (visible-target:stead-doc-change state actor project.query target.output now)
  ==
++  rows
  |=  [state=state:stead-doc-change catalog=state:stead-principals actor=authentication:stead-team query=query:stead-doc-change-query now=@ud runs=run-resolver:stead-doc-change]
  ^-  (unit (list row:stead-views))
  ?>  &((lte (lent ~(tap by heads.changes.state)) 2.048) (lte (lent ~(tap by results.changes.state)) 4.096))
  ?:  =('changes' kind.query)
    =/  items  ~(tap by heads.changes.state)
    =/  found=(list row:stead-views)  ~
    |-
    ?~  items  (some (sort found |=([a=row:stead-views b=row:stead-views] (aor id.a id.b))))
    =/  key  p.i.items
    =/  head  q.i.items
    ?.  &(=(project.query project.key) =(work.query work.head))  $(items t.items)
    =/  output  (~(got by results.changes.state) [project.key change.key output-revision.head])
    ?.  (output-visible state actor query output now)  $(items t.items)
    $(items t.items, found [[change.key (metadata state catalog actor head output | now runs)] found])
  =/  head  (~(get by heads.changes.state) [project.query change.query])
  ?~  head  ~
  ?.  =(work.query work.u.head)  ~
  =/  latest  (~(got by results.changes.state) [project.query change.query output-revision.u.head])
  ?.  (output-visible state actor query latest now)  ~
  ?:  =('results' kind.query)
    =/  items  ~(tap by results.changes.state)
    =/  found=(list row:stead-views)  ~
    |-
    ?~  items
      (some (sort found |=([a=row:stead-views b=row:stead-views] (lth (uint id.a) (uint id.b)))))
    =/  key  p.i.items
    =/  output  q.i.items
    ?.  &(=(project.query project.key) =(change.query change.key))  $(items t.items)
    ?.  (output-visible state actor query output now)  $(items t.items)
    $(items t.items, found [[(decimal revision.output) (metadata state catalog actor u.head output | now runs)] found])
  =/  revision  ?:(=(0 revision.query) output-revision.u.head revision.query)
  =/  output  (~(get by results.changes.state) [project.query change.query revision])
  ?~  output  ~
  ?.  &(?|(=(0 revision.query) =(digest.query digest.u.output)) (output-visible state actor query u.output now))  ~
  ?:  =('change' kind.query)
    (some ~[[change.query (metadata state catalog actor u.head u.output & now runs)]])
  =/  body  (result-body state u.output side.query)
  =/  row
    %-  fields:stead-views
    :~  ['kind' 'doc-change-body']  ['project_id' project.query]  ['work_id' work.query]  ['change_id' change.query]
        ['result_revision' (decimal revision.u.output)]  ['result_digest' digest.u.output]
        ['side' side.query]  ['body_status' status.body]  ['markdown' markdown.body]  ['markdown_sha256' digest.body]
    ==
  (some ~[[change.query row]])
++  execute
  |=  [state=state:stead-doc-change catalog=state:stead-principals prior=state:stead-views actor=authentication:stead-team query=query:stead-doc-change-query now=@ud entropy=@ runs=run-resolver:stead-doc-change]
  ^-  result
  ?.  (valid:stead-doc-change-query query)  [(error query 'invalid_request') prior]
  ?.  (member state catalog actor query now)  [(error query 'denied_or_not_found') prior]
  ?~  migration.product.state  [(error query 'migration_required') prior]
  =/  attempted  (mule |.((rows state catalog actor query now runs)))
  ?:  ?=(%| -.attempted)  [(error query 'invalid_product_state') prior]
  =/  found  p.attempted
  ?~  found  [(error query 'denied_or_not_found') prior]
  =/  all  u.found
  =/  rank  (role:stead-team db.state actor project.query now)
  =/  epoch  epoch:(~(got by projects.data.db.state) project.query)
  =/  filter  (bytes:stead-doc-change-query query(request '', cursor ''))
  =/  gen  (hash 'stead.doc-change-view-generation/1' (bytes-hex (jam [actor filter rank epoch all])))
  =/  next=state:stead-views  prior(cursors (malt (skim ~(tap by cursors.prior) |=([key=@t val=cursor-record:stead-views] (gth expires.val now)))))
  =/  continuation=(unit cursor-record:stead-views)  (~(get by cursors.next) cursor.query)
  ?:  &(!=('' cursor.query) ?=(~ continuation))  [(error query 'stale_cursor') prior]
  ?.  ?~  continuation  &
      ?&  =('doc-change-query' purpose.u.continuation)  =(actor actor.u.continuation)
          =(filter owner.u.continuation)  =(gen generation.u.continuation)
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
    (malt (skip ~(tap by cursors.next) |=([key=@t val=cursor-record:stead-views] &(=('doc-change-query' purpose.val) =(actor actor.val)))))
  ?:  &(more ?|(=(0 entropy) (gte counter.next 18.446.744.073.709.551.615) (gte (lent ~(tap by cursors.next)) 64) (gte (lent (skim ~(tap by cursors.next) |=([key=@t val=cursor-record:stead-views] =(principal.identity.actor principal.identity.actor.val)))) 4)))
    [(error query 'capacity_exceeded') prior]
  =?  next  more  next(counter +(counter.next))
  =/  token  ?:(more (token:stead-session entropy counter.next 'stead.doc-change-cursor/1') '')
  ?:  &(more (~(has by cursors.prior) token))  [(error query 'capacity_exceeded') prior]
  =?  cursors.next  more
    (~(put by cursors.next) token [actor *query:stead-team-codec gen rank epoch (add offset (lent page)) (min expires.actor (add now 300.000)) 'doc-change-query' filter ''])
  =/  fields
    %-  fields:stead-views
    :~  ['protocol' 'stead.doc-change-query-result/1']  ['status' 'read']  ['request_id' request.query]  ['kind' kind.query]
        ['project_id' project.query]  ['work_id' work.query]  ['change_id' change.query]
        ['result_revision' (decimal revision.query)]  ['result_digest' digest.query]  ['side' side.query]
        ['authority_epoch' (decimal epoch)]  ['generation' gen]  ['cursor' token]
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
