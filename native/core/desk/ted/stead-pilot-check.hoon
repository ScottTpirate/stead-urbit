::  Disposable Khan adapter for pilot status and Home handoff controls.
/-  spider
/+  strandio, stead-codec, stead-delivery, stead-home-handoff
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  [~ target=@p app=@tas mode=@tas route=path raw=@t]  ;;([~ @p @tas @tas path @t] q.arg)
?>  =(app %stead-home)
?>  (lte (met 3 raw) 512)
=/  m  (strand ,vase)
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
?:  =(%handoff mode)
  ?>  ?=(~ route)
  =/  input  (decode:stead-home-handoff raw)
  ;<  ~  bind:m  (poke:strandio [target app] %stead-home-handoff-1 !>(input))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?:  =(%project-retire mode)
  ?>  ?=(~ route)
  ;<  ~  bind:m  (poke:strandio [target app] %stead-project-retirement-1 !>(raw))
  (pure:m !>([%stead-core-result (bytes-hex:stead-codec '{}')]))
?>  =('' raw)
?>  ?:  =(%operator-status mode)  ?=([%operator @ ~] route)
    ?:  =(%project-retirement-status mode)  ?=([%project-retirement @ ~] route)
    &(=(%handoff-status mode) =(route /home-handoff/status))
;<  ~  bind:m  (watch:strandio /result [target app] route)
=/  state=progress:stead-delivery  [& | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  text  (need answer.state)
  =/  value  (need (parse-result:stead-codec text))
  ?>  ?=([%o *] value)
  `[%done !>([%stead-core-result (bytes-hex:stead-codec text)])]
?+  in.tin  `[%skip ~]
  ~  `[%wait ~]
  [~ %agent * %fact *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    ?.  =(%stead-result-3 p.cage.sign.u.in.tin)  `[%fail %stead-result-mark ~]
    =/  text  !<(@t q.cage.sign.u.in.tin)
    ?.  (lte (met 3 text) 2.048)  `[%fail %stead-result-limit ~]
    =/  next  (advance:stead-delivery state [%fact text])
    ?~  next  `[%fail %stead-duplicate-fact ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %kick *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    =/  next  (advance:stead-delivery state [%kick ~])
    ?~  next  `[%fail %stead-duplicate-kick ~]
    `[%cont ..loop(state u.next)]
==
