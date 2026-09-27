::  Current subscription authorization at open and dequeue.
/+  stead-codec, stead-team, stead-team-codec, stead-session, stead-views, stead-core
=,  stead-codec
|%
++  current
  |=  [db=state:stead-team sessions=state:stead-session actor=authentication:stead-team now=@ud]
  ^-  ?
  ?.  (current:stead-team db actor now)  |
  ?:  =('native-sender/1' method.actor)
    =/  fresh  (native-context:stead-team db ship.identity.actor now)
    ?~  fresh  |
    =(actor u.fresh)
  =/  matches
    (skim ~(tap by sessions.sessions) |=([key=@t row=session:stead-session] =(audit.actor audit.row)))
  ?.  ?=([^ ~] matches)  |
  =/  derived  (browser-context:stead-team db q.i.matches now)
  ?~  derived  |
  =(actor u.derived)
++  allowed
  |=  [db=state:stead-team sessions=state:stead-session actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  ?
  &((current db sessions actor now) (authorized:stead-views db actor query now))
++  access
  ::  No content counter: same-rank grant churn changes the principal's access
  ::  generation. Inaccessible project/private-scope mutations are not inputs.
  |=  [db=state:stead-team actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  @t
  =/  rows  ~(tap by projects.data.db)
  =/  selected=(map @t [epoch=@ud rank=@ud generation=@ud])  ~
  |-
  ?~  rows
    (hash 'stead.update-access/3' (bytes-hex (jam [actor query(request '', cursor '') selected])))
  =/  id  p.i.rows
  =/  rank  (role:stead-team db actor id now)
  ?.  &(?|(=('projects' kind.query) =(project.query id)) (gth rank 0))
    $(rows t.rows)
  =/  counter  (~(get by generations.db) [id (cat 3 'access:' principal.identity.actor)])
  $(rows t.rows, selected (~(put by selected) id [epoch.q.i.rows rank ?~(counter 0 u.counter)]))
--
