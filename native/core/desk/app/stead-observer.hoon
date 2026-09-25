::  Test-only persistent Gall observer. Never an authority or employee API.
::  Stores bounded event metadata/digests, not page bodies or receipt contents.
/+  default-agent, stead-codec
=>
|%
+$  observation
  $:  kind=@t  source=@p  wire=@t  mark=@t  size=@ud  digest=@t
      provenance=@t  at=@ud  terminal=?
  ==
+$  probe
  $:  route=@t  watch=?  leaving=?  closed=?  facts=@ud  kicks=@ud
      watch-acks=@ud  watch-nacks=@ud  poke-acks=@ud  poke-nacks=@ud
      pokes=@ud  events=(map @ud observation)
  ==
+$  saved
  [%stead-observer %1 probes=(map @t probe) count=@ud fault=@t]
++  digest
  |=  raw=@t
  (hex:stead-codec 64 (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))
++  milliseconds
  |=  now=@da
  (div (mul 1.000 (sub now ~1970.1.1)) ~s1)
++  native-path
  |=  raw=@t
  ^-  path
  ?>  &((gth (met 3 raw) 0) (lte (met 3 raw) 1.024))
  =/  bytes  (rip 3 raw)
  ?>  ?=(^ bytes)
  ?>  =(47 i.bytes)
  =/  bytes  t.bytes
  =/  out=path  ~
  =/  part=@t  ''
  |-
  ?>  (lte (lent out) 8)
  ?~  bytes
    ?:  =('' part)  ?>(=(~ out) ~)
    ?>  (lth (lent out) 8)
    (flop [part out])
  ?:  =(47 i.bytes)
    ?>  !=('' part)
    $(bytes t.bytes, out [part out], part '')
  ?>  ?|  &((gte i.bytes 48) (lte i.bytes 57))
          &((gte i.bytes 65) (lte i.bytes 90))
          &((gte i.bytes 97) (lte i.bytes 122))
          =(45 i.bytes)  =(46 i.bytes)  =(95 i.bytes)  =(126 i.bytes)
      ==
  =.  part  (cat 3 part i.bytes)
  ?>  (lte (met 3 part) 128)
  $(bytes t.bytes)
++  event-json
  |=  value=observation
  %-  object:stead-codec
  :~  ['kind' kind.value]
      ['source_ship' (scot %p source.value)]
      ['peer_agent' 'stead-home']
      ['peer_agent_basis' 'fixed issued Gall wire; sign has no agent field']
      ['wire' wire.value]
      ['mark' mark.value]
      ['payload_bytes' (decimal:stead-codec size.value)]
      ['payload_sha256' digest.value]
      ['source_provenance_sha256' provenance.value]
      ['observed_at_ms' (decimal:stead-codec at.value)]
      ['after_terminal' ?:(terminal.value 'true' 'false')]
  ==
++  probe-json
  |=  [id=@t value=probe ongoing=? fault=@t]
  ^-  json
  =/  base
    %-  object:stead-codec
    :~  ['protocol' 'stead.observer/1']
        ['id' id]
        ['status' ?:(!=('' fault) 'failed' 'observed')]
        ['fault' fault]
        ['route' route.value]
        ['watch_requested' ?:(watch.value 'true' 'false')]
        ['leave_requested' ?:(leaving.value 'true' 'false')]
        ['closed' ?:(closed.value 'true' 'false')]
        ['ongoing_subscription' ?:(ongoing 'true' 'false')]
        ['facts' (decimal:stead-codec facts.value)]
        ['kicks' (decimal:stead-codec kicks.value)]
        ['watch_acks' (decimal:stead-codec watch-acks.value)]
        ['watch_nacks' (decimal:stead-codec watch-nacks.value)]
        ['poke_acks' (decimal:stead-codec poke-acks.value)]
        ['poke_nacks' (decimal:stead-codec poke-nacks.value)]
        ['pokes_requested' (decimal:stead-codec pokes.value)]
    ==
  ?>  ?=([%o *] base)
  =/  events=json
    :-  %o
    %-  malt
    %+  turn  ~(tap by events.value)
    |=  [number=@ud row=observation]
    [(decimal:stead-codec number) (event-json row)]
  [%o (~(put by p.base) 'events' events)]
