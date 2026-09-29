/+  stead-updates, stead-update-codec, stead-update-security, stead-team, stead-team-codec, stead-team-config, stead-codec, stead-core, stead-git, stead-projection, stead-views, stead-session, stead-browser, stead-team-owner
/=  home-agent  /app/stead-home
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  (fixture-id:stead-core (cat 3 '000000000' (decimal:stead-codec n)))
++  command
  |=  [req=@ud resource=@ud revision=@ud operation=@t payload=(list [@t @t])]
  ^-  command:stead-codec
  =/  value
    %-  object:stead-codec
    :~  ['protocol' 'stead.command/3']  ['request_id' (id req)]
        ['project_id' (id 100)]  ['resource_id' (id resource)]
        ['expected_revision' (decimal:stead-codec revision)]
        ['authority_epoch' '1']  ['operation' operation]
    ==
  ?>  ?=([%o *] value)
  (decode:stead-team-codec (canonical:stead-codec [%o (~(put by p.value) 'payload' (object:stead-codec payload))]))
++  value
  |=  raw=@t
  ^-  object-map:stead-codec
  =/  parsed  (need (parse-result:stead-codec raw))
  ?>  ?=([%o *] parsed)
  p.parsed
++  field
  |=  [raw=@t name=@t]
  (field:stead-codec (value raw) name)
++  accepted
  |=  out=transition:stead-team
  =('accepted' (field response.out 'status'))
++  indexed
  |=  db=state:stead-team
  ^-  state:stead-projection
  =/  view  (begin:stead-projection db *state:stead-projection)
  |-
  ?:  (ready:stead-projection db view)  view
  ?>  &(!poisoned.view rebuilding.view)
  $(view (batch:stead-projection db view))
++  saved-owner
  |=  app=agent:gall
  ^-  saved:stead-team-owner
  =/  captured=vase  on-save:app
  =/  decoded  !<([%stead-home %3 team=saved:stead-team-owner] captured)
  team.decoded
++  wake-wire
  |=  cards=(list card:agent:gall)
  ^-  wire
  =/  waiting
    %+  skim  cards
    |=(card=card:agent:gall ?=([%pass [%stead-rebuild @ ~] %arvo %b %wait @] card))
  ?>  ?=(^ waiting)
  ?>  ?=(~ t.waiting)
  ?>  ?=([%pass [%stead-rebuild @ ~] %arvo %b %wait @] i.waiting)
  =/  [%pass route=wire *]  i.waiting
  route
++  bounded-pump
  |=  [app=agent:gall cards=(list card:agent:gall) actor=authentication:stead-team stop=@ud]
  ^-  [app=agent:gall cards=(list card:agent:gall)]
  =/  turns=@ud  0
  |-
  =/  saved  (saved-owner app)
  =/  done
    ?:  =(stop 0)  (ready:stead-projection db.saved projection.saved)
    ?&(rebuilding.projection.saved ?=(^ remaining.projection.saved) =(stop (lent entries.shadow.projection.saved)))
  ?:  done  [app cards]
  ?>  (lth turns 32)
  ?>  !(ready:stead-projection db.saved projection.saved)
  ?>  =(~ entries.visible.projection.saved)
  =/  input=query:stead-team-codec  [(id 990) 'work' (id 100) '' '' '' '']
  =/  unavailable  (execute:stead-views db.saved projection.saved *state:stead-views actor input 2.000 990)
  ?>  =((error:stead-team 'projection_unavailable') response.unavailable)
  =/  [next-cards=(list card:agent:gall) next=agent:gall]
    (on-arvo:app (wake-wire cards) [%behn %wake ~])
  =/  observed  (saved-owner next)
  ::  Each actual projection wake consumes at most sixteen accepted events.
  =/  bounded
    ?.  &(rebuilding.projection.saved ?=(^ remaining.projection.saved))
      ?.  ?=(^ remaining.projection.observed)
        !(ready:stead-projection db.observed projection.observed)
      ?&  rebuilding.projection.observed
          !poisoned.projection.observed
          =(68 (lent remaining.projection.observed))
          =(~ entries.shadow.projection.observed)
          =(~ entries.visible.projection.observed)
      ==
    ?>  !poisoned.projection.observed
    =/  left  (lent remaining.projection.saved)
    =/  consumed  (min 16 left)
    ?>  =((sub left consumed) (lent remaining.projection.observed))
    =/  count  (add (lent entries.shadow.projection.saved) consumed)
    ?:  rebuilding.projection.observed
      =((lent entries.shadow.projection.observed) count)
    ?&  =(~ entries.shadow.projection.observed)
        =((lent entries.visible.projection.observed) count)
    ==
  ?>  bounded
  $(app next, cards next-cards, turns +(turns))
