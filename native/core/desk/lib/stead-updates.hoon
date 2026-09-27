::  Bounded subscriptions. Ephemeral; never include in on-save.
::  Update and pagination cursors share one bounded purpose-tagged store.
/+  stead-codec, stead-team, stead-team-codec, stead-session, stead-views, stead-projection, stead-update-codec, stead-update-security
=,  stead-codec
|%
+$  invalidation  [sequence=@ud generation=@t]
+$  stream
  $:  actor=authentication:stead-team  query=query:stead-team-codec
      access=@t  generation=@t  sequence=@ud  rows=(list invalidation)
  ==
+$  watch-record
  $:  actor=authentication:stead-team  query=query:stead-team-codec
      access=@t  stream=@t  cursor=@t  seen=@ud  expires=@ud  closed=?
  ==
+$  state
  [counter=@ud streams=(map @t stream) watches=(map @t watch-record)]
+$  result  [response=@t next=state pages=state:stead-views]
++  drop
  |=  [prior=state pages=state:stead-views watch=@t]
  ^-  [next=state pages=state:stead-views]
  =/  cursors=(map @t cursor-record:stead-views)
    (malt (skip ~(tap by cursors.pages) |=([key=@t val=cursor-record:stead-views] &(=('updates' purpose.val) =(watch owner.val)))))
  =/  watches  (~(del by watches.prior) watch)
  =/  needed
    (silt (turn (skip ~(tap by watches) |=([key=@t val=watch-record] closed.val)) |=([key=@t val=watch-record] stream.val)))
  =/  streams=(map @t stream)
    (malt (skim ~(tap by streams.prior) |=([key=@t val=stream] (~(has in needed) key))))
  [prior(watches watches, streams streams) pages(cursors cursors)]
++  forget-session
  ::  A reloaded browser cannot recover its old in-memory read handles. Retire
  ::  only this session's watches/cursors; business receipts remain untouched.
  |=  [prior=state pages=state:stead-views audit=@t]
  ^-  [next=state pages=state:stead-views]
  ?>  (token-valid:stead-session audit)
  =.  pages
    pages(cursors (malt (skip ~(tap by cursors.pages) |=([key=@t val=cursor-record:stead-views] =(audit audit.actor.val)))))
  =/  retired=(list @t)
    (turn (skim ~(tap by watches.prior) |=([key=@t val=watch-record] =(audit audit.actor.val))) |=([key=@t val=watch-record] key))
  |-
  ?~  retired  [prior pages]
  =/  out  (drop prior pages i.retired)
  $(prior next.out, pages pages.out, retired t.retired)
++  prune
  |=  [db=state:stead-team sessions=state:stead-session prior=state pages=state:stead-views now=@ud]
  ^-  [next=state pages=state:stead-views]
  =/  watches=(map @t watch-record)
    %-  malt
    %+  skim  ~(tap by watches.prior)
    |=  [key=@t val=watch-record]
    ?&  (gth expires.val now)
        (allowed:stead-update-security db sessions actor.val query.val now)
        =(access.val (access:stead-update-security db actor.val query.val now))
    ==
  =/  cursors=(map @t cursor-record:stead-views)
    %-  malt
    %+  skim  ~(tap by cursors.pages)
    |=  [key=@t val=cursor-record:stead-views]
    ?.  (gth expires.val now)  |
    ?:  =('query' purpose.val)  &
    ?.  =('updates' purpose.val)  |
    =/  watch  (~(get by watches) owner.val)
    ?~  watch  |
    ?&  !closed.u.watch  =(key cursor.u.watch)  =(actor.val actor.u.watch)
        =(access.val access.u.watch)  =(query.val query.u.watch)
    ==
  =/  needed
    (silt (turn (skip ~(tap by watches) |=([key=@t val=watch-record] closed.val)) |=([key=@t val=watch-record] stream.val)))
  =/  streams=(map @t stream)
    (malt (skim ~(tap by streams.prior) |=([key=@t val=stream] (~(has in needed) key))))
  [prior(watches watches, streams streams) pages(cursors cursors)]
