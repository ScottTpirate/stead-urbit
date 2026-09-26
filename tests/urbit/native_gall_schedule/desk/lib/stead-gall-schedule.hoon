::  Draft native Gall schedule. No Ames, UDP or wall-clock claim.
::  Gall setup adapted from pinned Urbit lib/test/ames-gall.hoon (MIT).
::  See tests/urbit/native_gall_schedule/README.md and UPSTREAM_LICENSE.txt.
/+  stead-codec, inputs=stead-gall-schedule-inputs
/=  gall-raw  /sys/vane/gall
/=  home-agent  /app/stead-home
/=  observer-agent  /app/stead-observer
=/  gall-bunt  (gall-raw ~zod)
=>
|%
++  make-gall
  |=  who=ship
  =/  pupa  (gall-raw who)
  =/  adult  (pupa now=~2026.9.25 eny=`@`0xdead.beef scry=*roof)
  =+  [out next]=(call:adult duct=~[/init] dud=~ task=[%init ~])
  ?>  =(~ out)
  next
--
=/  gall-adult  (make-gall ~zod)
|%
+$  machine  _gall-adult
+$  motion  move:gall-bunt
+$  passage  [parent=duct tag=%pass link=wire vane=%g input=task:gall]
++  call
  |=  [state=machine return=duct input=(hobo task:gall)]
  (call:(state ~2026.9.25 `@`0xdead.beef *roof) return ~ input)
++  take
  |=  [state=machine link=wire return=duct input=sign-arvo]
  (take:(state ~2026.9.25 `@`0xdead.beef *roof) link return ~ input)
