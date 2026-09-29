:: Fixed qualification runner, separate from the public developer package.
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
=/  public=thread:spider  !<(thread:spider sample)
;<  command=dais:clay  bind:m  (build-mark:strandio snapshot %stead-command-3)
;<  query=dais:clay  bind:m  (build-mark:strandio snapshot %stead-query-3)
;<  result=dais:clay  bind:m  (build-mark:strandio snapshot %stead-result-3)
;<  updates=dais:clay  bind:m  (build-mark:strandio snapshot %stead-updates-3)
=/  response
  %-  canonical:stead-codec
  %-  object:stead-codec
  :~  ['protocol' 'stead.sdk-compile/1']
      ['status' 'compiled']
      ['consumer' (scot %p our)]
      ['desk' syd]
      ['clay_case' (scot %da p.case)]
      ['clay_case_atom' (scot %ux p.case)]
      ['marks' 'stead-command-3,stead-query-3,stead-result-3,stead-updates-3']
  ==
(pure:m !>([%stead-core-result (bytes-hex:stead-codec response)]))
