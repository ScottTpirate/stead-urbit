::  Reserved command/4 Work decoder. No Home route or saved-state activation.
::  This admits syntax and closed shapes only. Current authorization, CAS,
::  outcomes/checks and completion authority belong in the final reducer.
/+  stead-codec, stead-team-codec, stead-code-git-objects
=,  stead-codec
|%
+$  command
  $:  request=@t  project=@t  resource=@t  epoch=@ud  operation=@t
      expected=object-map  payload=object-map  canonical-bytes=@t  digest=@t
  ==
++  parse-product
  |=  raw=@t
  ^-  (unit json)
  ?:  (gth (met 3 raw) 65.536)  ~
  ::  Exactly four object levels: envelope, payload, outcomes, typed target.
  ::  Existing dict-rule rejects duplicate keys and caps each object at16.
  %+  rush  raw
  %+  ifix  [spac:de:json:html spac:de:json:html]
  %+  stag  %o
  %-  dict-rule
  ;~  pose
    (stag %s string-rule)
    %+  stag  %o
    %-  dict-rule
    ;~  pose
      (stag %s string-rule)
      %+  stag  %o
      %-  dict-rule
      ;~  pose
        (stag %s string-rule)
        (stag %o (dict-rule (stag %s string-rule)))
      ==
    ==
  ==
++  object-field
  |=  [data=object-map name=@t]
  ^-  object-map
  =/  value  (~(got by data) name)
  ?>  ?=([%o *] value)
  p.value
++  principal
  |=  value=@t
  ^-  ?
  ?|(=('' value) (uuid value))
++  branch
  |=  value=@t
  ^-  ?
  ?&  (lte (met 3 value) 128)
      =('refs/heads/' (cut 3 [0 11] value))
      (valid-ref:stead-code-git-objects [(met 3 value) value])
  ==
++  outcome
  |=  [project=@t work=@t value=json]
  ^-  ?
  ?.  ?=([%o *] value)  |
  =/  data  p.value
  =/  kind  (field data 'kind')
  ?.  =(project (field data 'project_id'))  |
  ?:  =('document' kind)
    ?&  (keys data ~['kind' 'project_id' 'collection_id' 'document_id' 'expected_revision' 'base_markdown_sha256'])
        (uuid (field data 'collection_id'))  (uuid (field data 'document_id'))
        =/  revision  (uint (field data 'expected_revision'))
        =/  digest  (field data 'base_markdown_sha256')
        ?:(=(revision 0) =('' digest) (opaque:stead-team-codec digest))
    ==
  ?:  =('code' kind)
    ?&  (keys data ~['kind' 'project_id' 'repository_id' 'target_ref' 'base_oid'])
        (uuid (field data 'repository_id'))  (branch (field data 'target_ref'))
        (oid:stead-team-codec (field data 'base_oid'))
    ==
  ?:  =('completion-note' kind)
    ?&  (keys data ~['kind' 'project_id' 'work_id' 'expected_revision'])
        =(work (field data 'work_id'))
        =/  revision  (uint (field data 'expected_revision'))
        (lte revision 18.446.744.073.709.551.615)
    ==
  |
++  outcome-identity
  ::  Two outcomes cannot require independent acceptance of the same target
  ::  base: accepting one would make the other's base permanently stale.
  |=  value=json
  ^-  @t
  ?>  ?=([%o *] value)
  =/  kind  (field p.value 'kind')
  =/  names
    ?:  =('document' kind)  ~['kind' 'project_id' 'collection_id' 'document_id']
    ?:  =('code' kind)  ~['kind' 'project_id' 'repository_id' 'target_ref']
    ~['kind' 'project_id' 'work_id']
  (canonical (object (turn names |=(name=@t [name (field p.value name)]))))
++  outcomes
  |=  [project=@t work=@t data=object-map]
  ^-  ?
  ?&  (lte (lent ~(tap by data)) 16)
      %+  levy  ~(tap by data)
      |=  [id=@t value=json]
      &((uuid id) (outcome project work value))
      =/  targets  (turn ~(tap by data) |=([id=@t value=json] (outcome-identity value)))
      =((lent targets) (lent ~(tap in (silt targets))))
  ==
++  properties
  |=  [data=object-map allow-done=?]
  ^-  ?
  =/  status  (field data 'status')
  =/  blocked  (field data 'blocked_reason')
  ?&  (~(has in (silt ~['deliverable' 'task' 'problem'])) (field data 'type'))
      ?|  (~(has in (silt ~['backlog' 'todo' 'in_progress' 'in_review' 'canceled'])) status)
          &(allow-done =('done' status))
      ==
      (~(has in (silt ~['none' 'low' 'medium' 'high' 'urgent'])) (field data 'priority'))
      (principal (field data 'owner_principal_id'))
      (principal (field data 'worker_principal_id'))
      ?|  =('' blocked)
          &(!=('canceled' status) !=('done' status) (comment-body:stead-team-codec blocked))
      ==
  ==
