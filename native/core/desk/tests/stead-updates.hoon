/+  stead-updates, stead-update-codec, stead-update-security, stead-team, stead-team-codec, stead-team-config, stead-codec, stead-core, stead-git, stead-projection, stead-views, stead-session, stead-browser
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
++  test-updates-open-before-snapshot
  ^-  tang
  ?>  =('watching' (field response.first 'status'))
  ?>  (opaque:stead-team-codec watch)
  ?>  (opaque:stead-team-codec cursor)
  ?>  =(1 (lent ~(tap by watches.next.first)))
  ?>  =(1 (lent ~(tap by cursors.pages.first)))
  ?>  =(1 (lent ~(tap by streams.next.first)))
  ?>  =((generation:stead-views db bob query 1.010) (field response.first 'generation'))
  ?>  =('updates' purpose:(~(got by cursors.pages.first) cursor))
  ~
++  test-updates-minimal-ordered-invalidation
  ^-  tang
  ?>  =('updated' (field response.consumed 'status'))
  =/  parsed  (value response.consumed)
  =/  rows  (~(got by parsed) 'rows')
  ?>  ?=([%o *] rows)
  ?>  =(1 (lent ~(tap by p.rows)))
  =/  row  (~(got by p.rows) '0')
  ?>  ?=([%o *] row)
  ?>  (keys:stead-codec p.row ~['sequence' 'generation'])
  ?>  =('1' (field:stead-codec p.row 'sequence'))
  ?>  !(contains:stead-views 'Second' response.consumed)
  ?>  !(contains:stead-views principal.identity.alice response.consumed)
  ?>  =(advanced (advance:stead-updates later *state:stead-session next.advanced pages.advanced 1.012))
  ~
++  test-updates-replay-requires-refresh
  ^-  tang
  =/  replay  (execute:stead-updates later (indexed later) *state:stead-session next.consumed pages.consumed bob poll 1.013 3)
  ?>  =('refresh_required' (field response.replay 'status'))
  ?>  ?=(~ watches.next.replay)
  ?>  ?=(~ streams.next.replay)
  ?>  ?=(~ cursors.pages.replay)
  ~
++  test-updates-resume-retains-suffix
  ^-  tang
  =/  input  (envelope 703 'resume' '' cursor query)
  =/  resumed  (execute:stead-updates later (indexed later) *state:stead-session next.advanced pages.advanced bob input 1.012 4)
  ?>  =('resumed' (field response.resumed 'status'))
  ?>  !=(watch (field response.resumed 'watch_id'))
  ?>  !(~(has by watches.next.resumed) watch)
  ?>  !(~(has by cursors.pages.resumed) cursor)
  =/  next-poll  poll(watch (field response.resumed 'watch_id'), cursor (field response.resumed 'cursor'))
  =/  out  (execute:stead-updates later (indexed later) *state:stead-session next.resumed pages.resumed bob next-poll 1.013 5)
  ?>  =('updated' (field response.out 'status'))
  ?>  (contains:stead-views '"sequence":"1"' response.out)
  ~
++  test-updates-foreign-watch-isolation
  ^-  tang
  =/  out  (execute:stead-updates db view *state:stead-session next.first pages.first alice poll 1.011 6)
  ?>  =('refresh_required' (field response.out 'status'))
  ?>  =(next.first next.out)
  ?>  =(pages.first pages.out)
  =/  cancelled  (execute:stead-updates db view *state:stead-session next.first pages.first alice poll(action 'cancel', cursor '') 1.011 7)
  ?>  =('cancelled' (field response.cancelled 'status'))
  ?>  =(next.first next.cancelled)
  ?>  =(pages.first pages.cancelled)
  ~