++  advance
  ::  Call after each accepted command in both transports; repeated/denied
  ::  commands leave generations unchanged and cannot append duplicate rows.
  |=  [db=state:stead-team sessions=state:stead-session prior=state pages=state:stead-views now=@ud]
  ^-  [next=state pages=state:stead-views]
  =/  clean  (prune db sessions prior pages now)
  =.  prior  next.clean
  =.  pages  pages.clean
  =/  retired
    %-  silt
    %+  turn
      %+  skim  ~(tap by streams.prior)
      |=  [key=@t val=stream]
      &((gte sequence.val 18.446.744.073.709.551.615) !=(generation.val (generation:stead-views db actor.val query.val now)))
    |=  [key=@t val=stream]
    key
  =/  streams=(map @t stream)
    %-  malt
    %+  turn  (skip ~(tap by streams.prior) |=([key=@t val=stream] (~(has in retired) key)))
    |=  [key=@t val=stream]
    =/  generation  (generation:stead-views db actor.val query.val now)
    ?:  =(generation generation.val)  [key val]
    =/  next=@ud  +(sequence.val)
    =/  appended=(list invalidation)  [[next generation] rows.val]
    [key val(generation generation, sequence next, rows (scag 64 appended))]
  =/  watches=(map @t watch-record)
    %-  malt
    %+  turn  ~(tap by watches.prior)
    |=  [key=@t val=watch-record]
    ?:  closed.val  [key val]
    ?:  (~(has in retired) stream.val)
      [key val(stream '', cursor '', seen 0, closed &)]
    =/  current  (~(got by streams) stream.val)
    ?>  (gte sequence.current seen.val)
    ?:  (lte (sub sequence.current seen.val) 16)  [key val]
    ::  Closed terminal counts against the same caps and keeps its deadline.
    [key val(stream '', cursor '', seen 0, closed &)]
  (prune db sessions prior(streams streams, watches watches) pages now)
++  error
  |=  [request=@t why=@t prior=state pages=state:stead-views]
  ^-  result
  [(canonical (object ~[['protocol' 'stead.update-result/3'] ['status' 'rejected'] ['request_id' request] ['error' why]])) prior pages]
++  reply
  |=  [request=@t status=@t watch=@t cursor=@t generation=@t rows=(list invalidation) prior=state pages=state:stead-views]
  ^-  result
  ?>  (lte (lent rows) 16)
  =/  out=object-map  ~
  =/  index=@ud  0
  |-
  ?~  rows
    =/  fields  (fields:stead-views ~[['protocol' 'stead.update-result/3'] ['status' status] ['request_id' request] ['watch_id' watch] ['cursor' cursor] ['generation' generation]])
    [(canonical [%o (~(put by fields) 'rows' [%o out])]) prior pages]
  =/  row  (object ~[['sequence' (decimal sequence.i.rows)] ['generation' generation.i.rows]])
  $(rows t.rows, index +(index), out (~(put by out) (decimal index) row))
++  cursor
  |=  [db=state:stead-team prior=state:stead-views actor=authentication:stead-team query=query:stead-team-codec access=@t watch=@t sequence=@ud generation=@t expires=@ud now=@ud entropy=@]
  ^-  (unit [pages=state:stead-views token=@t])
  ?:  ?|  (gte counter.prior 18.446.744.073.709.551.615)
          (gte (lent ~(tap by cursors.prior)) 64)
          (gte (lent (skim ~(tap by cursors.prior) |=([key=@t val=cursor-record:stead-views] =(principal.identity.actor principal.identity.actor.val)))) 4)
      ==
    ~
  =/  counter  +(counter.prior)
  =/  token  (token:stead-session entropy counter 'stead.updates.cursor/3')
  ?:  (~(has by cursors.prior) token)  ~
  =/  rank  ?:(=('' project.query) 0 (role:stead-team db actor project.query now))
  =/  epoch  ?:(=('' project.query) 0 epoch:(~(got by projects.data.db) project.query))
  =/  record=cursor-record:stead-views
    [actor query generation rank epoch sequence expires 'updates' watch access]
  (some [prior(counter counter, cursors (~(put by cursors.prior) token record)) token])