++  contract
  |=  [project=@t work=@t data=object-map]
  ^-  ?
  ?&  (title (field data 'title'))
      (prose (field data 'description') 8.192)
      (prose (field data 'acceptance_criteria') 8.192)
      (outcomes project work (object-field data 'required_outcomes'))
  ==
++  expected-shape
  |=  [operation=@t data=object-map]
  ^-  ?
  ?:  =('work.create' operation)
    ?&  (keys data ~['work_revision' 'execution_contract_revision'])
        =(0 (uint (field data 'work_revision')))
        =(0 (uint (field data 'execution_contract_revision')))
    ==
  ?:  ?|(=('work.update-properties' operation) =('work.resolve-legacy-blocked' operation) =('work.resolve-legacy-assignee' operation))
    &((keys data ~['work_revision']) (gth (uint (field data 'work_revision')) 0))
  ?:  =('work.update-contract' operation)
    &((keys data ~['execution_contract_revision']) (gth (uint (field data 'execution_contract_revision')) 0))
  ?:  =('work.comment' operation)
    ?&  (keys data ~['discussion_sequence'])
        =/  sequence  (uint (field data 'discussion_sequence'))
        (lte sequence 18.446.744.073.709.551.615)
    ==
  ?.  ?|(=('work.complete' operation) =('work.delete' operation))  |
  ?&  (keys data ?:(=('work.complete' operation) ~['work_revision' 'execution_contract_revision'] ~['work_revision' 'execution_contract_revision' 'discussion_sequence']))
      (gth (uint (field data 'work_revision')) 0)
      (gth (uint (field data 'execution_contract_revision')) 0)
      ?:  =('work.complete' operation)  &
      =/  sequence  (uint (field data 'discussion_sequence'))
      (lte sequence 18.446.744.073.709.551.615)
  ==
++  payload-shape
  |=  [operation=@t project=@t work=@t data=object-map]
  ^-  ?
  ?:  =('work.create' operation)
    ?&  (keys data ~['type' 'status' 'priority' 'owner_principal_id' 'worker_principal_id' 'blocked_reason' 'title' 'description' 'acceptance_criteria' 'required_outcomes'])
        (properties data |)  (contract project work data)
    ==
  ?:  =('work.update-properties' operation)
    ::  Done may be retained while editing other properties. The reducer must
    ::  reject a transition into Done here and preserve its completion basis.
    ?&  (keys data ~['type' 'status' 'priority' 'owner_principal_id' 'worker_principal_id' 'blocked_reason'])
        (properties data &)
    ==
  ?:  =('work.update-contract' operation)
    ?&  (keys data ~['title' 'description' 'acceptance_criteria' 'required_outcomes'])
        (contract project work data)
    ==
  ?:  =('work.resolve-legacy-blocked' operation)
    ?&  (keys data ~['status' 'blocked_reason'])
        (~(has in (silt ~['backlog' 'todo' 'in_progress' 'in_review'])) (field data 'status'))
        =/  reason  (field data 'blocked_reason')
        ?|(=('' reason) (comment-body:stead-team-codec reason))
    ==
  ?:  =('work.resolve-legacy-assignee' operation)
    ?&  (keys data ~['owner_principal_id' 'worker_principal_id'])
        (principal (field data 'owner_principal_id'))
        (principal (field data 'worker_principal_id'))
    ==
  ?:  =('work.comment' operation)
    &((keys data ~['body']) (comment-body:stead-team-codec (field data 'body')))
  ?:  =('work.delete' operation)  (keys data ~)
  ?.  =('work.complete' operation)  |
  ::  The final reducer must reject human-note when required outcomes exist;
  ::  this syntactic shape neither proves a human actor nor accepts any output.
  ?&  (keys data ~['basis' 'note'])
      =/  basis  (field data 'basis')
      =/  note  (field data 'note')
      ?|  &(=('accepted-outcomes' basis) =('' note))
          &(=('human-note' basis) (comment-body:stead-team-codec note))
      ==
  ==
++  decode
  |=  raw=@t
  ^-  command
  =/  value  (need (parse-product raw))
  ?>  ?=([%o *] value)
  =/  data  p.value
  ?>  (keys data ~['protocol' 'request_id' 'project_id' 'resource_id' 'authority_epoch' 'operation' 'expected' 'payload'])
  ?>  =('stead.command/4' (field data 'protocol'))
  =/  request  (field data 'request_id')
  =/  project  (field data 'project_id')
  =/  resource  (field data 'resource_id')
  ?>  &((uuid request) (uuid project) (uuid resource))
  =/  epoch  (uint (field data 'authority_epoch'))
  ?>  (gth epoch 0)
  =/  operation  (field data 'operation')
  =/  expected  (object-field data 'expected')
  =/  payload  (object-field data 'payload')
  ?>  (expected-shape operation expected)
  ?>  (payload-shape operation project resource payload)
  =/  bytes  (canonical value)
  [request project resource epoch operation expected payload bytes (hash 'stead.command/4' bytes)]
--
