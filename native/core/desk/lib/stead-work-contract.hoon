::  Read-only execution pins derived from accepted command/3 history.
::  This preserves saved state, journal bytes, receipts and aggregate revision.
::  Only exact title/description changes advance this v1 contract; native Code
::  submission does not yet accept this pin and is not atomically fenced by it.
/+  stead-codec, stead-team-codec
=,  stead-codec
|%
+$  event  [project=@t bytes=@t digest=@t]
+$  goal  [revision=@ud title=@t description=@t]
++  replay
  |=  [journal=(list event) project=@t work=@t]
  ^-  (unit goal)
  ::  The authoritative restore/admission bounds include security reserves.
  ?>  (lte (lent journal) 6.144)
  =/  remaining  (flop journal)
  =/  current=(unit goal)  ~
  |-
  ?~  remaining  current
  ?.  =(project project.i.remaining)  $(remaining t.remaining)
  =/  record  (need (parse-result bytes.i.remaining))
  ?>  ?=([%o *] record)
  =/  cmd  (decode:stead-team-codec (field p.record 'canonical_command'))
  ?>  =(project project.cmd)
  ?.  =(work resource.cmd)  $(remaining t.remaining)
  ?:  =('work.delete' operation.cmd)  $(remaining t.remaining, current ~)
  ?.  ?|(=('work.create' operation.cmd) =('work.update' operation.cmd))
    $(remaining t.remaining)
  =/  title  (field payload.cmd 'title')
  =/  description  (field payload.cmd 'description')
  ?:  =('work.create' operation.cmd)
    ?>  ?=(~ current)
    $(remaining t.remaining, current (some [1 title description]))
  =/  prior  (need current)
  =/  changed  ?|(!=(title title.prior) !=(description description.prior))
  $(remaining t.remaining, current (some [?:(changed +(revision.prior) revision.prior) title description]))
++  fingerprint
  |=  [project=@t work=@t contract=goal]
  ^-  @t
  %-  hash
  :-  'stead.work-contract/1'
  %-  canonical
  %-  object
  :~  ['project_id' project]  ['work_id' work]
      ['execution_contract_revision' (decimal revision.contract)]
      ['title' title.contract]  ['description' description.contract]
  ==
++  fields
  |=  [journal=(list event) project=@t work=@t data=object-map]
  ^-  object-map
  =/  contract  (need (replay journal project work))
  ::  A pin is never returned for an inconsistent current resource projection.
  ?>  &(=(title.contract (field data 'title')) =(description.contract (field data 'description')))
  =/  value
    %-  object
    :~  ['execution_contract_protocol' 'stead.work-contract/1']
        ['execution_contract_revision' (decimal revision.contract)]
        ['execution_contract_digest' (fingerprint project work contract)]
    ==
  ?>  ?=([%o *] value)
  p.value
--
