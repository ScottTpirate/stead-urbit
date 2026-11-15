::  Reserved exact Doc Change commands. No Home mark or route is active.
::  Parsing admits intent, never a producer identity, approval or worker lease.
/+  stead-codec, stead-team-codec, stead-product-codec
=,  stead-codec
|%
+$  command
  $:  request=@t  project=@t  work=@t  change=@t  epoch=@ud
      expected=@ud  operation=@t  payload=object-map
      canonical-bytes=@t  digest=@t
  ==
++  result-pin
  |=  payload=object-map
  ^-  ?
  ?&  (gth (uint (field payload 'result_revision')) 0)
      (opaque:stead-team-codec (field payload 'result_digest'))
  ==
++  submission
  |=  [project=@t work=@t payload=object-map]
  ^-  ?
  ?&  (keys payload ~['outcome_id' 'target' 'markdown' 'summary' 'execution_contract_revision' 'execution_contract_digest' 'run_id' 'attempt'])
      (uuid (field payload 'outcome_id'))
      =/  target  (~(got by payload) 'target')
      ?&  (outcome:stead-product-codec project work target)
          ?>  ?=([%o *] target)
          =('document' (field p.target 'kind'))
      ==
      (prose (field payload 'markdown') 32.768)
      (comment-body:stead-team-codec (field payload 'summary'))
      (gth (uint (field payload 'execution_contract_revision')) 0)
      (opaque:stead-team-codec (field payload 'execution_contract_digest'))
      =/  run  (field payload 'run_id')
      =/  attempt  (uint (field payload 'attempt'))
      ?:(=('' run) =(attempt 0) &((uuid run) (gth attempt 0)))
  ==
++  action
  |=  [operation=@t expected=@ud project=@t work=@t payload=object-map]
  ^-  ?
  ?:  =('change.submit' operation)
    (submission project work payload)
  ?.  (gth expected 0)  |
  ?.  (~(has in (silt ~['change.request-changes' 'change.approve' 'change.adopt' 'change.accept' 'change.reject' 'change.quarantine'])) operation)  |
  ?&  (keys payload ~['result_revision' 'result_digest' 'note'])
      (result-pin payload)
      =/  note  (field payload 'note')
      ?:  ?|(=('change.approve' operation) =('change.accept' operation))
        ?|(=('' note) (comment-body:stead-team-codec note))
      (comment-body:stead-team-codec note)
  ==
++  decode
  |=  raw=@t
  ^-  command
  ::  The shared bounded parser rejects duplicate keys, numbers, arrays and
  ::  extra nesting. This envelope and its payload are closed independently.
  =/  value  (need (parse-product:stead-product-codec raw))
  ?>  ?=([%o *] value)
  =/  data  p.value
  ?>  (keys data ~['protocol' 'request_id' 'project_id' 'work_id' 'change_id' 'authority_epoch' 'expected_revision' 'operation' 'payload'])
  ?>  =('stead.doc-change/1' (field data 'protocol'))
  =/  request  (field data 'request_id')
  =/  project  (field data 'project_id')
  =/  work  (field data 'work_id')
  =/  change  (field data 'change_id')
  ?>  &((uuid request) (uuid project) (uuid work) (uuid change))
  =/  epoch  (uint (field data 'authority_epoch'))
  ?>  (gth epoch 0)
  =/  expected  (uint (field data 'expected_revision'))
  =/  operation  (field data 'operation')
  =/  payload  (object-field:stead-product-codec data 'payload')
  ?>  (action operation expected project work payload)
  =/  bytes  (canonical value)
  [request project work change epoch expected operation payload bytes (hash 'stead.doc-change/1' bytes)]
--