++  load-agent
  |=  [who=ship state=machine app=term implementation=agent:gall]
  =^  load-moves  state
    %+  call  state
    [~[/load] load/[[app [who %base da+~2026.9.25] implementation]~]]
  =^  ready-moves  state
    =/  response=sign-arvo
      :+  %clay  %writ
      `[[%a da+~2026.9.25 %base] /app/[app]/hoon vase+!>(!>(implementation))]
    %:  take
      state
      /sys/cor/[app]/(scot %p who)/base/(scot %da ~2026.9.25)
      ~[/load]
      response
    ==
  ::  These outputs are Clay/bootstrap plumbing, not app delivery evidence.
  state
++  input-duct
  |=  message=motion
  ?>  ?=([* %pass * %g %deal *] message)
  =/  sent=passage  message
  [link.sent parent.sent]
++  dispatch
  |=  [state=machine message=motion]
  ?>  ?=([* %pass * %g %deal *] message)
  =/  sent=passage  message
  (call state (input-duct message) input.sent)
++  one-pass
  |=  moves=(list motion)
  ^-  motion
  ?>  (lte (lent moves) 4)
  =/  sent
    (skim moves |=(message=motion ?=([* %pass * %g %deal *] message)))
  ?>  =(1 (lent sent))
  ?>  ?=(^ sent)
  ::  The other output is the native ACK of the owner-local observer control.
  =/  other  (skip moves |=(message=motion ?=([* %pass * %g %deal *] message)))
  ?>  =(1 (lent other))
  ?>  ?=(^ other)
  ?>  ?=([* %give %unto %poke-ack ~] i.other)
  i.sent
++  deliver
  |=  [state=machine moves=(list motion)]
  ^-  machine
  ?>  (lte (lent moves) 8)
  |-
  ?~  moves  state
  =/  message  i.moves
  ?>  ?=([^ %give %unto *] message)
  =/  address  duct.message
  =^  replies  state
    (take state i.address t.address [%gall +.move.message])
  ::  The real observer should emit no follow-up effects for these signs.
  ?>  =(~ replies)
  $(moves t.moves)
++  just-ack
  |=  moves=(list motion)
  ^-  ?
  ?~  moves  |
  &(=(1 (lent moves)) ?=([* %give %unto %poke-ack ~] i.moves))
++  query
  |=  [state=machine who=ship app=term route=path]
  ^-  [raw=@t next=machine]
  =^  moves  state
    (call state ~[/schedule/query] [%deal [who who /] app %watch route])
  ?>  =(3 (lent moves))
  =/  facts  (skim moves |=(message=motion ?=([* %give %unto %fact *] message)))
  =/  kicks  (skim moves |=(message=motion ?=([* %give %unto %kick ~] message)))
  =/  acks  (skim moves |=(message=motion ?=([* %give %unto %watch-ack ~] message)))
  ?>  &(=(1 (lent facts)) =(1 (lent kicks)) =(1 (lent acks)))
  ?>  ?=(^ facts)
  =/  message  i.facts
  ?>  ?=([* %give %unto %fact *] message)
  =/  [return=duct a=@ b=@ c=@ result=cage]  message
  ?>  =(%stead-result-2 p.result)
  [!<(@t q.result) state]
++  field
  |=  [raw=@t name=@t]
  ^-  @t
  =/  value  (need (parse-result:stead-codec raw))
  ?>  ?=([%o *] value)
  (field:stead-codec p.value name)
++  incoming
  |=  state=machine
  ^-  bitt:gall
  =/  current  (state ~2026.9.25 `@`0xdead.beef *roof)
  =/  yoke  (~(got by yokes.state.current) %stead-home)
  ?>  ?=(%live -.yoke)
  ?>  (lte (lent ~(tap by bitt.yoke)) 4)
  bitt.yoke
++  observe
  |=  [state=machine id=@t]
  (query state ~bus %stead-observer /v1/observer/[id])
++  control
  |=  [state=machine action=@t id=@t route=@t command=@t]
  =/  raw
    %-  canonical:stead-codec
    %-  object:stead-codec
    :~  ['action' action]  ['id' id]  ['target' '~zod']
        ['route' route]  ['raw' command]
    ==
  (call state ~[/schedule/control] [%deal [~bus ~bus /] %stead-observer %poke %stead-observer-1 !>(raw)])
++  route
  |=  raw=@t
  ^-  path
  =/  command  (decode:stead-codec raw)
  =/  binding=@t  '019939ba-4000-7000-8000-000000000202'
  /v2/result/~bus/[binding]/[project.command]/[request.command]/[digest.command]
++  route-text
  |=  value=path
  (rap 3 (turn value |=(segment=@t (cat 3 '/' segment))))
++  hash
  |=  raw=@t
  (hex:stead-codec 64 (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)]))
++  noun-record
  |=  value=*
  ^-  @t
  =/  raw  (jam value)
  ~|  [%stead-scheduled-gall-noun-record-bytes (met 3 raw)]
  ?>  (lte (met 3 raw) 16.384)
  %-  canonical:stead-codec
  %-  object:stead-codec
  :~  ['jam_hex' (bytes-hex:stead-codec raw)]
      ['jam_sha256' (hash raw)]
      ['jam_bytes' (decimal:stead-codec (met 3 raw))]
      ['noun' (crip <value>)]
  ==
++  measured-jam
  |=  value=*
  ^-  @
  =/  raw  (jam value)
  ::  Native-only hash input, never exported or passed to the host noun decoder.
  ::  Gall05 measured 1,376,721 bytes for the actual old poke output list.
  ~|  [%stead-scheduled-gall-opaque-measurement-bytes (met 3 raw)]
  ?>  (lte (met 3 raw) 2.097.152)
  raw
++  poke-record
  |=  moves=(list motion)
  ^-  @t
  =/  emitted  (one-pass moves)
  ?>  ?=([* %pass * %g %deal * * %poke *] emitted)
  =/  [return=duct a=@ link=wire b=@ c=@ origin=[ship ship path] app=term d=@ payload=cage]  emitted
  =/  original-moves  (measured-jam moves)
  =/  original-poke  (measured-jam emitted)
  =/  original-type  (measured-jam p.q.payload)
  =/  type-sha  (hash original-type)
  =/  type-bytes  (met 3 original-type)
  ::  This deliberately invalid vase type is a report projection, never a task.
  ::  Preserve every other field, the exact body, output order and owner ACK.
  =/  projected=*
    [return a link b c origin app d p.payload [%stead-opaque-vase-type type-sha type-bytes] q.q.payload]
  =/  projected-moves
    (turn moves |=(message=motion ?:(=(message emitted) projected message)))
  %-  canonical:stead-codec
  %-  object:stead-codec
  :~  ['protocol' 'stead.gall-poke-projection/1']
      ['representation' 'poke-vase-type-omitted']
      ['measurement_scope' 'native hash-and-size only; omitted bytes not reconstructed']
      ['projected_moves' (noun-record projected-moves)]
      ['original_moves_jam_sha256' (hash original-moves)]
      ['original_moves_jam_bytes' (decimal:stead-codec (met 3 original-moves))]
      ['original_poke_jam_sha256' (hash original-poke)]
      ['original_poke_jam_bytes' (decimal:stead-codec (met 3 original-poke))]
      ['omitted_type_jam_sha256' type-sha]
      ['omitted_type_jam_bytes' (decimal:stead-codec type-bytes)]
  ==
++  assert-fresh
  |=  [observation=@t facts=@t kicks=@t ongoing=@t pokes=@t]
  ^-  ?
  ?&  =('' (field observation 'fault'))
      =('observed' (field observation 'status'))
      =(facts (field observation 'facts'))
      =(kicks (field observation 'kicks'))
      =('1' (field observation 'watch_acks'))
      =('0' (field observation 'watch_nacks'))
      =('0' (field observation 'poke_nacks'))
      =(ongoing (field observation 'ongoing_subscription'))
      =(pokes (field observation 'pokes_requested'))
      =(pokes (field observation 'poke_acks'))
  ==
++  assert-pending
  |=  [expected=@ud observation=@t]
  ^-  ?
  =/  actual  (field observation 'total')
  ~|  [%stead-scheduled-gall-pending-control expected actual]
  ?>  =((decimal:stead-codec expected) actual)
  &
++  one-fact
  |=  moves=(list motion)
  ^-  @t
  ?>  (lte (lent moves) 4)
  =/  facts  (skim moves |=(message=motion ?=([* %give %unto %fact *] message)))
  ?>  =(1 (lent facts))
  ?>  ?=(^ facts)
  ?>  ?=([* %give %unto %fact *] i.facts)
  =/  [return=duct a=@ b=@ c=@ result=cage]  i.facts
  ?>  =(%stead-result-2 p.result)
  !<(@t q.result)
++  run
  |=  expected-fresh-pending=@ud
  ^-  @t
  =/  home  (load-agent ~zod (make-gall ~zod) %stead-home home-agent)
  =/  bus  (load-agent ~bus (make-gall ~bus) %stead-observer observer-agent)
  =^  initialized  home
    (call home ~[/schedule/fixture] [%deal [~zod ~zod /] %stead-home %poke %stead-fixture-1 !>(fixture:inputs)])
  ?>  (just-ack initialized)
  =^  created  home
    (call home ~[/schedule/project] [%deal [~zod ~zod /] %stead-home %poke %stead-command-2 !>(project:inputs)])
  ?>  (just-ack created)
  =^  granted  home
    (call home ~[/schedule/grant] [%deal [~zod ~zod /] %stead-home %poke %stead-command-2 !>(grant:inputs)])
  ?>  (just-ack granted)
  =^  baseline  home  (query home ~zod %stead-home /v1/fixture-snapshot)
  ?>  &(=('1' (field baseline 'projects')) =('0' (field baseline 'work_items')) =('2' (field baseline 'journal_events')) =('2' (field baseline 'receipts')))
  =/  exact-path  (route work:inputs)
  =/  exact-text  (route-text exact-path)
  =/  old-id=@t  '019939ba-4000-7000-8000-000000009001'
  =/  new-id=@t  '019939ba-4000-7000-8000-000000009002'
  =/  live-id=@t  '019939ba-4000-7000-8000-000000009003'
  =^  old-watch-output  bus  (control bus 'watch' old-id exact-text '')
  =/  old-watch  (one-pass old-watch-output)
  ?>  ?=([* %pass * %g %deal * * %watch *] old-watch)
  =/  old-duct  (input-duct old-watch)
  =^  old-watch-gifts  home  (dispatch home old-watch)
  =.  bus  (deliver bus old-watch-gifts)
  =^  old-active  bus  (observe bus old-id)
  ?>  (assert-fresh old-active '0' '0' 'true' '0')
  =/  old-incoming  (incoming home)
  ?>  =(`[~bus exact-path] (~(get by old-incoming) old-duct))
  =^  old-pending  home  (query home ~zod %stead-home /v1/pending-snapshot)
  ?>  =('1' (field old-pending 'total'))
  ::  Capture the exact sender-Gall leave while the old home watch is active.
  =^  leave-output  bus  (control bus 'leave' old-id '' '')
  =/  held-leave  (one-pass leave-output)
  ?>  ?=([* %pass * %g %deal * * %leave ~] held-leave)
  ?>  =(old-duct (input-duct held-leave))
  =/  held-before  (noun-record held-leave)
  =^  old-poke-output  bus  (control bus 'poke' old-id '' work:inputs)
  =/  old-poke  (one-pass old-poke-output)
  =^  old-result-gifts  home  (dispatch home old-poke)
  =/  receipt  (one-fact old-result-gifts)
  ?>  =('accepted' (field receipt 'status'))
  =.  bus  (deliver bus old-result-gifts)
  =^  committed  home  (query home ~zod %stead-home /v1/fixture-snapshot)
  ?>  &(=('1' (field committed 'work_items')) =('3' (field committed 'journal_events')) =('3' (field committed 'receipts')))
  =^  retired-pending  home  (query home ~zod %stead-home /v1/pending-snapshot)
  ?>  =('0' (field retired-pending 'total'))
  =/  retired-incoming  (incoming home)
  ?>  !(~(has by retired-incoming) old-duct)
  =^  old-retired  bus  (observe bus old-id)
  ?>  (assert-fresh old-retired '0' '0' 'false' '1')
  ?>  =('true' (field old-retired 'leave_requested'))
  ::  New observer probe, identical path, distinct kernel-generated nonce/duct.
  =^  new-watch-output  bus  (control bus 'watch' new-id exact-text '')
  =/  new-watch  (one-pass new-watch-output)
  ?>  ?=([* %pass * %g %deal * * %watch *] new-watch)
  =/  new-duct  (input-duct new-watch)
  ?>  !=(old-duct new-duct)
  =/  old-sent=passage  old-watch
  =/  new-sent=passage  new-watch
  =/  old-nonce  (snag 6 link.old-sent)
  =/  new-nonce  (snag 6 link.new-sent)
  ?>  !=(old-nonce new-nonce)
  =^  new-watch-gifts  home  (dispatch home new-watch)
  =.  bus  (deliver bus new-watch-gifts)
  =^  pending-before  home  (query home ~zod %stead-home /v1/pending-snapshot)
  ?>  (assert-pending expected-fresh-pending pending-before)
  =/  incoming-before  (incoming home)
  ?>  =(1 (lent ~(tap by incoming-before)))
  ?>  =(`[~bus exact-path] (~(get by incoming-before) new-duct))
  ?>  !(~(has by incoming-before) old-duct)
  =^  observer-before  bus  (observe bus new-id)
  ?>  (assert-fresh observer-before '0' '0' 'true' '0')
  ::  Actual receiving Gall call, using unchanged retained task AND old duct.
  ?>  =(held-before (noun-record held-leave))
  =^  late-leave-output  home  (dispatch home held-leave)
  ?>  =(~ late-leave-output)
  =^  pending-after  home  (query home ~zod %stead-home /v1/pending-snapshot)
  =/  incoming-after  (incoming home)
  =^  observer-after  bus  (observe bus new-id)
  =^  old-after  bus  (observe bus old-id)
  =^  history-after  home  (query home ~zod %stead-home /v1/fixture-snapshot)
  ?>  =(pending-before pending-after)
  ?>  =(incoming-before incoming-after)
  ?>  =(observer-before observer-after)
  ?>  =(old-retired old-after)
  ?>  =(committed history-after)
  ::  The exact retry delivers one receipt and closes only the fresh watch.
  =^  new-poke-output  bus  (control bus 'poke' new-id '' work:inputs)
  =/  new-poke  (one-pass new-poke-output)
  =^  fresh-gifts  home  (dispatch home new-poke)
  ?>  =(receipt (one-fact fresh-gifts))
  =.  bus  (deliver bus fresh-gifts)
  =^  observer-completed  bus  (observe bus new-id)
  ?>  (assert-fresh observer-completed '1' '1' 'false' '1')
  ?>  =('true' (field observer-completed 'closed'))
  =^  old-completed  bus  (observe bus old-id)
  ?>  =(old-retired old-completed)
  =^  final-pending  home  (query home ~zod %stead-home /v1/pending-snapshot)
  ?>  =('0' (field final-pending 'total'))
  ?>  =(~ (incoming home))
  =^  history-completed  home  (query home ~zod %stead-home /v1/fixture-snapshot)
  ?>  =(committed history-completed)
  ::  A current live leave must really remove a new home reservation.
  =^  live-watch-output  bus  (control bus 'watch' live-id exact-text '')
  =/  live-watch  (one-pass live-watch-output)
  =^  live-watch-gifts  home  (dispatch home live-watch)
  =.  bus  (deliver bus live-watch-gifts)
  =^  live-before  home  (query home ~zod %stead-home /v1/pending-snapshot)
  ?>  =('1' (field live-before 'total'))
  =^  live-leave-output  bus  (control bus 'leave' live-id '' '')
  =/  live-leave  (one-pass live-leave-output)
  ?>  =((input-duct live-watch) (input-duct live-leave))
  =^  live-delivery-output  home  (dispatch home live-leave)
  ?>  =(~ live-delivery-output)
  =^  live-after  home  (query home ~zod %stead-home /v1/pending-snapshot)
  ?>  =('0' (field live-after 'total'))
  ?>  =(~ (incoming home))
  =^  live-observer  bus  (observe bus live-id)
  ?>  (assert-fresh live-observer '0' '0' 'false' '0')
  =^  final-history  home  (query home ~zod %stead-home /v1/fixture-snapshot)
  ?>  =(committed final-history)
  ::  Scalar diagnostics precede bounded serialization, including unprojected gifts.
  ~&  [%stead-scheduled-gall-jam-bytes
       [%old-poke (met 3 (jam old-poke-output))]
       [%fresh-poke (met 3 (jam new-poke-output))]
       [%old-result-gifts (met 3 (jam old-result-gifts))]
       [%fresh-result-gifts (met 3 (jam fresh-gifts))]]
  =/  result
    %-  canonical:stead-codec
    %-  object:stead-codec
    :~  ['protocol' 'stead.native-scheduled-gall/2']
        ['classification' 'native-scheduled-gall']
        ['status' 'passed']
        ['requirement' 'delivery-late-old-leave']
        ['clock' '2026-09-25T00:00:00Z; fixed test clock']
        ['transport' 'mock direct Gall dispatch; no Ames or UDP']
        ['late_old_leave' 'passed']
        ['current_live_leave_control' 'passed']
        ['expected_fresh_pending' (decimal:stead-codec expected-fresh-pending)]
        ['same_path' exact-text]
        ['old_nonce' old-nonce]  ['new_nonce' new-nonce]
        ['old_duct' (noun-record old-duct)]
        ['new_duct' (noun-record new-duct)]
        ['old_watch_moves' (noun-record old-watch-output)]
        ['old_watch_gifts' (noun-record old-watch-gifts)]
        ['captured_leave_moves' (noun-record leave-output)]
        ['captured_leave' held-before]
        ['delivered_leave' (noun-record held-leave)]
        ['delivered_leave_output' (noun-record late-leave-output)]
        ['old_poke_moves' (poke-record old-poke-output)]
        ['old_result_gifts' (noun-record old-result-gifts)]
        ['fresh_watch_moves' (noun-record new-watch-output)]
        ['fresh_watch_gifts' (noun-record new-watch-gifts)]
        ['fresh_poke_moves' (poke-record new-poke-output)]
        ['fresh_result_gifts' (noun-record fresh-gifts)]
        ['old_pending_active' old-pending]
        ['old_pending_retired' retired-pending]
        ['old_incoming_active' (noun-record old-incoming)]
        ['old_incoming_retired' (noun-record retired-incoming)]
        ['pending_before' pending-before]  ['pending_after' pending-after]
        ['incoming_before' (noun-record incoming-before)]
        ['incoming_after' (noun-record incoming-after)]
        ['observer_before' observer-before]  ['observer_after' observer-after]
        ['old_observer_retired' old-retired]  ['old_observer_after' old-after]
        ['observer_completed' observer-completed]
        ['old_observer_completed' old-completed]
        ['final_pending' final-pending]
        ['receipt' receipt]  ['receipt_sha256' (hash receipt)]
        ['business_committed' committed]
        ['business_after_leave' history-after]
        ['business_completed' history-completed]
        ['business_final' final-history]
        ['live_watch_moves' (noun-record live-watch-output)]
        ['live_leave_moves' (noun-record live-leave-output)]
        ['live_delivery_output' (noun-record live-delivery-output)]
        ['live_pending_before' live-before]  ['live_pending_after' live-after]
        ['live_observer' live-observer]
    ==
  ?>  (lte (met 3 result) 131.072)
  result
--
