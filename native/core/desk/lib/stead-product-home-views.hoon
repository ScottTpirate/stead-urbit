::  Product Home read dispatcher. Typed roster and exact completion advice
::  are scoped reads; neither grants authority nor replaces commit checks.
/+  stead-codec, stead-team, stead-team-codec, stead-session, stead-views, stead-principals, stead-product-state, stead-product-codec, stead-product-query, stead-product-views, stead-product-work, stead-product-history, stead-doc-change, stead-doc-change-proof
=,  stead-codec
|%
++  roster
  |=  [state=state:stead-product-history project=@t now=@ud]
  ^-  (list row:stead-views)
  =/  config  (need current.registry.db.state)
  ::  Config decode/restore validates one binding per principal. Do not merge
  ::  conflicting identities into a synthesized roster member.
  =/  people  ~(tap by members.config)
  =/  output=(list row:stead-views)  ~
  |-
  ?~  people  (sort output |=([a=row:stead-views b=row:stead-views] (aor id.a id.b)))
  =/  member  q.i.people
  =/  actor  (native-context:stead-team db.state p.i.people now)
  ?~  actor  $(people t.people)
  =/  rank  (role:stead-team db.state u.actor project now)
  ?:  =(rank 0)  $(people t.people)
  =/  principal  principal.identity.member
  =/  saved  (~(get by principals.catalog.state) principal)
  ?~  saved  $(people t.people)
  =/  kind  ?~(kind.u.saved 'unresolved' (scot %tas u.kind.u.saved))
  =/  role  ?:(=(rank 3) 'maintainer' ?:(=(rank 2) 'contributor' 'reader'))
  =/  row
    %-  fields:stead-views
    :~  ['kind' 'principal']  ['principal_id' principal]
        ['display_name' display.u.saved]  ['principal_kind' kind]
        ['active' ?:(active.u.saved 'yes' 'no')]  ['project_role' role]
    ==
  $(people t.people, output [[principal row] output])
