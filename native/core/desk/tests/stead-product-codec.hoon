::  Reserved pure decoder tests. Not registered or activated in Home yet.
/+  *test, stead-codec, stead-core, stead-product-codec
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  put
  |=  [value=json name=@t replacement=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) name replacement)]
++  wire
  |=  [operation=@t expected=json payload=json]
  ^-  json
  =/  value
    (object ~[['protocol' 'stead.command/4'] ['request_id' (id 301)] ['project_id' (id 100)] ['resource_id' (id 101)] ['authority_epoch' '1'] ['operation' operation]])
  (put (put value 'expected' expected) 'payload' payload)
++  refused
  |=  value=json
  ^-  ?
  =/  attempt  (mule |.((decode:stead-product-codec (canonical value))))
  ?=([%| *] attempt)
++  properties
  ^-  json
  (object ~[['type' 'task'] ['status' 'todo'] ['priority' 'none'] ['owner_principal_id' ''] ['worker_principal_id' ''] ['blocked_reason' '']])
++  contract
  |=  outcomes=json
  ^-  json
  (put (object ~[['title' 'Draft'] ['description' 'Exact notes'] ['acceptance_criteria' 'Reviewed and accepted']]) 'required_outcomes' outcomes)
++  create
  |=  outcomes=json
  ^-  json
  =/  goal  (contract outcomes)
  ?>  ?=([%o *] goal)
  =/  props  properties
  ?>  ?=([%o *] props)
  (wire 'work.create' (object ~[['work_revision' '0'] ['execution_contract_revision' '0']]) [%o (~(uni by p.props) p.goal)])
++  doc-target
  ^-  json
  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '0'] ['base_markdown_sha256' '']])