++  same-pages
  |=  [db=state:stead-team expected=state:stead-projection actual=state:stead-projection actor=authentication:stead-team kind=@t]
  ^-  ?
  =/  input=query:stead-team-codec  [(id 991) kind (id 100) '' '' '' '']
  =/  left=state:stead-views  *state:stead-views
  =/  right=state:stead-views  *state:stead-views
  =/  page=@ud  0
  |-
  ?>  (lth page 8)
  =/  wanted  (execute:stead-views db expected left actor input (add 2.000 page) (add 800 page))
  =/  observed  (execute:stead-views db actual right actor input (add 2.000 page) (add 800 page))
  ?>  =(wanted observed)
  ?>  =('read' (field response.observed 'status'))
  =/  continuation  (field response.observed 'cursor')
  ?:  =('' continuation)  &
  $(input input(cursor continuation), left next.wanted, right next.observed, page +(page))
++  bounded-recovery
  |=  [db=state:stead-team expected=state:stead-projection actor=authentication:stead-team member=authentication:stead-team]
  ^-  state:stead-projection
  ?>  =(68 (lent journal.data.db))
  ?>  ?=(^ journal.data.db)
  =/  context=bowl:gall  *bowl:gall
  =.  context  context(our ~zod, src ~zod, now (add ~1970.1.1 (mul 2 ~s1)), eny `@uvJ`17, act 5)
  =/  initial-agent  ~(. home-agent context)
  =/  [load-cards=(list card:agent:gall) loaded=agent:gall]
    (on-load:initial-agent !>([%stead-home %3 [db expected]]))
  =/  [partial=agent:gall partial-cards=(list card:agent:gall)]
    (bounded-pump loaded load-cards actor 32)
  =/  checkpoint  (saved-owner partial)
  ?>  =(db db.checkpoint)
  ?>  =(32 (lent entries.shadow.projection.checkpoint))
  ?>  =(36 (lent remaining.projection.checkpoint))
  =/  partial-vase=vase  on-save:partial
  =/  reload-initial  ~(. home-agent context(eny `@uvJ`37, act 6))
  =/  [reload-cards=(list card:agent:gall) reloaded=agent:gall]
    (on-load:reload-initial partial-vase)
  ::  Load starts a new authenticated reconstruction; it does not trust shadow.
  ?>  !=((wake-wire partial-cards) (wake-wire reload-cards))
  =/  [ignored-cards=(list card:agent:gall) ignored=agent:gall]
    (on-arvo:reloaded (wake-wire partial-cards) [%behn %wake ~])
  ?>  =(~ ignored-cards)
  ?>  =((saved-owner reloaded) (saved-owner ignored))
  =/  [finished=agent:gall finished-cards=(list card:agent:gall)]
    (bounded-pump reloaded reload-cards actor 0)
  =/  completed  (saved-owner finished)
  ?>  =(db db.completed)
  ?>  =(expected projection.completed)
  ?>  =(~ finished-cards)
  ?>  (levy `(list @t)`~['work' 'search' 'activity' 'inbox']
        |=(kind=@t &((same-pages db expected projection.completed actor kind) (same-pages db expected projection.completed member kind))))
  ::  Valid duplicates remain idempotent; gaps and corrupt data never promote.
  ?>  =(expected (append:stead-projection expected i.journal.data.db))
  =/  chronological  (flop journal.data.db)
  =/  staged  (begin:stead-projection db *state:stead-projection)
  =/  gapped  (batch:stead-projection db staged(remaining [(snag 0 chronological) (snag 2 chronological) ~]))
  ?>  &(poisoned.gapped =(~ entries.visible.gapped))
  =/  first-row  (snag 0 chronological)
  =/  corrupt  (batch:stead-projection db staged(remaining [first-row(bytes 'bad') ~]))
  ?>  &(poisoned.corrupt =(~ entries.visible.corrupt))
  projection.completed
