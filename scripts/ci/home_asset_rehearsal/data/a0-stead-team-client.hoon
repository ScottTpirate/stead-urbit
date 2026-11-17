::  Bounded disposable Khan adapter for the actual configured Gall interfaces.
/-  spider
/+  strandio, stead-codec, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ target=@p app=@tas mode=@tas route=path raw=@t]  ;;([~ @p @tas @tas path @t] q.arg)
?>  (lte (met 3 raw) 65.536)
?>  ?|(=(%stead-home app) =(%stead-identity app))
?>  ?:  =(%identity-config mode)  =(%stead-identity app)
    ?|(=(%bootstrap mode) =(%stead-home app))
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
    %configure  %stead-team-config-1
    %identity-config  %stead-identity-config-1
    %bootstrap  %stead-bootstrap-1
    %command  %stead-command-3
    %query  %stead-query-3
    %updates  %stead-updates-3
    %legacy-poke  %stead-command-2
    %legacy-watch  %stead-command-2
    %approve  %stead-auth-approval-1
  ==
?:  ?|(=(%configure mode) =(%identity-config mode) =(%approve mode) =(%legacy-poke mode))
  ;<  ~  bind:m  (poke:strandio [target app] mark !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
;<  ~  bind:m  (watch:strandio /result [target app] route)
?:  =(%legacy-watch mode)
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
;<  ~  bind:m  (send-raw-card:strandio [%pass /command %agent [target app] %poke mark !>(raw)])
=/  state=progress:stead-delivery  [| | ~]
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
