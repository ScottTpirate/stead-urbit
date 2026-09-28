:: Public protocol/3 sample. No authority configuration or private state imports.
/-  spider
/+  strandio, stead-codec, stead-delivery
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  m  (strand ,vase)
=/  protect
  |=  computation=(trap form:m)
  ^-  form:m
  |=  tin=strand-input:strand
  =*  loop  $
  =/  attempted  (mule |.(($:computation tin)))
  ?:  ?=(%| -.attempted)
    `[%done !>([%stead-sdk-result '{"protocol":"stead.sdk-error/1","status":"failed","error":"request_unconfirmed"}'])]
  =/  out  p.attempted
  ?:  ?=(%cont -.next.out)
    out(self.next ..loop(computation |.(self.next.out)))
  ?.  ?=(%fail -.next.out)  out
  out(next [%done !>([%stead-sdk-result '{"protocol":"stead.sdk-error/1","status":"failed","error":"request_unconfirmed"}'])])
^-  form:m
:: Inner normalization lets set-timeout cancel its timer on early failure.
:: Outer normalization handles timeout itself, after its wake was delivered.
%-  protect
|.
%+  (set-timeout:strandio ,vase)  ~s55
%-  protect
|.
=/  [~ home=@p binding=@t revision=@ud mode=@tas raw=@t]
  ;;([~ @p @t @ud @tas @t] q.arg)
?>  &((uuid:stead-codec binding) (gth revision 0) (lte revision 18.446.744.073.709.551.615))
?>  (lte (met 3 raw) 65.536)
=/  domain=@t
  ?+  mode  !!
    %command  'stead.command/3'
    %query  'stead.query/3'
    %updates  'stead.updates/3'
  ==
=/  mark=@tas
  ?+  mode  !!
    %command  %stead-command-3
    %query  %stead-query-3
    %updates  %stead-updates-3
  ==
=/  value  (need (parse:stead-codec raw))
?>  ?=([%o *] value)
=/  request  (field:stead-codec p.value 'request_id')
?>  (uuid:stead-codec request)
=/  digest  (hash:stead-codec domain (canonical:stead-codec value))
;<  our=@p  bind:m  get-our:strandio
=/  route=path  [%v3 %result (scot %p our) binding (decimal:stead-codec revision) request digest ~]
;<  ~  bind:m  (watch:strandio /result [home %stead-home] route)
;<  ~  bind:m  (send-raw-card:strandio [%pass /command %agent [home %stead-home] %poke mark !>(raw)])
=/  state=progress:stead-delivery  [| | ~]
|=  tin=strand-input:strand
=*  loop  $
?:  (complete:stead-delivery state)
  =/  text  (need answer.state)
  =/  value  (need (parse-result:stead-codec text))
  ?>  ?=([%o *] value)
  `[%done !>([%stead-sdk-result text])]
?+  in.tin  `[%skip ~]
  ~  `[%wait ~]
  [~ %agent * %poke-ack *]
    ?.  =(/command wire.u.in.tin)  `[%skip ~]
    ?^  p.sign.u.in.tin  `[%fail %request-unconfirmed ~]
    =/  next  (advance:stead-delivery state [%ack ~])
    ?~  next  `[%fail %duplicate-ack ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %fact *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    ?.  =(%stead-result-3 p.cage.sign.u.in.tin)  `[%fail %result-mark ~]
    =/  text  !<(@t q.cage.sign.u.in.tin)
    ?.  (lte (met 3 text) 262.144)  `[%fail %result-limit ~]
    =/  next  (advance:stead-delivery state [%fact text])
    ?~  next  `[%fail %duplicate-fact ~]
    `[%cont ..loop(state u.next)]
  [~ %agent * %kick *]
    ?.  =(/watch/result wire.u.in.tin)  `[%skip ~]
    =/  next  (advance:stead-delivery state [%kick ~])
    ?~  next  `[%fail %duplicate-kick ~]
    `[%cont ..loop(state u.next)]
==
