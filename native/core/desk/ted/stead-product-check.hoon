::  Disposable product-profile Gall test carrier. No actor is supplied on wire.
::  Exact source/target identity is still derived by Gall; this does not bootstrap.
/-  spider
/+  strandio, stead-codec, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ target=@p app=@tas mode=@tas route=path raw=@t]  ;;([~ @p @tas @tas path @t] q.arg)
?>  (lte (met 3 raw) 65.536)
?>  =(%stead-home app)
=/  m  (strand ,vase)
=/  n  (strand ,~)
^-  form:m
=;  computation=form:m
  |=  tin=strand-input:strand
  =*  loop  $
  =/  out  (computation tin)
  ?:  ?=(%cont -.next.out)
    out(self.next ..loop(computation self.next.out))
  ?.  ?=(%fail -.next.out)  out
  =/  [kind=@tas detail=tang]  err.next.out
  ?>  (lte (met 3 (jam detail)) 16.384)
  =/  lines=wall  (zing (turn (flop detail) (cury wash [0 120])))
  =/  text=@t  (rap 3 (turn lines |=(line=tape (cat 3 (crip line) '\0a'))))
  ?>  (lte (met 3 text) 32.768)
  =/  bytes
    %-  canonical:stead-codec
    %-  object:stead-codec
    :~  ['protocol' 'stead.test-terminal/1']  ['status' 'failed']
        ['kind' kind]  ['trace' text]
        ['trace_jam_hex' (bytes-hex:stead-codec (jam detail))]
    ==
  out(next [%done !>([%stead-core-result (bytes-hex:stead-codec bytes)])])
%+  (set-timeout:strandio ,vase)  ~s55
=/  mark
  ?+  mode  !!
    %activate  %stead-product-activate-1
    %owner-command  %stead-owner-command-1
    %owner-receipt  %stead-owner-command-1
    %command  %stead-command-4
    %query  %stead-query-4
    %doc-command  %stead-doc-change-1
    %doc-query  %stead-doc-change-query-1
  ==
?:  ?|(=(%activate mode) =(%owner-command mode))
  ?>  ?=(~ route)
  ;<  ~  bind:m  (poke:strandio [target app] mark !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
=/  owner-receipt=?  =(%owner-receipt mode)
?>  ?:  owner-receipt
      &(!?=(~ route) =('' raw) ?=([%product-owner-receipt @ @ ~] route))
    ?=([%product %result @ @ @ @ @ ~] route)
;<  ~  bind:m  (watch:strandio /result [target app] route)
;<  ~  bind:m
  ?:  owner-receipt
    (pure:n ~)
  (send-raw-card:strandio [%pass /command %agent [target app] %poke mark !>(raw)])
=/  state=progress:stead-delivery  [owner-receipt | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  text  (need answer.state)
  =/  value  (need (parse-result:stead-codec text))
  ?>  ?=([%o *] value)
  `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
?+  in.tin  `[%skip ~]
  ~  `[%wait ~]
  [~ %agent * %poke-ack *]
    ?.  =(/command wire.u.in.tin)  `[%skip ~]
    ?^  p.sign.u.in.tin  `[%fail %poke-fail u.p.sign.u.in.tin]
    =/  next  (advance:stead-delivery state [%ack ~])
    ?~  next  `[%fail %stead-duplicate-ack ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %fact *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    ?.  =(%stead-result-3 p.cage.sign.u.in.tin)  `[%fail %stead-result-mark ~]
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