++  execute
  |=  [db=state:stead-team view=state:stead-projection sessions=state:stead-session prior=state pages=state:stead-views actor=authentication:stead-team input=envelope:stead-update-codec now=@ud entropy=@]
  ^-  result
  =/  request  request.input
  ?.  (current:stead-update-security db sessions actor now)
    (error request 'denied_or_not_found' prior pages)
  ::  Cleanup needs current identity/ownership, not a usable read projection.
  ?:  =('cancel' action.input)
    =/  found  (~(get by watches.prior) watch.input)
    ?:  ?~(found & !=(actor actor.u.found))
      (reply request 'cancelled' watch.input '' '' ~ prior pages)
    =/  removed  (drop prior pages watch.input)
    (reply request 'cancelled' watch.input '' '' ~ next.removed pages.removed)
  ?.  (ready:stead-projection db view)
    (error request 'projection_unavailable' prior pages)
  =/  clean  (advance db sessions prior pages now)
  =.  prior  next.clean
  =.  pages  pages.clean
  =/  action  action.input
  ?:  ?|(=('poll' action) =('cancel' action))
    =/  watch  watch.input
    =/  found  (~(get by watches.prior) watch)
    ?~  found
      (reply request ?:(=('cancel' action) 'cancelled' 'refresh_required') watch '' '' ~ prior pages)
    ::  Do not remove any watch/cursor because another actor supplied its ID.
    ?.  =(actor actor.u.found)
      (reply request ?:(=('cancel' action) 'cancelled' 'refresh_required') watch '' '' ~ prior pages)
    =/  row  u.found
    ?:  =('cancel' action)
      =/  removed  (drop prior pages watch)
      (reply request 'cancelled' watch '' '' ~ next.removed pages.removed)
    ?:  closed.row
      =/  removed  (drop prior pages watch)
      (reply request 'refresh_required' watch '' '' ~ next.removed pages.removed)
    =/  provided  (~(get by cursors.pages) cursor.input)
    ::  A known foreign/pagination cursor never triggers another watch's cleanup.
    ?:  ?&  ?=(^ provided)
            ?|  !=('updates' purpose.u.provided)  !=(watch owner.u.provided)
                !=(actor actor.u.provided)
            ==
        ==
      (reply request 'refresh_required' watch '' '' ~ prior pages)
    ?.  &(?=(^ provided) =(cursor.input cursor.row))
      =/  removed  (drop prior pages watch)
      (reply request 'refresh_required' watch '' '' ~ next.removed pages.removed)
    =/  current  (~(got by streams.prior) stream.row)
    =/  rows  (flop (skim rows.current |=(item=invalidation (gth sequence.item seen.row))))
    ?>  (lte (lent rows) 16)
    =/  expires  (min expires.actor (add now 300.000))
    =/  trial  pages(cursors (~(del by cursors.pages) cursor.row))
    =/  fresh  (cursor db trial actor query.row access.row watch sequence.current generation.current expires now entropy)
    ?~  fresh  (error request 'capacity_exceeded' prior pages)
    ?:  (~(has by cursors.pages) token.u.fresh)
      (error request 'capacity_exceeded' prior pages)
    =/  next  prior(watches (~(put by watches.prior) watch row(cursor token.u.fresh, seen sequence.current, expires expires)))
    (reply request 'updated' watch token.u.fresh generation.current rows next pages.u.fresh)
  =/  query  query.input(request '', cursor '')
  ?.  (allowed:stead-update-security db sessions actor query now)
    (error request 'denied_or_not_found' prior pages)
  =/  access  (access:stead-update-security db actor query now)
  =/  key  (hash 'stead.update-scope/3' (bytes-hex (jam [actor query access])))
  =/  stored  (~(get by streams.prior) key)
  =/  current=stream
    ?~  stored
      [actor query access (generation:stead-views db actor query now) 0 ~]
    u.stored
  =/  seen  sequence.current
  =/  old-watch=@t  ''
  ?:  &(!=('open' action) !=('resume' action))
    (error request 'invalid_update' prior pages)
  =/  resumed=(unit cursor-record:stead-views)  (~(get by cursors.pages) cursor.input)
  ?:  &(=('resume' action) ?~(resumed & ?|(!=('updates' purpose.u.resumed) !=(actor actor.u.resumed) !=(query query.u.resumed) !=(access access.u.resumed))))
    (reply request 'refresh_required' '' '' '' ~ prior pages)
  =?  old-watch  =('resume' action)  owner:(need resumed)
  =?  seen  =('resume' action)  offset:(need resumed)
  ?:  ?|  (gth seen sequence.current)
          (gth (sub sequence.current seen) 64)
          (gth (sub sequence.current seen) 16)
      ==
    (reply request 'refresh_required' '' '' '' ~ prior pages)
  =/  staged=[next=state pages=state:stead-views]
    ?:(=('resume' action) (drop prior pages old-watch) [prior pages])
  =/  next  next.staged
  =/  next-pages  pages.staged
  ?:  ?|  (gte counter.next 18.446.744.073.709.551.615)
          (gte (lent ~(tap by watches.next)) 64)
          (gte (lent (skim ~(tap by watches.next) |=([id=@t val=watch-record] =(principal.identity.actor principal.identity.actor.val)))) 4)
          &(!(~(has by streams.next) key) (gte (lent ~(tap by streams.next)) 64))
      ==
    (error request 'capacity_exceeded' prior pages)
  =/  counter  +(counter.next)
  =/  watch  (token:stead-session entropy counter 'stead.watch/3')
  ?:  (~(has by watches.prior) watch)  (error request 'capacity_exceeded' prior pages)
  =/  expires  (min expires.actor (add now 300.000))
  =/  fresh  (cursor db next-pages actor query access watch seen generation.current expires now entropy)
  ?~  fresh  (error request 'capacity_exceeded' prior pages)
  ?:  (~(has by cursors.pages) token.u.fresh)
    (error request 'capacity_exceeded' prior pages)
  =/  record=watch-record  [actor query access key token.u.fresh seen expires |]
  =.  next  next(counter counter, streams (~(put by streams.next) key current), watches (~(put by watches.next) watch record))
  ::  Resume does not silently skip its suffix; the next poll returns it. The
  ::  caller opens before reading a snapshot, never after a stale snapshot.
  (reply request ?:(=('resume' action) 'resumed' 'watching') watch token.u.fresh generation.current ~ next pages.u.fresh)
--