--
=|  probes=(map @t probe)
=|  count=@ud
=|  fault=@t
^-  agent:gall
|_  =bowl:gall
+*  this  .
    def  ~(. (default-agent this %|) bowl)
++  on-init
  ?>  ?|(=(our.bowl ~zod) =(our.bowl ~bus) =(our.bowl ~nec) =(our.bowl ~bud))
  `this
++  on-save
  !>([%stead-observer %1 probes count fault])
++  on-load
  |=  old=vase
  ~|  %stead-observer-unsupported-state
  =/  restored  !<(saved old)
  ?>  &((lte count.restored 256) (lte (lent ~(tap by probes.restored)) 80))
  =/  total
    %+  roll  ~(tap by probes.restored)
    |=  [pair=[@t probe] sum=@ud]
    (add sum (lent ~(tap by events.+.pair)))
  ?>  =(count.restored total)
  `this(probes probes.restored, count count.restored, fault fault.restored)
++  on-poke
  |=  [=mark =vase]
  ^-  (quip card:agent:gall _this)
  ~|  %stead-observer-control-denied
  ?>  &(=(src.bowl our.bowl) =(%stead-observer-1 mark) =('' fault))
  =/  raw  !<(@t vase)
  =/  parsed  (need (parse-result:stead-codec raw))
  ?>  ?=([%o *] parsed)
  =/  fields  p.parsed
  ?>  (keys:stead-codec fields ~['action' 'id' 'target' 'route' 'raw'])
  =/  action  (field:stead-codec fields 'action')
  =/  id  (field:stead-codec fields 'id')
  =/  route  (field:stead-codec fields 'route')
  =/  command  (field:stead-codec fields 'raw')
  ?>  &((uuid:stead-codec id) =('~zod' (field:stead-codec fields 'target')))
  =/  existing  (~(get by probes) id)
  ?:  =('watch' action)
    ?>  &(?=(~ existing) =('' command) (lth (lent ~(tap by probes)) 80))
    =/  path  (native-path route)
    =/  value=probe  [route & | | 0 0 0 0 0 0 0 ~]
    :_  this(probes (~(put by probes) id value))
    ~[[%pass /probe/[id]/watch %agent [~zod %stead-home] %watch path]]
  ?:  =('poke' action)
    ?>  &(=('' route) (lte (met 3 command) 65.536))
    ?>  ?|(?=(^ existing) (lth (lent ~(tap by probes)) 80))
    =/  value=probe  ?~(existing ['' | | | 0 0 0 0 0 0 0 ~] u.existing)
    ?>  (lth pokes.value 4)
    :_  this(probes (~(put by probes) id value(pokes +(pokes.value))))
    ~[[%pass /probe/[id]/poke %agent [~zod %stead-home] %poke %stead-command-2 !>(command)]]
  ?:  =('leave-ended' action)
    ?>  &(=('' route) =('' command) ?=(^ existing))
    =/  value  u.existing
    ?>  &(watch.value ?|(closed.value leaving.value))
    ::  Test only: ask Gall to leave the retained original wire. No new watch,
    ::  fabricated sign, new route, or business authority is created.
    :_  this
    ~[[%pass /probe/[id]/watch %agent [~zod %stead-home] %leave ~]]
  ?>  &(=('leave' action) =('' route) =('' command) ?=(^ existing))
  =/  value  u.existing
  ?>  &(watch.value !leaving.value !closed.value)
  :_  this(probes (~(put by probes) id value(leaving &)))
  ~[[%pass /probe/[id]/watch %agent [~zod %stead-home] %leave ~]]