++  test-updates-cursor-purpose-and-actor
  ^-  tang
  =/  page  (~(got by cursors.pages.first) cursor)
  =/  alien  (token:stead-session 1 1 'foreign')
  =/  pages  pages.first(cursors (~(put by cursors.pages.first) alien page(purpose 'query')))
  =/  out  (execute:stead-updates db view *state:stead-session next.first pages bob poll(cursor alien) 1.011 8)
  ?>  =('refresh_required' (field response.out 'status'))
  ?>  =(next.first next.out)
  ?>  =(pages pages.out)
  =/  query-out  (execute:stead-views db view pages.first bob query(cursor cursor) 1.011 9)
  ?>  =('stale_cursor' (field response.query-out 'error'))
  ?>  =(pages.first next.query-out)
  =/  resumed  (execute:stead-updates db view *state:stead-session next.first pages.first alice (envelope 704 'resume' '' cursor query) 1.011 9)
  ?>  =('refresh_required' (field response.resumed 'status'))
  ?>  =(next.first next.resumed)
  ?>  =(pages.first pages.resumed)
  ~
++  test-updates-revoked-before-dequeue
  ^-  tang
  =/  revoked  (apply-command:stead-team later alice (command 305 100 2 'policy.revoke' ~[['grant_id' (id 501)]]) 1.012)
  ?>  (accepted revoked)
  =/  out  (execute:stead-updates next.revoked (indexed next.revoked) *state:stead-session next.advanced pages.advanced bob poll 1.013 10)
  ?>  =('refresh_required' (field response.out 'status'))
  ?>  ?=(~ watches.next.out)
  ?>  ?=(~ cursors.pages.out)
  ?>  ?=(~ streams.next.out)
  ~
++  test-updates-private-change-invisible
  ^-  tang
  =/  private  (apply-command:stead-team db alice (command 306 104 0 'container.create' ~[['title' 'PRIVATE-CANARY'] ['visibility' 'private']]) 1.011)
  ?>  (accepted private)
  =/  out  (advance:stead-updates next.private *state:stead-session next.first pages.first 1.012)
  ?>  =(next.first next.out)
  ?>  =(pages.first pages.out)
  ~
++  test-updates-owned-cancel-while-rebuilding
  ^-  tang
  =/  input  poll(action 'cancel', cursor '')
  =/  out  (execute:stead-updates db *state:stead-projection *state:stead-session next.advanced pages.advanced bob input 1.013 11)
  ?>  =('cancelled' (field response.out 'status'))
  ?>  ?=(~ watches.next.out)
  ?>  ?=(~ streams.next.out)
  ?>  ?=(~ cursors.pages.out)
  ?>  =(out (execute:stead-updates db *state:stead-projection *state:stead-session next.out pages.out bob input 1.013 12))
  ~
++  test-updates-expiry-before-dequeue
  ^-  tang
  =/  out  (execute:stead-updates later (indexed later) *state:stead-session next.advanced pages.advanced bob poll 301.010 12)
  ?>  =('refresh_required' (field response.out 'status'))
  ?>  ?=(~ watches.next.out)
  ?>  ?=(~ streams.next.out)
  ?>  ?=(~ cursors.pages.out)
  ~
++  test-updates-overflow-terminal-and-caps
  ^-  tang
  =/  row  (~(got by watches.next.first) watch)
  =/  stream  (~(got by streams.next.first) stream.row)
  =/  queued  next.first(streams (~(put by streams.next.first) stream.row stream(sequence 17)))
  =/  out  (advance:stead-updates db *state:stead-session queued pages.first 1.011)
  ?>  closed:(~(got by watches.next.out) watch)
  ?>  ?=(~ cursors.pages.out)
  ?>  ?=(~ streams.next.out)
  =/  deadline  expires:(~(got by watches.next.out) watch)
  ?>  =(expires.row deadline)
  =/  final  (execute:stead-updates db view *state:stead-session next.out pages.out bob poll 1.012 13)
  ?>  =('refresh_required' (field response.final 'status'))
  ?>  ?=(~ watches.next.final)
  ~
