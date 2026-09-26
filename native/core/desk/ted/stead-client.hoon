::  Synthetic Khan client. Gall sends raw JSON; Khan returns a fixed hex wrapper.
/-  spider
/+  strandio, stead-codec, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ target=@p mode=@tas route=path raw=@t]  ;;([~ @p @tas path @t] q.arg)
=/  load-control=?
  ?.  =(%control mode)  |
  =/  val  ;;([@tas @p @t @t] (cue raw))
  ?|  =(%migrate-legacy -.val)  =(%load-bad-legacy -.val)
  ==
=/  m  (strand ,vase)
=/  n  (strand ,~)
^-  form:m
::  Full-state fixture validation can occupy one event; normal calls stay 55s.
%+  (set-timeout:strandio ,vase)  ?:(load-control ~s600 ~s55)
;<  =bowl:spider  bind:m  get-bowl:strandio
?:  =(%observe mode)
  ;<  ~  bind:m  (poke:strandio [our.bowl %stead-observer] %stead-observer-1 !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?:  =(%codec mode)
  =/  parsed  (mule |.((decode:stead-codec raw)))
  =/  result=@t
    ?-  -.parsed
      %|
        (canonical:stead-codec (object:stead-codec ~[['status' 'rejected'] ['error' 'invalid_command']]))
      %&
        (canonical:stead-codec (object:stead-codec ~[['status' 'accepted'] ['canonical' canonical-bytes.p.parsed] ['sha256' digest.p.parsed]]))
    ==
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec result)]))
?:  =(%poke mode)
  ;<  ~  bind:m  (poke:strandio [target %stead-home] %stead-command-2 !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?:  =(%fixture mode)
  ;<  ~  bind:m  (poke:strandio [target %stead-home] %stead-fixture-1 !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?:  =(%control mode)
  =/  val  ;;([@tas @p @t @t] (cue raw))
  ;<  ~  bind:m  (poke:strandio [target %stead-home] %stead-control-1 !>(val))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?>  ?|(=(mode %command) =(mode %read) =(mode %observer-read))
=/  cmd=(unit command:stead-codec)
  ?:  =(mode %command)  (some (decode:stead-codec raw))
  ~
;<  ~  bind:m
  ?:  =(mode %command)
    ::  Result registration has no early body; wait for its ACK before poking.
    ;<  ~  bind:n  (watch:strandio /result [target %stead-home] route)
    (send-raw-card:strandio [%pass /command %agent [target %stead-home] %poke %stead-command-2 !>(raw)])
  ::  Read watches can answer immediately: collect ACK and fact in either order.
  =/  peer=[@p @tas]
    ?:(=(mode %observer-read) [our.bowl %stead-observer] [target %stead-home])
  (send-raw-card:strandio [%pass /watch/result %agent peer %watch route])
=/  state=progress:stead-delivery  [| | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  text  (need answer.state)
  =/  value  (need (parse-result:stead-codec text))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?:  =(mode %observer-read)
    ?>  ?|(=('stead.observer/1' (field:stead-codec obj 'protocol')) =('stead.observer-summary/1' (field:stead-codec obj 'protocol')))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?^  cmd
    =/  status  (field:stead-codec obj 'status')
    ?>  ?|(=('accepted' status) =('rejected' status))
    ?:  =('accepted' status)
      ?>  ?&  (receipt-fields:stead-codec obj)
              =(request.u.cmd (field:stead-codec obj 'request_id'))
              =(project.u.cmd (field:stead-codec obj 'project_id'))
              =(resource.u.cmd (field:stead-codec obj 'resource_id'))
              =(digest.u.cmd (field:stead-codec obj 'canonical_sha256'))
              =((receipt-kind:stead-codec operation.u.cmd) (field:stead-codec obj 'resource_kind'))
              =(?:(=('document.save' operation.u.cmd) (field:stead-codec payload.u.cmd 'container_id') '') (field:stead-codec obj 'container_id'))
          ==
      `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
    ?>  =('stead.result/2' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?:  ?|(=(route /v1/fixture-snapshot) =(route /v1/predecessor-snapshot))
    ?>  =('stead.fixture-snapshot/1' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?:  =(route /v1/pending-snapshot)
    ?>  =('stead.fixture-pending/1' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?:  ?|(=(route /v1/predecessor-response) =(route /v1/batch-response))
    ?>  =('stead.fixture-predecessor/1' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  =/  status  (field:stead-codec obj 'status')
  ?:  =('rejected' status)
    ?>  =('stead.result/2' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?:  =('accepted' status)
    ?>  ?=([%v2 %receipt @ @ @ @ @ ~] route)
    ?>  ?&  (receipt-fields:stead-codec obj)
            =(i.t.t.route (field:stead-codec obj 'project_id'))
            =(i.t.t.t.t.route (field:stead-codec obj 'resource_id'))
            =(i.t.t.t.t.t.t.route (field:stead-codec obj 'request_id'))
            =((receipt-kind:stead-codec i.t.t.t.t.t.route) (field:stead-codec obj 'resource_kind'))
            =(?:(=('document.save' i.t.t.t.t.t.route) i.t.t.t.route '') (field:stead-codec obj 'container_id'))
        ==
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?>  &(=('read' status) =('stead.result/2' (field:stead-codec obj 'protocol')))
  ?>  ?=([%v2 @ @ *] route)
  ?>  =(i.t.t.route (field:stead-codec obj 'project_id'))
  =/  resource
    ?:  =(i.t.route %project)  i.t.t.route
    ?>  ?=([%v2 @ @ @ *] route)
    ?:  =(i.t.route %document)
      ?>  ?=([%v2 %document @ @ @ ~] route)
      =/  payload  (~(got by obj) 'payload')
      ?>  ?=([%o *] payload)
      ?>  =(i.t.t.t.route (field:stead-codec p.payload 'container_id'))
      i.t.t.t.t.route
    i.t.t.t.route
  ?>  =(resource (field:stead-codec obj 'resource_id'))
  `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
?+  in.tin  `[%skip ~]
  ~  `[%wait ~]
  [~ %agent * %poke-ack *]
    ?.  &(=(mode %command) =(/command wire.u.in.tin))  `[%skip ~]
    ?^  p.sign.u.in.tin  `[%fail %poke-fail u.p.sign.u.in.tin]
    =/  next  (advance:stead-delivery state [%ack ~])
    ?~  next  `[%fail %stead-duplicate-ack ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %watch-ack *]
    ?.  &(?|(=(mode %read) =(mode %observer-read)) =(/watch/result wire.u.in.tin))  `[%skip ~]
    ?^  p.sign.u.in.tin  `[%fail %watch-fail u.p.sign.u.in.tin]
    =/  next  (advance:stead-delivery state [%ack ~])
    ?~  next  `[%fail %stead-duplicate-ack ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %fact *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    ?.  =(%stead-result-2 p.cage.sign.u.in.tin)  `[%fail %stead-result-mark ~]
    =/  text  !<(@t q.cage.sign.u.in.tin)
    ?.  (lte (met 3 text) 262.144)  `[%fail %stead-result-limit ~]
    =/  next  (advance:stead-delivery state [%fact text])
    ?~  next  `[%fail %stead-duplicate-fact ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %kick *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    =/  next  (advance:stead-delivery state [%kick ~])
    ?~  next  `[%fail %stead-duplicate-kick ~]
    `[%cont ..loop(state u.next)]
==