++  on-agent
  |=  [=wire =sign:agent:gall]
  ^-  (quip card:agent:gall _this)
  =/  record
    |=  [id=@t lane=@t value=probe kind=@t mark=@t size=@ud bytes-digest=@t terminal=? failure=@t]
    ^-  (quip card:agent:gall _this)
    =/  expected-lane
      ?:(?|(=('poke-ack' kind) =('poke-nack' kind)) 'poke' 'watch')
    =.  failure  ?:(=(lane expected-lane) failure 'Unexpected native sign lane')
    =/  source-provenance  (jam sap.bowl)
    =/  text-wire  (cat 3 '/probe/' (cat 3 id (cat 3 '/' lane)))
    =/  event=observation
      [kind src.bowl text-wire mark size bytes-digest (digest source-provenance) (milliseconds now.bowl) terminal]
    =.  value  value(events (~(put by events.value) +(count) event))
    `this(probes (~(put by probes) id value), count +(count), fault failure)
  ?:  !=('' fault)  `this
  ?.  &(?=([%probe @ @ ~] wire) =(src.bowl ~zod))
    `this(fault 'Unexpected native source or wire')
  =/  id  i.t.wire
  =/  lane  i.t.t.wire
  =/  found  (~(get by probes) id)
  ?~  found  `this(fault 'Native event for unknown probe')
  ?.  ?|(=(lane %watch) =(lane %poke))  `this(fault 'Unexpected probe lane')
  ?:  (gte count 256)
    =/  cards=(list card:agent:gall)
      %+  turn  ~(tap by wex.bowl)
      |=  [[route=wire ship=@p name=@tas] [acked=? path=path]]
      [%pass route %agent [ship name] %leave ~]
    [cards this(fault 'Observer event capacity exceeded')]
  =/  value  u.found
  =/  was-terminal  |(closed.value leaving.value)
  =/  kind=@t  ''
  =/  mark=@t  ''
  =/  size=@ud  0
  =/  bytes-digest=@t  ''
  ?-  -.sign
    %fact
      =.  kind  'fact'
      =.  mark  p.cage.sign
      =.  value  value(facts +(facts.value))
      =/  extracted  (mule |.(!<(@t q.cage.sign)))
      ?:  ?=(%| -.extracted)
        (record id lane value 'invalid-fact' mark 0 '' was-terminal 'Non-cord fact payload')
      =/  body  p.extracted
      ?:  (gth (met 3 body) 262.144)
        (record id lane value 'invalid-fact' mark (met 3 body) '' was-terminal 'Oversized fact payload')
      =.  size  (met 3 body)
      =.  bytes-digest  (digest body)
      (record id lane value kind mark size bytes-digest was-terminal '')
    %kick
      =.  value  value(kicks +(kicks.value), closed &)
      (record id lane value 'kick' mark size bytes-digest was-terminal '')
    %watch-ack
      ?~  p.sign
        =.  value  value(watch-acks +(watch-acks.value))
        (record id lane value 'watch-ack' mark size bytes-digest was-terminal '')
      =.  value  value(watch-nacks +(watch-nacks.value), closed &)
      (record id lane value 'watch-nack' mark size bytes-digest was-terminal '')
    %poke-ack
      ?~  p.sign
        =.  value  value(poke-acks +(poke-acks.value))
        (record id lane value 'poke-ack' mark size bytes-digest was-terminal '')
      =.  value  value(poke-nacks +(poke-nacks.value))
      (record id lane value 'poke-nack' mark size bytes-digest was-terminal '')
  ==
++  on-watch
  |=  route=path
  ^-  (quip card:agent:gall _this)
  ~|  %stead-observer-query-denied
  ?>  =(src.bowl our.bowl)
  =/  result=json
    ?:  =(route /v1/observer-summary)
      %-  object:stead-codec
      :~  ['protocol' 'stead.observer-summary/1']
          ['status' ?:(!=('' fault) 'failed' 'observed')]
          ['fault' fault]
          ['probes' (decimal:stead-codec (lent ~(tap by probes)))]
          ['events' (decimal:stead-codec count)]
          ['ongoing_subscriptions' (decimal:stead-codec (lent ~(tap by wex.bowl)))]
      ==
    ?>  ?=([%v1 %observer @ ~] route)
    =/  id  i.t.t.route
    =/  found  (~(got by probes) id)
    =/  ongoing  (~(has by wex.bowl) [/probe/[id]/watch ~zod %stead-home])
    (probe-json id found ongoing fault)
  =/  raw  (canonical:stead-codec result)
  ?>  (lte (met 3 raw) 262.144)
  :_  this
  :~  [%give %fact ~ %stead-result-2 !>(raw)]
      [%give %kick ~ ~]
  ==
++  on-leave  on-leave:def
++  on-peek   on-peek:def
++  on-arvo   on-arvo:def
++  on-fail   on-fail:def
--