++  test-updates-sequence-exhaustion
  ^-  tang
  =/  row  (~(got by watches.next.first) watch)
  =/  stream  (~(got by streams.next.first) stream.row)
  =/  queued  next.first(streams (~(put by streams.next.first) stream.row stream(sequence 18.446.744.073.709.551.615)))
  =/  out  (advance:stead-updates later *state:stead-session queued pages.first 1.012)
  ?>  closed:(~(got by watches.next.out) watch)
  ?>  ?=(~ cursors.pages.out)
  ?>  ?=(~ streams.next.out)
  ~
++  test-updates-cursor-collision-rollback
  ^-  tang
  ::  Synthetic entropy/counter collision with the consumed token. The trial
  ::  cursor map has deleted it; the original map must still reject reuse.
  =/  old  (~(got by watches.next.first) watch)
  =/  page  (~(got by cursors.pages.first) cursor)
  =/  collision  (token:stead-session 20 +(counter.pages.first) 'stead.updates.cursor/3')
  =/  prior  next.first(watches (~(put by watches.next.first) watch old(cursor collision)))
  =/  pages  pages.first(cursors (~(put by (~(del by cursors.pages.first) cursor)) collision page))
  =/  out  (execute:stead-updates db view *state:stead-session prior pages bob poll(cursor collision) 1.011 20)
  ?>  =('capacity_exceeded' (field response.out 'error'))
  ?>  =(prior next.out)
  ?>  =(pages pages.out)
  =/  resumed  (execute:stead-updates db view *state:stead-session prior pages bob (envelope 707 'resume' '' collision query) 1.011 20)
  ?>  =('capacity_exceeded' (field response.resumed 'error'))
  ?>  =(prior next.resumed)
  ?>  =(pages pages.resumed)
  ~
++  test-updates-actor-watch-limit
  ^-  tang
  =/  filled
    =/  out  first
    =/  index=@ud  2
    |-
    ?:  =(index 5)  out
    =/  new  (execute:stead-updates db view *state:stead-session next.out pages.out bob open 1.011 index)
    ?>  =('watching' (field response.new 'status'))
    $(out new, index +(index))
  ?>  =(4 (lent ~(tap by watches.next.filled)))
  =/  rejected  (execute:stead-updates db view *state:stead-session next.filled pages.filled bob open 1.012 30)
  ?>  =('capacity_exceeded' (field response.rejected 'error'))
  ?>  =(next.filled next.rejected)
  ?>  =(pages.filled pages.rejected)
  ~
++  test-updates-browser-session-revocation
  ^-  tang
  =/  pending  (begin:stead-session *state:stead-session identity.bob ~zod 'https://home.test' 1.010 40)
  =/  approved  (approve:stead-session next.pending id.pending ~nec identity.bob ~zod 'https://home.test' 'stead.auth/1' 'member-session' 121.010 1.011)
  =/  logged  (consume:stead-session next.approved id.pending cookie.pending identity.bob ~zod 'https://home.test' 1.012 41)
  ?>  =(%accepted status.logged)
  =/  session  (~(got by sessions.next.logged) (digest:stead-session 'stead.session/1' cookie.logged))
  =/  actor  (need (browser-context:stead-team db session 1.013))
  =/  out  (execute:stead-updates db view next.logged *state:stead-updates *state:stead-views actor open 1.013 42)
  ?>  =('watching' (field response.out 'status'))
  =/  pruned  (prune:stead-updates db *state:stead-session next.out pages.out 1.014)
  ?>  ?=(~ watches.next.pruned)
  ?>  ?=(~ streams.next.pruned)
  ?>  ?=(~ cursors.pages.pruned)
  ?>  !(current:stead-update-security db next.logged actor 1.801.012)
  ~
