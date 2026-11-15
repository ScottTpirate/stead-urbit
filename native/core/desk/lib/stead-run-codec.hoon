::  Reserved closed run intent decoder. No Home route/mark advertises it.
::  Claimed contract data is not authority: the reducer's current Home gates
::  must verify every pin. Nested JSON strings have one canonical encoding.
/+  stead-codec, stead-core, stead-run-state
=,  stead-codec
|%
++  object-of
  |=  [raw=@t names=(list @t)]
  ^-  object-map
  ::  A contract has23 closed fields; the ordinary request parser allows16.
  ::  Keep the request byte bound and enforce the exact keys at this seam.
  ?>  (lte (met 3 raw) 65.536)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  ?>  &((keys p.value names) =(raw (canonical value)))
  ?>  (levy ~(tap by p.value) |=([key=@t val=json] ?=([%s *] val)))
  p.value
++  positive
  |=  raw=@t
  ^-  @ud
  =/  value  (uint raw)
  ?>  (gth value 0)
  value
++  text
  |=  [raw=@t limit=@ud]
  ^-  @t
  ?>  &((gth (met 3 raw) 0) (prose raw limit))
  raw
++  digest
  |=  raw=@t
  ^-  @t
  ?>  (digest-valid:stead-run-state raw)
  raw
++  identity
  |=  raw=@t
  ^-  @t
  ?>  (uuid raw)
  raw
++  usage-of
  |=  raw=@t
  ^-  usage:stead-run-state
  =/  value  (object-of raw ~['tool_calls' 'network_calls' 'token_units' 'cost_units' 'input_bytes' 'output_bytes'])
  =/  row=usage:stead-run-state
    :*  (uint (field value 'tool_calls'))  (uint (field value 'network_calls'))
        (uint (field value 'token_units'))  (uint (field value 'cost_units'))
        (uint (field value 'input_bytes'))  (uint (field value 'output_bytes'))
    ==
  ?>  (usage-valid:stead-run-state row)
  row
++  result-of
  |=  raw=@t
  ^-  result-reference:stead-run-state
  =/  value  (object-of raw ~['change_id' 'result_revision' 'result_digest' 'outcome_id'])
  [(identity (field value 'change_id')) (positive (field value 'result_revision')) (digest (field value 'result_digest')) (identity (field value 'outcome_id'))]
++  grant-of
  |=  raw=@t
  ^-  grant-state:stead-core
  =/  value  (object-of raw ~['project_id' 'principal_id' 'role' 'expires_at_ms' 'revoked'])
  =/  role  (field value 'role')
  ?>  ?|(=('contributor' role) =('maintainer' role))
  ?>  =('no' (field value 'revoked'))
  [(identity (field value 'project_id')) (identity (field value 'principal_id')) role (positive (field value 'expires_at_ms')) |]
++  targets-of
  |=  [project=@t raw=@t]
  ^-  (list target:stead-run-state)
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  ?>  &(=(raw (canonical value)) (gth ~(wyt by p.value) 0) (lte ~(wyt by p.value) 4))
  =/  rows
    %+  turn  ~(tap by p.value)
    |=  [outcome=@t fields=json]
    ^-  target:stead-run-state
    ?>  &((uuid outcome) ?=([%o *] fields))
    =/  data  p.fields
    ?>  (keys data ~['kind' 'project_id' 'collection_id' 'document_id' 'expected_revision' 'base_markdown_sha256'])
    ?>  &(=('document' (field data 'kind')) =(project (field data 'project_id')))
    =/  revision  (uint (field data 'expected_revision'))
    =/  markdown  (field data 'base_markdown_sha256')
    ?>  ?:(=(0 revision) =('' markdown) (digest-valid:stead-run-state markdown))
    [outcome (identity (field data 'collection_id')) (identity (field data 'document_id')) revision markdown]
  ?>  =((lent rows) (lent ~(tap in (silt (turn rows |=(row=target:stead-run-state [collection.row document.row]))))))
  (sort rows |=([a=target:stead-run-state b=target:stead-run-state] (aor outcome.a outcome.b)))