++  completion
  |=  [state=state:stead-product-history actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  row:stead-views
  =/  key=work-key:stead-product-state  [project.query resource.query]
  =/  work  (~(got by works.data.db.state) key)
  =/  meta  (~(got by works.product.state) key)
  ?>  =(execution-digest.meta (contract-digest:stead-product-state key execution-revision.meta data.work))
  =/  outcomes  (object-field:stead-product-codec data.work 'required_outcomes')
  =/  epoch  epoch:(~(got by projects.data.db.state) project.query)
  =/  wanted=proof-request:stead-product-work
    [project.query resource.query epoch execution-revision.meta execution-digest.meta outcomes principal.identity.actor now]
  =/  proof
    (resolve:stead-doc-change-proof [db.state product.state changes.state] actor wanted)
  =/  blocked
    ?|  ?&(?=(^ legacy-blocked.meta) !resolved.u.legacy-blocked.meta)
        !=('' (field data.work 'blocked_reason'))
        (~(has in (silt ~['done' 'canceled'])) (field data.work 'status'))
    ==
  =/  ready  &(?=(^ outcomes) ?=(^ proof) !blocked)
  =/  reason  ?~(outcomes 'human-note-required' ?:(ready '' 'required-outcomes-unconfirmed'))
  :-  resource.query
  %-  fields:stead-views
  :~  ['kind' 'completion']  ['project_id' project.query]  ['work_id' resource.query]
      ['execution_contract_revision' (decimal execution-revision.meta)]
      ['execution_contract_digest' execution-digest.meta]
      ['ready' ?:(ready 'yes' 'no')]  ['reason' reason]
  ==
++  execute
  |=  [state=state:stead-product-history prior=state:stead-views actor=authentication:stead-team query=query:stead-team-codec now=@ud entropy=@]
  ^-  result:stead-views
  ?.  (active-member:stead-product-history state actor now)
    [(error:stead-product-views query 'denied_or_not_found') prior]
  =/  checked  (mule |.((decode:stead-product-query (bytes:stead-product-query query))))
  ?:  ?=(%| -.checked)  [(error:stead-product-views query 'invalid_request') prior]
  ?:  ?|(=('work' kind.query) =('comments' kind.query))
    (execute:stead-product-views db.state product.state prior actor query now entropy)
  =/  rank  (role:stead-team db.state actor project.query now)
  ?.  (gte rank 2)  [(error:stead-product-views query 'denied_or_not_found') prior]
  ?~  migration.product.state  [(error:stead-product-views query 'migration_required') prior]
  ?:  &(=('completion' kind.query) !(subject:stead-team db.state actor project.query 'work' '' resource.query now))
    [(error:stead-product-views query 'denied_or_not_found') prior]
  =/  attempted
    %-  mule
    |.
    ?:  =('principals' kind.query)  (roster state project.query now)
    ~[(completion state actor query now)]
  ?:  ?=(%| -.attempted)  [(error:stead-product-views query 'invalid_product_state') prior]
  =/  all  p.attempted
  =/  epoch  epoch:(~(got by projects.data.db.state) project.query)
  =/  filter  query(request '', cursor '')
  =/  gen  (hash 'stead.product-home-view/1' (bytes-hex (jam [identity.actor filter rank epoch all])))
  =/  next=state:stead-views
    prior(cursors (malt (skim ~(tap by cursors.prior) |=([key=@t val=cursor-record:stead-views] (gth expires.val now)))))
  =/  continuation  (~(get by cursors.next) cursor.query)
  ?:  &(!=('' cursor.query) ?=(~ continuation))  [(error:stead-product-views query 'stale_cursor') prior]
  ?.  ?~  continuation  &
      ?&  =('product-principals' purpose.u.continuation)  =(actor actor.u.continuation)
          =(filter query.u.continuation)  =(gen generation.u.continuation)
          =(rank rank.u.continuation)  =(epoch epoch.u.continuation)
      ==
    [(error:stead-product-views query 'stale_cursor') prior]
  =/  offset  ?~(continuation 0 offset.u.continuation)
  ?:  (gth offset (lent all))  [(error:stead-product-views query 'stale_cursor') prior]
  =.  cursors.next  (~(del by cursors.next) cursor.query)
  =/  remaining  (slag offset all)
  =/  page  (scag 20 remaining)
  =/  more  (gth (lent remaining) 20)
  =/  token=@t  ''
  =?  cursors.next  &(more =('' cursor.query))
    (malt (skip ~(tap by cursors.next) |=([key=@t val=cursor-record:stead-views] &(=('product-principals' purpose.val) =(actor actor.val)))))
  ?:  &(more ?|(=(0 entropy) (gte counter.next 18.446.744.073.709.551.615) (gte (lent ~(tap by cursors.next)) 64) (gte (lent (skim ~(tap by cursors.next) |=([key=@t val=cursor-record:stead-views] =(principal.identity.actor principal.identity.actor.val)))) 4)))
    [(error:stead-product-views query 'capacity_exceeded') prior]
  =?  next  more  next(counter +(counter.next))
  =?  token  more  (token:stead-session entropy counter.next 'stead.product-principal-cursor/1')
  ?:  &(more (~(has by cursors.prior) token))  [(error:stead-product-views query 'capacity_exceeded') prior]
  =?  cursors.next  more
    (~(put by cursors.next) token [actor filter gen rank epoch (add offset (lent page)) (min expires.actor (add now 300.000)) 'product-principals' '' ''])
  =/  fields
    %-  fields:stead-views
    :~  ['protocol' 'stead.query-result/4']  ['status' 'read']
        ['request_id' request.query]  ['kind' kind.query]  ['project_id' project.query]
        ['container_id' '']  ['resource_id' resource.query]  ['authority_epoch' (decimal epoch)]
        ['generation' gen]  ['cursor' token]
    ==
  =/  index=@ud  0
  =/  output=object-map  ~
  |-
  ?~  page
    =/  encoded  (canonical [%o (~(put by fields) 'rows' [%o output])])
    ?:  (gth (met 3 encoded) 262.144)  [(error:stead-product-views query 'capacity_exceeded') prior]
    [encoded next]
  $(page t.page, index +(index), output (~(put by output) (decimal index) [%o fields.i.page]))
--