++  test-updates-public-codec-admission
  ^-  tang
  ?>  =(open (decode:stead-update-codec (wire open)))
  ?>  =(poll (decode:stead-update-codec (wire poll)))
  =/  cancel  poll(action 'cancel', cursor '')
  ?>  =(cancel (decode:stead-update-codec (wire cancel)))
  =/  resume  open(action 'resume', cursor cursor)
  ?>  =(resume (decode:stead-update-codec (wire resume)))
  =/  data  (value (wire open))
  ?>  (rejected-wire (canonical:stead-codec [%o (~(put by data) 'protocol' [%s 'stead.updates/99'])]))
  ?>  (rejected-wire (canonical:stead-codec [%o (~(put by data) 'actor' [%s principal.identity.bob])]))
  ?>  (rejected-wire (canonical:stead-codec [%o (~(del by data) 'cursor')]))
  ?>  (rejected-wire (wire open(action 'unknown')))
  ?>  (rejected-wire (wire open(watch watch)))
  ?>  (rejected-wire (wire open(cursor cursor)))
  ?>  (rejected-wire (wire poll(query query)))
  ?>  (rejected-wire (wire poll(cursor 'bad')))
  ?>  (rejected-wire (wire cancel(cursor cursor)))
  ?>  (rejected-wire (wire open(query query(kind 'identity', project ''))))
  ?>  (rejected-wire (wire open(query query(kind 'receipt', resource (id 303)))))
  =/  raw  (wire open)
  =/  padded  (cat 3 raw (fil 3 (sub 2.048 (met 3 raw)) 32))
  ?>  =(open (decode:stead-update-codec padded))
  ?>  (rejected-wire (cat 3 padded ' '))
  ?>  (rejected-wire '{')
  ?>  (rejected-wire (cat 3 (wire open) 'x'))
  ~
++  test-updates-delayed-old-watch-after-resume
  ^-  tang
  =/  resumed  (execute:stead-updates db view *state:stead-session next.first pages.first bob open(action 'resume', cursor cursor) 1.011 50)
  ?>  =('resumed' (field response.resumed 'status'))
  =/  cancelled  (execute:stead-updates db view *state:stead-session next.resumed pages.resumed bob poll(action 'cancel', cursor '') 1.012 51)
  ?>  =(next.resumed next.cancelled)
  ?>  =(pages.resumed pages.cancelled)
  =/  out  (execute:stead-updates db view *state:stead-session next.cancelled pages.cancelled bob poll 1.013 52)
  ?>  =('refresh_required' (field response.out 'status'))
  ?>  =(next.resumed next.out)
  ?>  =(pages.resumed pages.out)
  ~
++  test-updates-same-rank-access-churn
  ^-  tang
  =/  revoked  (apply-command:stead-team db alice (command 307 100 2 'policy.revoke' ~[['grant_id' (id 501)]]) 1.011)
  ?>  (accepted revoked)
  =/  granted  (apply-command:stead-team next.revoked alice (command 308 100 3 'policy.grant' ~[['grant_id' (id 502)] ['principal_id' principal.identity.bob] ['role' 'contributor'] ['expires_at_ms' '8000000']]) 1.012)
  ?>  (accepted granted)
  ?>  =(2 (role:stead-team next.granted bob (id 100) 1.013))
  =/  out  (execute:stead-updates next.granted (indexed next.granted) *state:stead-session next.first pages.first bob poll 1.013 53)
  ?>  =('refresh_required' (field response.out 'status'))
  ?>  ?=(~ watches.next.out)
  ?>  ?=(~ streams.next.out)
  ?>  ?=(~ cursors.pages.out)
  ~
++  queued
  |=  [count=@ud prior=state:stead-updates pages=state:stead-views]
  ^-  [db=state:stead-team prior=state:stead-updates pages=state:stead-views]
  ?>  (lte count 65)
  =/  data  db
  =/  index=@ud  0
  |-
  ?:  =(index count)  [data prior pages]
  =/  cmd  (command (add 800 index) (add 200 index) 0 'work.create' ~[['title' 'Queued work'] ['description' 'Synthetic'] ['type' 'task'] ['status' 'todo'] ['priority' 'none']])
  =/  changed  (apply-command:stead-team data alice cmd 1.011)
  ?>  (accepted changed)
  =/  out  (advance:stead-updates next.changed *state:stead-session prior pages 1.011)
  $(data next.changed, prior next.out, pages pages.out, index +(index))
