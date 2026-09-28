:: Prepared controller source; not yet compiled or executed.
:: Install only in the separate public-SDK builder, never on the Home.
/-  spider
/+  strandio, stead-codec
=,  strand=strand:spider
^-  thread:spider
|=  arg=vase
=/  m  (strand ,vase)
^-  form:m
;<  [our=ship syd=desk =case]  bind:m  get-beak:strandio
?>  ?=(%da -.case)
=/  snapshot=beak  [our syd case]
;<  sample=vase  bind:m
  (build-file-hard:strandio snapshot /ted/stead-sdk-call/hoon)
;<  command=dais:clay  bind:m
  (build-mark:strandio snapshot %stead-command-3)
;<  query=dais:clay  bind:m
  (build-mark:strandio snapshot %stead-query-3)
;<  result=dais:clay  bind:m
  (build-mark:strandio snapshot %stead-result-3)
;<  updates=dais:clay  bind:m
  (build-mark:strandio snapshot %stead-updates-3)
:: Retain the complete sample vase, including its captured subject. Each mark
:: is a separately named typed dais vase, even when mark source bytes match.
=/  artifacts=(list [name=@tas bytes=@])
  :~  [%sample (jam sample)]
      [%stead-command-3 (jam !>(command))]
      [%stead-query-3 (jam !>(query))]
      [%stead-result-3 (jam !>(result))]
      [%stead-updates-3 (jam !>(updates))]
  ==
?>  (levy artifacts |=([name=@tas bytes=@] &((gth (met 3 bytes) 0) (lte (met 3 bytes) 16.777.216))))
=/  total=@ud
  (roll artifacts |=([item=[name=@tas bytes=@] sum=@ud] (add sum (met 3 bytes.item))))
?>  (lte total 67.108.864)
=/  manifest=json
  :-  %o
  %-  malt
  %+  turn  artifacts
  |=  [name=@tas bytes=@]
  =/  size  (met 3 bytes)
  :-  (cat 3 name '.jam')
  %-  object:stead-codec
  :~  ['bytes' (decimal:stead-codec size)]
      ['sha256' (hex:stead-codec 64 (sha-256l:sha [size (rev 3 size bytes)]))]
  ==
;<  ~  bind:m
  %-  send-raw-card:strandio
  =-  [%pass /stead-sdk-export %arvo %c %info syd %& -]
  ^-  soba:clay
  %+  turn  artifacts
  |=  [name=@tas bytes=@]
  [[%tmp %stead-sdk name %jam ~] %ins %jam %noun bytes]
:: %info edits the current Clay desk. A verified mount/export mapping is also
:: required; these are Clay paths, not files below the host /tmp directory.
:: This queues the export; it does not acknowledge that files materialized.
:: The controller must wait/read back, stop/reap, and verify custody separately.
=/  fields
  %-  malt
  :~  ['protocol' [%s 'stead.sdk-build-staged/1']]
      ['status' [%s 'export_queued']]
      ['builder' [%s (scot %p our)]]
      ['desk' [%s syd]]
      ['clay_case' [%s (scot %da p.case)]]
      ['artifacts' manifest]
  ==
=/  response  (canonical:stead-codec [%o fields])
(pure:m !>([%stead-core-result (bytes-hex:stead-codec response)]))