++  contract-of
  |=  [project=@t raw=@t]
  ^-  contract:stead-run-state
  =/  value
    %+  object-of  raw
    :~  'home'  'project_id'  'work_id'  'authority_epoch'
        'execution_contract_revision'  'execution_contract_digest'
        'requester_id'  'owner_id'  'owner_source'  'worker_id'
        'binding_id'  'binding_revision'  'definition_id'  'definition_revision'
        'runtime_id'  'runtime_revision'  'grant_key'  'grant'
        'context_digest'  'targets'  'duration_ms'  'budget'  'deadline_ms'
    ==
  =/  home  (need (slaw %p (field value 'home')))
  ?>  &(=(project (field value 'project_id')) =((scot %p home) (field value 'home')) (lte (met 0 home) 128))
  =/  owner-source  (field value 'owner_source')
  ?>  ?|(=('explicit' owner-source) =('steward' owner-source))
  =/  row=contract:stead-run-state
    :*  home  project  (identity (field value 'work_id'))  (positive (field value 'authority_epoch'))
        (positive (field value 'execution_contract_revision'))  (digest (field value 'execution_contract_digest'))
        (identity (field value 'requester_id'))  (identity (field value 'owner_id'))
        ?:(=('explicit' owner-source) %explicit %steward)
        (identity (field value 'worker_id'))  (identity (field value 'binding_id'))  (positive (field value 'binding_revision'))
        (identity (field value 'definition_id'))  (positive (field value 'definition_revision'))
        (identity (field value 'runtime_id'))  (positive (field value 'runtime_revision'))
        (field value 'grant_key')  (grant-of (field value 'grant'))
        (digest (field value 'context_digest'))  (targets-of project (field value 'targets'))
        [(positive (field value 'duration_ms')) (usage-of (field value 'budget'))]
        (positive (field value 'deadline_ms'))
    ==
  ?>  ?&  !=(owner.row worker.row)  (lte duration.budget.row 3.600.000)
          =(project project.grant.row)  =(worker.row principal.grant.row)
          (lte deadline.row expires.grant.row)
          =(73 (met 3 grant-key.row))
          =((scope-key:stead-core project (cut 3 [37 36] grant-key.row)) grant-key.row)
          (uuid (cut 3 [37 36] grant-key.row))
          ?:  (gth network.limits.budget.row 0)
            &((gth tokens.limits.budget.row 0) (gth cost.limits.budget.row 0))
          &(=(0 tokens.limits.budget.row) =(0 cost.limits.budget.row))
      ==
  row
++  intent-of
  |=  raw=@t
  ^-  intent:stead-run-state
  =/  value  (object-of raw ~['effect_id' 'kind' 'provider_id' 'request_digest' 'result' 'charge'])
  =/  kind  (field value 'kind')
  ?>  ?|(=('provider-call' kind) =('doc-proposal' kind))
  =/  reference  (field value 'result')
  =/  row=intent:stead-run-state
    [(identity (field value 'effect_id')) ?:(=('provider-call' kind) %provider-call %doc-proposal) (field value 'provider_id') (field value 'request_digest') ?:(=('' reference) ~ (some (result-of reference))) (usage-of (field value 'charge'))]
  ?>  ?:  =(%provider-call kind.row)
        ?&  (uuid provider.row)  (digest-valid:stead-run-state request-digest.row)  ?=(~ result.row)
            =(1 network.charge.row)  (gth tokens.charge.row 0)  (gth cost.charge.row 0)
        ==
      ?&  ?=(^ result.row)  =('' provider.row)  =('' request-digest.row)
          =(0 network.charge.row)  =(0 tokens.charge.row)  =(0 cost.charge.row)
      ==
  row
++  settlement-of
  |=  [raw=@t reconcile=?]
  ^-  settlement:stead-run-state
  =/  value  (object-of raw ~['effect_id' 'status' 'evidence' 'result_digest'])
  =/  status  (field value 'status')
  ?>  ?|(=('settled' status) &(!reconcile =('unknown' status)))
  =/  result  (field value 'result_digest')
  ?>  ?:(=('settled' status) (digest-valid:stead-run-state result) =('' result))
  [(identity (field value 'effect_id')) ?:(=('settled' status) %settled %unknown) (digest (field value 'evidence')) result]
++  operation-of
  |=  [project=@t name=@t raw=@t]
  ^-  operation:stead-run-state
  ?:  =('issue' name)  [%issue (contract-of project raw)]
  ?:  =('claim' name)  ?>  =('' raw)  [%claim ~]
  ?:  =('heartbeat' name)  ?>  =('' raw)  [%heartbeat ~]
  ?:  =('replace' name)  [%replace (digest raw)]
  ?:  =('wait' name)  [%wait (text raw 2.048)]
  ?:  =('resume' name)  [%resume (positive raw)]
  ?:  =('cancel' name)  [%cancel (text raw 256)]
  ?:  =('finish' name)  [%finish (result-of raw)]
  ?:  =('intent' name)  [%intent (intent-of raw)]
  ?:  =('settle' name)  [%settle (settlement-of raw |)]
  ?:  =('reconcile' name)  [%reconcile (settlement-of raw &)]
  ?:  =('answer' name)
    =/  value  (object-of raw ~['question' 'text'])
    [%answer (positive (field value 'question')) (text (field value 'text') 2.048)]
  ?>  =('fail' name)
  =/  value  (object-of raw ~['reason' 'evidence'])
  [%fail (text (field value 'reason') 256) (digest (field value 'evidence'))]
++  decode
  |=  raw=@t
  ^-  command:stead-run-state
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  data  p.value
  ?>  (keys data ~['protocol' 'request_id' 'project_id' 'run_id' 'expected_revision' 'expected_attempt' 'operation' 'payload'])
  ?>  =('stead.run-command/1' (field data 'protocol'))
  =/  project  (identity (field data 'project_id'))
  =/  cmd=command:stead-run-state
    [(identity (field data 'request_id')) project (identity (field data 'run_id')) (uint (field data 'expected_revision')) (uint (field data 'expected_attempt')) (operation-of project (field data 'operation') (field data 'payload'))]
  ?>  (lte attempt.cmd 3)
  ?>  ?:(?=(%issue -.operation.cmd) &(=(0 expected.cmd) =(0 attempt.cmd)) (gth expected.cmd 0))
  ?>  =((canonical value) (command-bytes:stead-run-state cmd))
  cmd
--