++  test-updates-retained-history-sixty-four-then-trim
  ^-  tang
  =/  data  db
  =/  prior  next.first
  =/  pages  pages.first
  =/  current  cursor
  =/  n=@ud  1
  |-
  ?>  (lte n 65)
  =/  cmd  (command (add 900 n) 101 n 'work.update' ~[['title' 'Retained history'] ['description' (decimal:stead-codec n)] ['type' 'task'] ['status' 'todo'] ['priority' 'none']])
  =/  changed  (apply-command:stead-team data alice cmd (add 1.100 n))
  ?>  (accepted changed)
  =/  advanced  (advance:stead-updates next.changed *state:stead-session prior pages (add 1.100 n))
  =/  out  (execute:stead-updates next.changed (indexed next.changed) *state:stead-session next.advanced pages.advanced bob poll(cursor current) (add 1.100 n) (add 500 n))
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
    ~
  $(data next.changed, prior next.out, pages pages.out, current (field response.out 'cursor'), n +(n))
++  test-updates-sixteen-rows-seventeen-overflow
  ^-  tang
  =/  sixteen  (queued 16 next.first pages.first)
  =/  out  (execute:stead-updates db.sixteen (indexed db.sixteen) *state:stead-session prior.sixteen pages.sixteen bob poll 1.012 54)
  =/  rows  (~(got by (value response.out)) 'rows')
  ?>  ?=([%o *] rows)
  ?>  =(16 (lent ~(tap by p.rows)))
  =/  ordered
    |=  n=@ud
    =/  row  (~(got by p.rows) (decimal:stead-codec n))
    ?>  ?=([%o *] row)
    =((decimal:stead-codec +(n)) (field:stead-codec p.row 'sequence'))
  ?>  (levy (gulf 0 15) ordered)
  =/  seventeen  (queued 17 next.first pages.first)
  ?>  closed:(~(got by watches.prior.seventeen) watch)
  ?>  ?=(~ streams.prior.seventeen)
  ?>  ?=(~ cursors.pages.seventeen)
  =/  terminal  (execute:stead-updates db.seventeen (indexed db.seventeen) *state:stead-session prior.seventeen pages.seventeen bob poll 1.012 55)
  ?>  =('refresh_required' (field response.terminal 'status'))
  ?>  (contains:stead-views '"rows":{}' response.terminal)
  ~
++  test-updates-closed-watches-still-bounded
  ^-  tang
  =/  filled
    =/  out  first
    =/  index=@ud  2
    |-
    ?:  =(index 5)  out
    =/  new  (execute:stead-updates db view *state:stead-session next.out pages.out bob open 1.011 index)
    ?>  =('watching' (field response.new 'status'))
    $(out new, index +(index))
  =/  closed  (queued 17 next.filled pages.filled)
  ?>  =(4 (lent ~(tap by watches.prior.closed)))
  ?>  (levy ~(tap by watches.prior.closed) |=([key=@t val=watch-record:stead-updates] &(closed.val ?|(=(expires.val 301.010) =(expires.val 301.011)))))
  =/  out  (execute:stead-updates db.closed (indexed db.closed) *state:stead-session prior.closed pages.closed bob open 1.013 56)
  ?>  =('capacity_exceeded' (field response.out 'error'))
  ?>  ?=(~ streams.next.out)
  ?>  ?=(~ cursors.pages.out)
  ~
