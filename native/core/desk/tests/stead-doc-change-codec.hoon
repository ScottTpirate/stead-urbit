::  Source-only vectors; not registered or claimed as native execution.
/+  *test, stead-codec, stead-core, stead-doc-change-codec
=,  stead-codec
=>
|%
++  id
  |=  n=@ud
  ^-  @t
  ?>  &((gte n 100) (lte n 999))
  (fixture-id:stead-core (cat 3 '000000000' (decimal n)))
++  put
  |=  [value=json key=@t next=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key next)]
++  target
  ^-  json
  (object ~[['kind' 'document'] ['project_id' (id 100)] ['collection_id' (id 200)] ['document_id' (id 201)] ['expected_revision' '1'] ['base_markdown_sha256' 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa']])
++  payload
  ^-  json
  (put (object ~[['outcome_id' (id 401)] ['markdown' (cat 3 'Exact λ <text>  ' 10)] ['summary' 'Clarify the launch instructions'] ['execution_contract_revision' '2'] ['execution_contract_digest' 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'] ['run_id' ''] ['attempt' '0']]) 'target' target)
++  wire
  |=  [operation=@t expected=@t payload=json]
  ^-  json
  (put (object ~[['protocol' 'stead.doc-change/1'] ['request_id' (id 300)] ['project_id' (id 100)] ['work_id' (id 101)] ['change_id' (id 400)] ['authority_epoch' '1'] ['expected_revision' expected] ['operation' operation]]) 'payload' payload)
++  decision
  ^-  json
  (object ~[['result_revision' '1'] ['result_digest' 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc'] ['note' 'Please clarify the final step.']])
++  refused
  |=  value=json
  ^-  ?
  =/  attempted  (mule |.((decode:stead-doc-change-codec (canonical value))))
  ?=([%| *] attempted)
--
|%
++  test-doc-change-codec-exact-submission-and-result-pins
  =/  submitted  (decode:stead-doc-change-codec (canonical (wire 'change.submit' '0' payload)))
  =/  revised  (decode:stead-doc-change-codec (canonical (wire 'change.submit' '3' payload)))
  =/  approved  (decode:stead-doc-change-codec (canonical (wire 'change.approve' '1' decision)))
  =/  accepted  (decode:stead-doc-change-codec (canonical (wire 'change.accept' '2' decision)))
  %-  expect
  !>  ?&  =(0 expected.submitted)  =(3 expected.revised)
          =('change.approve' operation.approved)  =('change.accept' operation.accepted)
          =('1' (field payload.approved 'result_revision'))
          =((id 101) work.submitted)  =((id 400) change.submitted)
          (refused (wire 'change.accept' '0' decision))
          (refused (wire 'change.approve' '1' (put decision 'result_revision' [%s '0'])))
          (refused (wire 'change.accept' '1' (put decision 'result_digest' [%s 'short'])))
      ==
++  test-doc-change-codec-scope-base-and-run-pairs
  =/  fresh  (put (put target 'expected_revision' [%s '0']) 'base_markdown_sha256' [%s ''])
  =/  created  (decode:stead-doc-change-codec (canonical (wire 'change.submit' '0' (put payload 'target' fresh))))
  =/  run  (put (put payload 'run_id' [%s (id 500)]) 'attempt' [%s '1'])
  =/  agent  (decode:stead-doc-change-codec (canonical (wire 'change.submit' '0' run)))
  %-  expect
  !>  ?&  =('change.submit' operation.created)  =((id 500) (field payload.agent 'run_id'))
          (refused (wire 'change.submit' '0' (put payload 'target' (put target 'project_id' [%s (id 999)]))))
          (refused (wire 'change.submit' '0' (put payload 'target' (put target 'expected_revision' [%s '0']))))
          (refused (wire 'change.submit' '0' (put payload 'target' (put fresh 'expected_revision' [%s '1']))))
          (refused (wire 'change.submit' '0' (put payload 'run_id' [%s (id 500)])))
          (refused (wire 'change.submit' '0' (put payload 'attempt' [%s '1'])))
          (refused (wire 'change.submit' '0' (put payload 'execution_contract_revision' [%s '0'])))
          (refused (wire 'change.submit' '0' (put payload 'outcome_id' [%s 'latest'])))
      ==
++  test-doc-change-codec-never-decodes-authority-or-alternate-targets
  =/  base  (wire 'change.submit' '0' payload)
  =/  code  (object ~[['kind' 'code'] ['project_id' (id 100)] ['repository_id' (id 600)] ['target_ref' 'refs/heads/main'] ['base_oid' 'dddddddddddddddddddddddddddddddddddddddd']])
  %-  expect
  !>  ?&  (refused (put base 'producer_principal_id' [%s (id 700)]))
          (refused (put base 'payload' (put payload 'approved' [%s 'yes'])))
          (refused (put base 'payload' (put payload 'lease' [%s 'unlimited'])))
          (refused (put base 'payload' (put payload 'target' code)))
          (refused (put base 'payload' (put payload 'target' (put target 'visibility' [%s 'shared']))))
          (refused (put base 'protocol' [%s 'stead.command/4']))
          (refused (put base 'operation' [%s 'change.execute']))
          (refused (put base 'authority_epoch' [%s '01']))
          (refused (put base 'expected_revision' [%s '18446744073709551616']))
      ==
++  test-doc-change-codec-decisions-require-exact-output-and-explanation
  =/  empty  (put decision 'note' [%s ''])
  =/  approved  (decode:stead-doc-change-codec (canonical (wire 'change.approve' '2' empty)))
  =/  requested  (decode:stead-doc-change-codec (canonical (wire 'change.request-changes' '2' decision)))
  =/  adopted  (decode:stead-doc-change-codec (canonical (wire 'change.adopt' '2' decision)))
  =/  rejected  (decode:stead-doc-change-codec (canonical (wire 'change.reject' '2' decision)))
  =/  quarantined  (decode:stead-doc-change-codec (canonical (wire 'change.quarantine' '2' decision)))
  %-  expect
  !>  ?&  =('change.approve' operation.approved)  =('change.request-changes' operation.requested)
          =('change.adopt' operation.adopted)  =('change.reject' operation.rejected)
          =('change.quarantine' operation.quarantined)
          (refused (wire 'change.request-changes' '2' empty))
          (refused (wire 'change.adopt' '2' empty))
          (refused (wire 'change.reject' '2' empty))
          (refused (wire 'change.quarantine' '2' empty))
          (refused (wire 'change.adopt' '2' (put decision 'note' [%s '   '])))
          (refused (wire 'change.approve' '2' (put decision 'note' [%s (rap 3 (reap 2.049 'a'))])))
      ==
++  test-doc-change-codec-exact-markdown-and-canonical-domain
  =/  source  (wire 'change.submit' '0' payload)
  =/  raw  (canonical source)
  =/  decoded  (decode:stead-doc-change-codec (cat 3 '  ' (cat 3 raw 10)))
  =/  again  (decode:stead-doc-change-codec canonical-bytes.decoded)
  %-  expect
  !>  ?&  =(raw canonical-bytes.decoded)  =(decoded again)
          =((cat 3 'Exact λ <text>  ' 10) (field payload.decoded 'markdown'))
          =('8badc6f6292779c5c6b30d119d45fac8b8163647a6a7a6d08029a8efa1764223' digest.decoded)
          !=((hash 'stead.command/4' raw) digest.decoded)
          (refused (wire 'change.submit' '0' (put payload 'markdown' [%s (cat 3 'line' 13)])))
          (refused (wire 'change.submit' '0' (put payload 'markdown' [%s (rap 3 (reap 32.769 'a'))])))
      ==
++  test-doc-change-codec-bounds-duplicates-and-closed-depth
  =/  raw  (canonical (wire 'change.submit' '0' payload))
  =/  duplicate  (cat 3 '{"protocol":"stead.doc-change/1",' (cut 3 [1 (dec (met 3 raw))] raw))
  =/  repeated  (mule |.((decode:stead-doc-change-codec duplicate)))
  =/  oversized  (mule |.((decode:stead-doc-change-codec (rap 3 (reap 65.537 'a')))))
  =/  nested  (put payload 'markdown' (object ~[['text' 'body']]))
  %-  expect
  !>  ?&  ?=([%| *] repeated)  ?=([%| *] oversized)
          (refused (wire 'change.submit' '0' nested))
          (refused (wire 'change.approve' '1' (put decision 'result_revision' [%s '01'])))
          (refused (wire 'change.submit' '0' (put payload 'summary' [%s ''])))
      ==
--