++  wire
  |=  input=envelope:stead-update-codec
  %-  canonical:stead-codec
  %-  object:stead-codec
  :~  ['protocol' 'stead.updates/3']  ['request_id' request.input]
      ['action' action.input]  ['watch_id' watch.input]  ['cursor' cursor.input]
      ['kind' kind.query.input]  ['project_id' project.query.input]
      ['resource_id' resource.query.input]  ['container_id' container.query.input]
      ['search' search.query.input]
  ==
++  rejected-wire
  |=  raw=@t
  ^-  ?
  =/  out  (mule |.((decode:stead-update-codec raw)))
  =(%| -.out)
++  envelope
  |=  [request=@ud action=@t watch=@t cursor=@t query=query:stead-team-codec]
  ^-  envelope:stead-update-codec
  [(id request) action watch cursor query(request (id request), cursor '')]
--
=/  initial  (configure:stead-team empty:stead-team '{"protocol":"stead.team-config/1","expected_revision":"0","home":"~zod","origin":"https://home.test","organization_id":"019939ba-4000-7000-8000-000000000005","team_id":"019939ba-4000-7000-8000-000000000006","custody":"local-disposable","runtime":"isolated-fake","bindings":{"~bus":{"principal_id":"019939ba-4000-7000-8000-000000000102","binding_id":"019939ba-4000-7000-8000-000000000202","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Alice"},"~nec":{"principal_id":"019939ba-4000-7000-8000-000000000103","binding_id":"019939ba-4000-7000-8000-000000000203","binding_revision":"1","active":"yes","expires_at_ms":"9999999","display_name":"Zoë"}},"project_creators":{"019939ba-4000-7000-8000-000000000102":"yes"}}' ~zod 1.000)
=/  alice  (need (native-context:stead-team initial ~bus 1.001))
=/  bob  (need (native-context:stead-team initial ~nec 1.001))
?>  ?=(~ (native-context:stead-team initial ~bud 1.001))
=/  create  (command 301 100 0 'project.create' ~[['organization_id' '019939ba-4000-7000-8000-000000000005'] ['owning_team_id' '019939ba-4000-7000-8000-000000000006'] ['title' 'Garden'] ['project_key' 'GARDEN'] ['preset' 'general']])
=/  project  (apply-command:stead-team initial alice create 1.001)
?>  (accepted project)
?>  =(3 (role:stead-team next.project alice (id 100) 1.002))
?>  =(0 (role:stead-team next.project bob (id 100) 1.002))
=/  replay  (apply-command:stead-team next.project alice create 1.002)
?>  =(project replay)
=/  grant  (command 302 100 1 'policy.grant' ~[['grant_id' (id 501)] ['principal_id' principal.identity.bob] ['role' 'contributor'] ['expires_at_ms' '8000000']])
=/  granted  (apply-command:stead-team next.project alice grant 1.003)
?>  (accepted granted)
?>  =(2 (role:stead-team next.granted bob (id 100) 1.004))
=/  work-cmd  (command 303 101 0 'work.create' ~[['title' 'First task'] ['description' 'Native state'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']])
=/  work  (apply-command:stead-team next.granted bob work-cmd 1.004)
?>  (accepted work)
?>  (subject:stead-team next.work alice (id 100) 'work' '' (id 101) 1.005)
=/  db  next.work
=/  view  (indexed db)
=/  query=query:stead-team-codec  [(id 601) 'work' (id 100) '' '' '' '']
=/  open  (envelope 701 'open' '' '' query)
=/  first  (execute:stead-updates db view *state:stead-session *state:stead-updates *state:stead-views bob open 1.010 1)
=/  watch  (field response.first 'watch_id')
=/  cursor  (field response.first 'cursor')
=/  poll  (envelope 702 'poll' watch cursor [(id 702) '' '' '' '' '' ''])
=/  changed  (apply-command:stead-team db alice (command 304 102 0 'work.create' ~[['title' 'Second'] ['description' 'Update'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']]) 1.011)
?>  (accepted changed)
=/  later  next.changed
=/  advanced  (advance:stead-updates later *state:stead-session next.first pages.first 1.011)
=/  consumed  (execute:stead-updates later (indexed later) *state:stead-session next.advanced pages.advanced bob poll 1.012 2)
|%
++  test-updates-global-watch-cursor-stream-caps
  ^-  tang
  ::  Seventeen distinct current native bindings, four watches apiece. Use a
  ::  different authorized view kind for each to create 64 real streams.
  =/  registry=registry:stead-team-config  registry.db
  =/  config  (need current.registry)
  =/  index=@ud  0
  =/  prepared
    |-
    ?:  =(index 17)  registry(current [~ config])
    =/  person=actor:stead-session  [(add 256 index) (id (add 600 index)) (id (add 700 index)) 1 & 9.999.999]
    =.  config  config(members (~(put by members.config) ship.person [person 'Capacity member']))
    =.  registry  registry(revisions (~(put by revisions.registry) principal.person 1), owners (~(put by owners.registry) binding.person principal.person))
    $(index +(index))
  ?>  (validate:stead-team-config prepared ~zod)
  =/  data=state:stead-team  db(registry prepared)
  =.  data
    =/  index=@ud  0
    |-
    ?:  =(index 17)  data
    =/  cmd  (command (add 900 index) 100 (add 2 index) 'policy.grant' ~[['grant_id' (id (add 550 index))] ['principal_id' (id (add 600 index))] ['role' 'reader'] ['expires_at_ms' '8000000']])
    =/  changed  (apply-command:stead-team data alice cmd 1.010)
    ?>  (accepted changed)
    $(data next.changed, index +(index))
  =/  projection  (indexed data)
  =/  scope  query
  =/  filled
    =/  out=result:stead-updates  ['' *state:stead-updates *state:stead-views]
    =/  index=@ud  0
    |-
    ?:  =(index 64)  out
    =/  actor  (need (native-context:stead-team data (add 256 (div index 4)) 1.010))
    =/  input  (envelope 701 'open' '' '' scope(kind (snag (mod index 4) `(list @t)`~['work' 'search' 'activity' 'inbox'])))
    ?>  =(input (decode:stead-update-codec (wire input)))
    =/  next  (execute:stead-updates data projection *state:stead-session next.out pages.out actor input 1.010 (add 100 index))
    ?>  =('watching' (field response.next 'status'))
    $(index +(index), out next)
  ?>  =(64 (lent ~(tap by watches.next.filled)))
  ?>  =(64 (lent ~(tap by streams.next.filled)))
  ?>  =(64 (lent ~(tap by cursors.pages.filled)))
  =/  extra  (need (native-context:stead-team data `@p`272 1.010))
  =/  overflow  (execute:stead-updates data projection *state:stead-session next.filled pages.filled extra open(query scope) 1.011 180)
  ?>  =('capacity_exceeded' (field response.overflow 'error'))
  ?>  =(next.filled next.overflow)
  ?>  =(pages.filled pages.overflow)
  =/  only-pages=state:stead-views  pages.filled(cursors (malt (turn ~(tap by cursors.pages.filled) |=([key=@t val=cursor-record:stead-views] [key val(purpose 'query', owner '', access '')]))))
  =/  page-overflow  (execute:stead-updates data projection *state:stead-session *state:stead-updates only-pages extra open(query scope) 1.011 183)
  ?>  =('capacity_exceeded' (field response.page-overflow 'error'))
  ?>  =(*state:stead-updates next.page-overflow)
  ?>  =(only-pages pages.page-overflow)
  =/  released  (need (native-context:stead-team data `@p`271 1.010))
  =/  watch  (field response.filled 'watch_id')
  =/  cancelled  (execute:stead-updates data projection *state:stead-session next.filled pages.filled released poll(action 'cancel', watch watch, cursor '') 1.012 181)
  ?>  =(63 (lent ~(tap by watches.next.cancelled)))
  ?>  =(63 (lent ~(tap by streams.next.cancelled)))
  ?>  =(63 (lent ~(tap by cursors.pages.cancelled)))
  =/  admitted  (execute:stead-updates data projection *state:stead-session next.cancelled pages.cancelled extra open(query scope) 1.013 182)
  ?>  =('watching' (field response.admitted 'status'))
  ?>  =(64 (lent ~(tap by watches.next.admitted)))
  ~
++  test-updates-retained-history-sixty-four-then-trim
  ^-  tang
  =/  data  db
  =/  projection  view
  =/  prior  next.first
  =/  pages  pages.first
  =/  current  cursor
  =/  n=@ud  1
  |-
  ?>  (lte n 65)
  =/  cmd  (command (add 900 n) 101 n 'work.update' ~[['title' 'Retained history'] ['description' (decimal:stead-codec n)] ['type' 'task'] ['status' 'todo'] ['priority' 'none']])
  =/  changed  (apply-command:stead-team data alice cmd (add 1.100 n))
  ?>  (accepted changed)
  ?>  ?=(^ journal.data.next.changed)
  =/  next-view  (append:stead-projection projection i.journal.data.next.changed)
  ?>  (ready:stead-projection next.changed next-view)
  =/  advanced  (advance:stead-updates next.changed *state:stead-session prior pages (add 1.100 n))
  =/  out  (execute:stead-updates next.changed next-view *state:stead-session next.advanced pages.advanced bob poll(cursor current) (add 1.100 n) (add 500 n))
  ?>  =('updated' (field response.out 'status'))
  =/  rows  (~(got by (value response.out)) 'rows')
  ?>  ?=([%o *] rows)
  ?>  =(1 (lent ~(tap by p.rows)))
  =/  item  (~(got by p.rows) '0')
  ?>  ?=([%o *] item)
  ?>  =((decimal:stead-codec n) (field:stead-codec p.item 'sequence'))
  ?>  =(1 (lent ~(tap by streams.next.out)))
  ?>  =(1 (lent ~(tap by watches.next.out)))
  ?>  =(1 (lent ~(tap by cursors.pages.out)))
  =/  row  (~(got by watches.next.out) watch)
  ?>  !closed.row
  =/  stream  (~(got by streams.next.out) stream.row)
  =/  retained  (flop (turn rows.stream |=(item=invalidation:stead-updates sequence.item)))
  ?>  ?:(=(n 64) =(retained (gulf 1 64)) &)
  ?:  =(n 65)
    ?>  =(retained (gulf 2 65))
    ?>  =(next-view (indexed next.changed))
    ?>  =(next-view (bounded-recovery next.changed next-view alice bob))
    ~
  $(data next.changed, projection next-view, prior next.out, pages pages.out, current (field response.out 'cursor'), n +(n))
--