++  test-updates-private-projection-isolation
  ^-  tang
  =/  private  (apply-command:stead-team db alice (command 309 104 0 'container.create' ~[['title' 'PRIVATE-CANARY'] ['visibility' 'private']]) 1.011)
  ?>  (accepted private)
  =/  check
    |=  kind=@t
    ^-  ?
    =/  scope  query(kind kind)
    =/  input  open(query scope)
    =/  one  (execute:stead-updates db view *state:stead-session *state:stead-updates *state:stead-views alice input 1.010 60)
    =/  two  (execute:stead-updates db view *state:stead-session next.one pages.one bob input 1.010 61)
    =/  aw  (field response.one 'watch_id')
    =/  bw  (field response.two 'watch_id')
    =/  before-a  (~(got by streams.next.two) stream:(~(got by watches.next.two) aw))
    =/  before-b  (~(got by streams.next.two) stream:(~(got by watches.next.two) bw))
    =/  out  (advance:stead-updates next.private *state:stead-session next.two pages.two 1.012)
    =/  after-a  (~(got by streams.next.out) stream:(~(got by watches.next.out) aw))
    =/  after-b  (~(got by streams.next.out) stream:(~(got by watches.next.out) bw))
    ?&  =(+(sequence.before-a) sequence.after-a)
        !=(generation.before-a generation.after-a)
        =(before-b after-b)
        =(cursor:(~(got by watches.next.two) bw) cursor:(~(got by watches.next.out) bw))
    ==
  ?>  (levy `(list @t)`~['search' 'activity' 'relations'] check)
  ~
++  test-updates-shared-pagination-cap
  ^-  tang
  =/  row  (~(got by cursors.pages.first) cursor)
  =/  pages
    =/  prior  pages.first
    =/  index=@ud  0
    |-
    ?:  =(index 3)  prior
    =/  token  (token:stead-session 70 index 'pagination')
    $(prior prior(cursors (~(put by cursors.prior) token row(purpose 'query', owner '', access ''))), index +(index))
  ?>  =(4 (lent ~(tap by cursors.pages)))
  =/  out  (execute:stead-updates db view *state:stead-session next.first pages bob open 1.011 70)
  ?>  =('capacity_exceeded' (field response.out 'error'))
  ?>  =(next.first next.out)
  ?>  =(pages pages.out)
  =/  cancel  (execute:stead-updates db view *state:stead-session next.first pages bob poll(action 'cancel', cursor '') 1.012 71)
  ?>  =(3 (lent ~(tap by cursors.pages.cancel)))
  ?>  (levy ~(tap by cursors.pages.cancel) |=([key=@t val=cursor-record:stead-views] =('query' purpose.val)))
  ~
