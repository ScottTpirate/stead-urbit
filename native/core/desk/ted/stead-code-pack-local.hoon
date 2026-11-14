::  Private Khan exchange available on a disposable fake Home desk.
/-  spider
/+  strandio, stead-codec, stead-code-pack-owner, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ expected=@p cmd=command:stead-code-pack-owner]
  ;;([~ @p command:stead-code-pack-owner] q.arg)
=/  m  (strand ,vase)
^-  form:m
%+  (set-timeout:strandio ,vase)  ~s45
;<  =bowl:spider  bind:m  get-bowl:strandio
?>  =(expected our.bowl)
?>  .^(? %j /(scot %p our.bowl)/fake/(scot %da now.bowl))
=/  target  [our.bowl %stead-home]
=/  route=path  [%pack-local nonce.cmd ~]
;<  ~  bind:m  (watch:strandio /result target route)
;<  ~  bind:m
  (send-raw-card:strandio [%pass /command %agent target %poke %noun !>([~ %stead-pack-local cmd])])
=/  state=progress:stead-delivery  [| | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  raw  (need answer.state)
  `[%done !>([%stead-core-result (bytes-hex:stead-codec raw)])]
=/  event=(unit event:stead-delivery)
  ?+  in.tin  ~
    [~ %agent * %poke-ack *]
      ?.  =(/command wire.u.in.tin)  ~
      ?^  p.sign.u.in.tin  [~ %nack ~]
      [~ %ack ~]
    [~ %agent * %fact *]
      ?.  =(/watch/result wire.u.in.tin)  ~
      ?.  =(%stead-result-3 p.cage.sign.u.in.tin)  `[%nack ~]
      =/  raw  !<(@t q.cage.sign.u.in.tin)
      ?.  (lte (met 3 raw) 65.536)  `[%nack ~]
      `[%fact raw]
    [~ %agent * %kick *]
      ?.  =(/watch/result wire.u.in.tin)  ~
      `[%kick ~]
  ==
?~  event  ?~(in.tin `[%wait ~] `[%skip ~])
=/  next  (advance:stead-delivery state u.event)
?~  next  `[%fail %stead-pack-local-exchange ~]
`[%cont ..loop(state u.next)]
