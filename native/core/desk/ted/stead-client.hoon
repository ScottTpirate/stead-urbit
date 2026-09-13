::  Synthetic Khan client. Gall sends raw JSON; Khan returns a fixed hex wrapper.
/-  spider
/+  strandio, stead-codec, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ target=@p mode=@tas route=path raw=@t]  ;;([~ @p @tas path @t] q.arg)
=/  m  (strand ,vase)
=/  n  (strand ,~)
^-  form:m
%+  (set-timeout:strandio ,vase)  ~s55
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
  ;<  ~  bind:m  (poke:strandio [target %stead-home] %stead-command-1 !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?:  =(%fixture mode)
  ;<  ~  bind:m  (poke:strandio [target %stead-home] %stead-fixture-1 !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?:  =(%control mode)
  =/  val  ;;([@tas @p @t @t] (cue raw))
  ;<  ~  bind:m  (poke:strandio [target %stead-home] %stead-control-1 !>(val))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?>  ?|(=(mode %command) =(mode %read))
=/  cmd=(unit command:stead-codec)
  ?:  =(mode %command)  (some (decode:stead-codec raw))
  ~
;<  ~  bind:m
  ?:  =(mode %command)
    ::  Result registration has no early body; wait for its ACK before poking.
    ;<  ~  bind:n  (watch:strandio /result [target %stead-home] route)
    (send-raw-card:strandio [%pass /command %agent [target %stead-home] %poke %stead-command-1 !>(raw)])
  ::  Read watches can answer immediately: collect ACK and fact in either order.
  (send-raw-card:strandio [%pass /watch/result %agent [target %stead-home] %watch route])
=/  state=progress:stead-delivery  [| | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  text  (need answer.state)
  =/  value  (need (parse-result:stead-codec text))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?^  cmd
    =/  status  (field:stead-codec obj 'status')
    ?>  ?|(=('accepted' status) =('rejected' status))
    ?:  =('accepted' status)
      ?>  ?&  =('stead.receipt/1' (field:stead-codec obj 'protocol'))
              =(request.u.cmd (field:stead-codec obj 'request_id'))
              =(project.u.cmd (field:stead-codec obj 'project_id'))
              =(resource.u.cmd (field:stead-codec obj 'resource_id'))
              =(digest.u.cmd (field:stead-codec obj 'canonical_sha256'))
          ==
      `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
    ?>  =('stead.result/1' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?:  =(route /v1/fixture-snapshot)
    ?>  =('stead.fixture-snapshot/1' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  =/  status  (field:stead-codec obj 'status')
  ?:  =('rejected' status)
    ?>  =('stead.result/1' (field:stead-codec obj 'protocol'))
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?:  =('accepted' status)
    ?>  ?=([%v1 %receipt @ @ @ @ ~] route)
    ?>  ?&  =('stead.receipt/1' (field:stead-codec obj 'protocol'))
            =(i.t.t.route (field:stead-codec obj 'project_id'))
            =(i.t.t.t.route (field:stead-codec obj 'resource_id'))
            =(i.t.t.t.t.t.route (field:stead-codec obj 'request_id'))
        ==
    `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
  ?>  &(=('read' status) =('stead.result/1' (field:stead-codec obj 'protocol')))
  ?>  ?=([%v1 @ @ *] route)
  ?>  =(i.t.t.route (field:stead-codec obj 'project_id'))
  =/  resource
    ?:  =(i.t.route %project)  i.t.t.route
    ?>  ?=([%v1 @ @ @ *] route)
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
    ?.  &(=(mode %read) =(/watch/result wire.u.in.tin))  `[%skip ~]
    ?^  p.sign.u.in.tin  `[%fail %watch-fail u.p.sign.u.in.tin]
    =/  next  (advance:stead-delivery state [%ack ~])
    ?~  next  `[%fail %stead-duplicate-ack ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %fact *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    ?.  =(%stead-result-1 p.cage.sign.u.in.tin)  `[%fail %stead-result-mark ~]
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