++  test-updates-resume-retires-only-own-handles
  ^-  tang
  =/  pending  (begin:stead-session *state:stead-session identity.bob ~zod 'https://home.test' 1.010 80)
  =/  approved  (approve:stead-session next.pending id.pending ~nec identity.bob ~zod 'https://home.test' 'stead.auth/1' 'member-session' 121.010 1.011)
  =/  logged  (consume:stead-session next.approved id.pending cookie.pending identity.bob ~zod 'https://home.test' 1.012 81)
  ?>  =(%accepted status.logged)
  =/  key  (digest:stead-session 'stead.session/1' cookie.logged)
  =/  session  (~(got by sessions.next.logged) key)
  =/  actor  (need (browser-context:stead-team db session 1.013))
  =/  browser  (execute:stead-updates db view next.logged *state:stead-updates *state:stead-views actor open 1.013 82)
  =/  second  (begin:stead-session next.logged identity.bob ~zod 'https://home.test' 1.013 85)
  =/  second-approved  (approve:stead-session next.second id.second ~nec identity.bob ~zod 'https://home.test' 'stead.auth/1' 'member-session' 121.013 1.013)
  =/  second-logged  (consume:stead-session next.second-approved id.second cookie.second identity.bob ~zod 'https://home.test' 1.013 86)
  ?>  =(%accepted status.second-logged)
  =/  second-session  (~(got by sessions.next.second-logged) (digest:stead-session 'stead.session/1' cookie.second-logged))
  =/  second-actor  (need (browser-context:stead-team db second-session 1.013))
  ?>  !=(audit.actor audit.second-actor)
  =/  same-person  (execute:stead-updates db view next.second-logged next.browser pages.browser second-actor open 1.013 87)
  =/  other  (execute:stead-updates db view next.second-logged next.same-person pages.same-person alice open 1.013 83)
  ?>  =(3 (lent ~(tap by watches.next.other)))
  =/  query-token  (token:stead-session 88 1 'query')
  =/  query-record  (~(got by cursors.pages.other) (field response.browser 'cursor'))
  =/  pages  pages.other(cursors (~(put by cursors.pages.other) query-token query-record(purpose 'query', owner '', access '')))
  =/  transient=ephemeral:stead-browser  [next.second-logged pages next.other]
  =/  refused  (call:stead-browser db view transient ['/stead/auth/resume' '{"protocol":"stead.auth/1"}' (token:stead-session 89 1 'unknown-session') '' ''] 1.014 89)
  ?>  =(401 status.refused)
  ?>  =(transient transient.refused)
  ?>  =(db db.refused)
  ?>  =(view view.refused)
  =/  resumed  (call:stead-browser db view transient ['/stead/auth/resume' '{"protocol":"stead.auth/1"}' cookie.logged '' ''] 1.014 84)
  ?>  =(200 status.resumed)
  ?>  =(db db.resumed)
  ?>  =(view view.resumed)
  ?>  =(2 (lent ~(tap by watches.updates.transient.resumed)))
  ?>  (~(has by watches.updates.transient.resumed) (field response.other 'watch_id'))
  ?>  (~(has by watches.updates.transient.resumed) (field response.same-person 'watch_id'))
  ?>  !(~(has by watches.updates.transient.resumed) (field response.browser 'watch_id'))
  ?>  =(2 (lent ~(tap by cursors.pages.transient.resumed)))
  ?>  !(~(has by cursors.pages.transient.resumed) query-token)
  =/  after  (~(got by sessions.auth.transient.resumed) key)
  ?>  =(session(csrf csrf.after) after)
  ?>  !=(csrf.session csrf.after)
  ~