++  code-target
  ^-  json
  (object ~[['kind' 'code'] ['project_id' (id 100)] ['repository_id' (id 202)] ['target_ref' 'refs/heads/main'] ['base_oid' 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb']])
++  note-target
  ^-  json
  (object ~[['kind' 'completion-note'] ['project_id' (id 100)] ['work_id' (id 101)] ['expected_revision' '0']])
++  outcomes
  ^-  json
  [%o (malt ~[[(id 401) doc-target] [(id 402) code-target] [(id 403) note-target]])]
++  contract-wire
  |=  value=json
  ^-  json
  (wire 'work.update-contract' (object ~[['execution_contract_revision' '2']]) (contract value))
--
|%
++  test-product-codec-split-operations-and-preconditions
  =/  created  (decode:stead-product-codec (canonical (create outcomes)))
  =/  empty  (decode:stead-product-codec (canonical (create (object ~))))
  =/  docs  (decode:stead-product-codec (canonical (create [%o (malt ~[[(id 401) doc-target]])])))
  =/  edited  (decode:stead-product-codec (canonical (wire 'work.update-properties' (object ~[['work_revision' '5']]) properties)))
  =/  goal  (decode:stead-product-codec (canonical (contract-wire outcomes)))
  =/  comment  (decode:stead-product-codec (canonical (wire 'work.comment' (object ~[['discussion_sequence' '0']]) (object ~[['body' 'Question']]))))
  =/  deleted  (decode:stead-product-codec (canonical (wire 'work.delete' (object ~[['work_revision' '5'] ['execution_contract_revision' '2'] ['discussion_sequence' '7']]) (object ~))))
  %-  expect
  !>  ?&  =('work.create' operation.created)
          =('work.create' operation.empty)  =('work.create' operation.docs)
          =('0' (field expected.created 'execution_contract_revision'))
          =('5' (field expected.edited 'work_revision'))
          !(~(has by expected.edited) 'execution_contract_revision')
          =('2' (field expected.goal 'execution_contract_revision'))
          !(~(has by expected.goal) 'work_revision')
          =('0' (field expected.comment 'discussion_sequence'))
          =('7' (field expected.deleted 'discussion_sequence'))
      ==
++  test-product-codec-rejects-legacy-and-mixed-revision-envelopes
  =/  ordinary  (wire 'work.update-properties' (object ~[['work_revision' '1']]) properties)
  =/  missing  (put ordinary 'expected' (object ~))
  =/  mixed  (put ordinary 'expected' (object ~[['work_revision' '1'] ['execution_contract_revision' '1']]))
  =/  wrong  (put ordinary 'expected' (object ~[['discussion_sequence' '1']]))
  =/  old  (put (put ordinary 'protocol' [%s 'stead.command/3']) 'expected_revision' [%s '1'])
  =/  zero  (put ordinary 'expected' (object ~[['work_revision' '0']]))
  =/  leading  (put ordinary 'expected' (object ~[['work_revision' '01']]))
  =/  overflow  (put ordinary 'expected' (object ~[['work_revision' '18446744073709551616']]))
  %-  expect
  !>  ?&  (refused missing)  (refused mixed)  (refused wrong)  (refused old)
          (refused zero)  (refused leading)  (refused overflow)
          (refused (put ordinary 'authority_epoch' [%s '0']))
          (refused (put ordinary 'operation' [%s 'work.update']))
          (refused (put (create (object ~)) 'expected' (object ~[['work_revision' '1'] ['execution_contract_revision' '0']])))
      ==
++  test-product-codec-status-blocking-and-legacy-disposition
  =/  base  (wire 'work.update-properties' (object ~[['work_revision' '1']]) properties)
  =/  review  (put properties 'status' [%s 'in_review'])
  =/  blocked  (put review 'blocked_reason' [%s 'Waiting for the reviewer'])
  =/  accepted  (decode:stead-product-codec (canonical (put base 'payload' blocked)))
  =/  retained-done  (decode:stead-product-codec (canonical (put base 'payload' (put properties 'status' [%s 'done']))))
  =/  creation  (create (object ~))
  ?>  ?=([%o *] creation)
  =/  creation-payload  (~(got by p.creation) 'payload')
  %-  expect
  !>  ?&  =('in_review' (field payload.accepted 'status'))
          =('Waiting for the reviewer' (field payload.accepted 'blocked_reason'))
          =('done' (field payload.retained-done 'status'))
          (refused (put creation 'payload' (put creation-payload 'status' [%s 'done'])))
          (refused (put base 'payload' (put properties 'status' [%s 'blocked'])))
          (refused (put base 'payload' (put properties 'status' [%s 'legacy-blocked'])))
          (refused (put base 'payload' (put blocked 'status' [%s 'canceled'])))
          (refused (put base 'payload' (put blocked 'status' [%s 'done'])))
          (refused (put base 'payload' (put properties 'legacy_blocked' [%s 'yes'])))
          (refused (put base 'payload' (put properties 'blocked_reason' [%s '   '])))
          (refused (put base 'payload' (put properties 'owner_principal_id' [%s '~bus'])))
      ==
++  test-product-codec-targets-pin-scope-and-base
  =/  saved-doc  (put (put doc-target 'expected_revision' [%s '9']) 'base_markdown_sha256' [%s 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'])
  =/  decoded  (decode:stead-product-codec (canonical (contract-wire (put outcomes (id 401) saved-doc))))
  %-  expect
  !>  ?&  =('work.update-contract' operation.decoded)
          (refused (contract-wire (put outcomes (id 401) (put doc-target 'project_id' [%s (id 999)]))))
          (refused (contract-wire (put outcomes (id 401) (put doc-target 'expected_revision' [%s '1']))))
          (refused (contract-wire (put outcomes (id 401) (put saved-doc 'expected_revision' [%s '0']))))
          (refused (contract-wire (put outcomes (id 401) (put saved-doc 'base_markdown_sha256' [%s 'not-a-digest']))))
          (refused (contract-wire (put outcomes (id 402) (put code-target 'target_ref' [%s 'refs/tags/release']))))
          (refused (contract-wire (put outcomes (id 402) (put code-target 'head_oid' [%s 'cccccccccccccccccccccccccccccccccccccccc']))))
          (refused (contract-wire (put outcomes (id 403) (put note-target 'work_id' [%s (id 999)]))))
          (refused (contract-wire (put outcomes 'unscoped-name' doc-target)))
      ==
++  test-product-codec-closed-fields-never-trust-client-authority
  =/  base  (wire 'work.comment' (object ~[['discussion_sequence' '0']]) (object ~[['body' 'Question']]))
  =/  props  (wire 'work.update-properties' (object ~[['work_revision' '1']]) properties)
  %-  expect
  !>  ?&  (refused (put base 'principal_id' [%s (id 888)]))
          (refused (put base 'authentication_context' [%s '{}']))
          (refused (put base 'payload' (object ~[['body' 'Question'] ['principal_id' (id 888)]])))
          (refused (put base 'payload' (object ~[['body' 'Question'] ['accepted_at_ms' '1000']])))
          (refused (put props 'payload' (put properties 'title' [%s 'Hidden goal edit'])))
          (refused (put (contract-wire outcomes) 'payload' (put (contract outcomes) 'status' [%s 'done'])))
          (refused (put base 'operation' [%s 'extension.arbitrary']))
      ==
++  test-product-codec-completion-is-explicit-and-bounded
  =/  accepted  (wire 'work.complete' (object ~[['work_revision' '4'] ['execution_contract_revision' '2']]) (object ~[['basis' 'accepted-outcomes'] ['note' '']]))
  =/  human  (put accepted 'payload' (object ~[['basis' 'human-note'] ['note' 'Resolved with the customer.']]))
  =/  one  (decode:stead-product-codec (canonical accepted))
  =/  two  (decode:stead-product-codec (canonical human))
  %-  expect
  !>  ?&  =('accepted-outcomes' (field payload.one 'basis'))
          =('human-note' (field payload.two 'basis'))
          (refused (put accepted 'payload' (object ~[['basis' 'legacy'] ['note' '']])))
          (refused (put accepted 'payload' (object ~[['basis' 'human-note'] ['note' '']])))
          (refused (put accepted 'payload' (object ~[['basis' 'accepted-outcomes'] ['note' 'Override']])))
          (refused (put accepted 'payload' (object ~[['basis' 'human-note'] ['note' (rap 3 (reap 2.049 'a'))]])))
          (refused (put accepted 'expected' (object ~[['work_revision' '4']])))
      ==
++  test-product-codec-canonical-exact-bytes-and-domain
  =/  body  (cat 3 'Exact λ <text>  ' 10)
  =/  request  (wire 'work.comment' (object ~[['discussion_sequence' '0']]) (object ~[['body' body]]))
  =/  raw  (canonical request)
  =/  decoded  (decode:stead-product-codec (cat 3 '  ' (cat 3 raw 10)))
  =/  roundtrip  (decode:stead-product-codec canonical-bytes.decoded)
  %-  expect
  !>  ?&  =(raw canonical-bytes.decoded)
          =(decoded roundtrip)  =(body (field payload.decoded 'body'))
          =('b4e24f08d8bea370485f53b606afc9b04ac919aba93dcd675f45fa41cd532fdb' digest.decoded)
          !=(digest.decoded (hash 'stead.command/3' raw))
      ==
++  test-product-codec-legacy-resolutions-are-explicit
  =/  base  (wire 'work.resolve-legacy-blocked' (object ~[['work_revision' '4']]) (object ~[['status' 'todo'] ['blocked_reason' '']]))
  =/  resolved  (decode:stead-product-codec (canonical base))
  =/  waiting  (decode:stead-product-codec (canonical (put base 'payload' (object ~[['status' 'in_review'] ['blocked_reason' 'Needs reviewer']]))))
  =/  assignee  (wire 'work.resolve-legacy-assignee' (object ~[['work_revision' '4']]) (object ~[['owner_principal_id' ''] ['worker_principal_id' '']]))
  =/  cleared  (decode:stead-product-codec (canonical assignee))
  %-  expect
  !>  ?&  =('work.resolve-legacy-blocked' operation.resolved)
          =('4' (field expected.resolved 'work_revision'))
          =('Needs reviewer' (field payload.waiting 'blocked_reason'))
          (refused (put base 'payload' (object ~[['status' 'done'] ['blocked_reason' '']])))
          (refused (put base 'payload' (object ~[['status' 'canceled'] ['blocked_reason' '']])))
          (refused (put base 'expected' (object ~[['execution_contract_revision' '4']])))
          =('work.resolve-legacy-assignee' operation.cleared)
          =('' (field payload.cleared 'owner_principal_id'))
          (refused (put assignee 'payload' (object ~[['owner_principal_id' '~bus'] ['worker_principal_id' '']])))
          (refused (put assignee 'payload' (object ~[['owner_principal_id' ''] ['worker_principal_id' ''] ['resolved' 'yes']])))
      ==
++  test-product-codec-parser-size-depth-and-duplicate-bounds
  =/  duplicate  '{"protocol":"stead.command/4","protocol":"stead.command/4"}'
  =/  nested  '{"a":{"b":{"c":{"d":{"e":"too deep"}}}}}'
  =/  array  '{"payload":[]}'
  =/  too-long  (rap 3 (reap 65.537 ' '))
  =/  entries=(map @t json)  ~
  =/  counter=@ud  0
  =/  seventeen
    |-
    ?:  =(17 counter)  [%o entries]
    $(counter +(counter), entries (~(put by entries) (id (add 400 counter)) doc-target))
  %-  expect
  !>  ?&  ?=(~ (parse-product:stead-product-codec duplicate))
          ?=(~ (parse-product:stead-product-codec nested))
          ?=(~ (parse-product:stead-product-codec array))
          ?=(~ (parse-product:stead-product-codec too-long))
          (refused (contract-wire seventeen))
          (refused (put (contract-wire outcomes) 'payload' (put (contract outcomes) 'description' [%s (rap 3 (reap 8.193 'a'))])))
          (refused (put (contract-wire outcomes) 'payload' (put (contract outcomes) 'acceptance_criteria' [%s (rap 3 (reap 8.193 'a'))])))
      ==
--