++  test-updates-empty-receipt-is-unconfirmed-only-in-current-scope
  ^-  tang
  =/  empty  query(kind 'receipt', resource (id 399))
  =/  absent  (execute:stead-views db view *state:stead-views bob empty 1.020 301)
  ?>  =('read' (field response.absent 'status'))
  =/  rows  (~(got by (value response.absent)) 'rows')
  ?>  ?=([%o *] rows)
  ?>  ?=(~ p.rows)
  ?>  =('' (field response.absent 'cursor'))
  =/  own  (execute:stead-views db view *state:stead-views bob empty(resource (id 303)) 1.020 302)
  ?>  =('read' (field response.own 'status'))
  ?>  (contains:stead-views '"status":"accepted"' response.own)
  =/  own-rows  (~(got by (value response.own)) 'rows')
  ?>  ?=([%o *] own-rows)
  ?>  =(response.work (canonical:stead-codec (~(got by p.own-rows) '0')))
  =/  foreign  (execute:stead-views db view *state:stead-views alice empty(resource (id 303)) 1.020 303)
  ?>  =('read' (field response.foreign 'status'))
  ?>  !(contains:stead-views '"status":"accepted"' response.foreign)
  =/  foreign-rows  (~(got by (value response.foreign)) 'rows')
  ?>  ?=([%o *] foreign-rows)
  ?>  &(?=(~ p.foreign-rows) =('' (field response.foreign 'cursor')))
  =/  private  (apply-command:stead-team db alice (command 311 111 0 'container.create' ~[['title' 'Private'] ['visibility' 'private']]) 1.021)
  ?>  (accepted private)
  =/  private-db  next.private
  =/  private-query  empty(container (id 111))
  =/  own-empty  (execute:stead-views private-db (indexed private-db) *state:stead-views alice private-query 1.022 304)
  ?>  =('read' (field response.own-empty 'status'))
  =/  private-rows  (~(got by (value response.own-empty)) 'rows')
  ?>  ?=([%o *] private-rows)
  ?>  &(?=(~ p.private-rows) =('' (field response.own-empty 'cursor')))
  =/  denied  (execute:stead-views private-db (indexed private-db) *state:stead-views bob private-query 1.022 305)
  ?>  =('denied_or_not_found' (field response.denied 'error'))
  =/  unknown-box  (execute:stead-views db view *state:stead-views bob empty(container (id 112)) 1.022 306)
  ?>  =(response.denied response.unknown-box)
  =/  wrong-scope  (execute:stead-views db view *state:stead-views bob empty(resource (id 303), container (id 112)) 1.022 310)
  ?>  =(response.denied response.wrong-scope)
  =/  revoked  (apply-command:stead-team db alice (command 312 100 2 'policy.revoke' ~[['grant_id' (id 501)]]) 1.023)
  ?>  (accepted revoked)
  =/  after  (execute:stead-views next.revoked (indexed next.revoked) *state:stead-views bob empty 1.024 307)
  ?>  =(response.denied response.after)
  =/  old-receipt  (execute:stead-views next.revoked (indexed next.revoked) *state:stead-views bob empty(resource (id 303)) 1.024 311)
  ?>  =(response.denied response.old-receipt)
  =/  stale-actor  bob(identity identity.bob(revision 2))
  =/  stale  (execute:stead-views db view *state:stead-views stale-actor empty 1.024 308)
  ?>  =(response.denied response.stale)
  =/  wrong-project  (execute:stead-views private-db (indexed private-db) *state:stead-views alice private-query(project (id 199)) 1.024 309)
  ?>  =(response.denied response.wrong-project)
  ~
++  test-updates-paginated-refresh-reclaims-only-own-query-walk
  ^-  tang
  =/  many  (queued 21 next.first pages.first)
  =/  data  db.many
  =/  index  (indexed data)
  =/  initial  (execute:stead-views data index pages.first bob query 1.014 190)
  =/  original  (field response.initial 'cursor')
  ?>  (opaque:stead-team-codec original)
  =/  other  (execute:stead-views data index next.initial alice query 1.014 191)
  =/  foreign  (field response.other 'cursor')
  =/  refreshed
    =/  out  other
    =/  n=@ud  0
    |-
    ?:  =(n 6)  out
    =/  fresh  (execute:stead-views data index next.out bob query 1.015 (add 192 n))
    ?>  =('read' (field response.fresh 'status'))
    ?>  =(3 (lent ~(tap by cursors.next.fresh)))
    ?>  (~(has by cursors.next.fresh) foreign)
    ?>  (~(has by cursors.next.fresh) cursor)
    $(out fresh, n +(n))
  =/  token  (field response.refreshed 'cursor')
  =/  meta  (execute:stead-views data index next.refreshed bob query(kind 'project') 1.016 199)
  ?>  =('read' (field response.meta 'status'))
  ?>  (~(has by cursors.next.meta) token)
  =/  single  (execute:stead-views data index next.meta bob query(resource (id 101)) 1.017 200)
  ?>  =('read' (field response.single 'status'))
  ?>  (~(has by cursors.next.single) token)
  =/  old  (execute:stead-views data index next.single bob query(cursor original) 1.018 201)
  ?>  =('stale_cursor' (field response.old 'error'))
  ?>  =(next.single next.old)
  =/  second  (execute:stead-views data index next.old bob query(cursor token) 1.018 202)
  ?>  =('read' (field response.second 'status'))
  ?>  =('' (field response.second 'cursor'))
  ?>  =(2 (lent ~(tap by cursors.next.second)))
  ?>  (~(has by cursors.next.second) foreign)
  ?>  (~(has by cursors.next.second) cursor)
  ~
--
