::  Prepared closed wire tests, not native execution or Home authority proof.
/+  *test, stead-codec, stead-core, stead-run-state, stead-run-codec
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
++  parsed
  |=  raw=@t
  ^-  json
  ?>  (lte (met 3 raw) 65.536)
  (need (parse-result raw))
++  refused
  |=  raw=@t
  ^-  ?
  ?=([%| *] (mule |.((decode:stead-run-codec raw))))
++  wire
  |=  [name=@t payload=@t expected=@t attempt=@t]
  ^-  json
  (object ~[['protocol' 'stead.run-command/1'] ['request_id' (id 300)] ['project_id' (id 100)] ['run_id' (id 401)] ['expected_revision' expected] ['expected_attempt' attempt] ['operation' name] ['payload' payload]])
++  task
  ^-  contract:stead-run-state
  :*  ~zod  (id 100)  (id 101)  1  2  (hex 64 5)
      (id 102)  (id 102)  %explicit  (id 107)  (id 807)  1
      (id 810)  1  (id 811)  1
      (scope-key:stead-core (id 100) (id 850))
      [(id 100) (id 107) 'contributor' 400.000 |]
      (hex 64 6)  ~[[(id 300) (id 200) (id 201) 0 '']]
      [300.000 [32 8 10.000 100.000 65.536 32.768]]  301.000
  ==
++  output
  ^-  result-reference:stead-run-state
  [(id 700) 1 (hex 64 7) (id 300)]
++  command
  |=  op=operation:stead-run-state
  ^-  command:stead-run-state
  [(id 300) (id 100) (id 401) ?:(?=(%issue -.op) 0 1) ?:(?=(?(%issue %claim) -.op) 0 1) op]
++  issue-refused
  |=  row=contract:stead-run-state
  ^-  ?
  (refused (command-bytes:stead-run-state (command [%issue row])))
--
|%
++  test-run-codec-portable-contract-and-normalized-targets
  =/  cmd  (command [%issue task])
  =/  raw  (command-bytes:stead-run-state cmd)
  =/  two  task(targets [[(id 301) (id 200) (id 202) 0 ''] targets.task])
  =/  multiple  (command [%issue two])
  =/  normalized  (normalize-contract:stead-run-state two)
  %-  expect
  !>  ?&  =(cmd (decode:stead-run-codec raw))
          =((contract-bytes:stead-run-state task) (operation-bytes:stead-run-state operation.cmd))
          =('8363546216f67077fb15b3c42123d55c95cfbb06692ddfa1f432b593385ec1af' (hash 'stead.run-contract/1' (contract-bytes:stead-run-state task)))
          =((command [%issue normalized]) (decode:stead-run-codec (command-bytes:stead-run-state multiple)))
          =((command-bytes:stead-run-state multiple) (command-bytes:stead-run-state (command [%issue normalized])))
      ==
++  test-run-codec-all-thirteen-typed-operations-roundtrip
  =/  operations=(list operation:stead-run-state)
    :~  [%issue task]  [%claim ~]  [%replace (hex 64 8)]  [%heartbeat ~]
        [%wait 'Which audience needs this guide?']  [%answer 1 'New members.']
        [%resume 1]  [%cancel 'Owner canceled this attempt.']
        [%fail 'Exact source unavailable.' (hex 64 9)]  [%finish output]
        [%intent [(id 901) %provider-call (id 902) (hex 64 10) ~ [0 1 100 10 50 100]]]
        [%settle [(id 901) %unknown (hex 64 11) '']]
        [%reconcile [(id 901) %settled (hex 64 12) (hex 64 13)]]
    ==
  %-  expect
  !>  ?&  =(13 (lent operations))
          %+  levy  operations
          |=  op=operation:stead-run-state
          =/  cmd  (command op)
          =(cmd (decode:stead-run-codec (command-bytes:stead-run-state cmd)))
      ==
++  test-run-codec-closed-envelope-and-canonical-nested-json
  =/  value  (wire 'claim' '' '1' '0')
  =/  raw  (canonical value)
  =/  duplicate  (cat 3 '{"request_id":"' (cat 3 (id 300) (cat 3 '",' (cut 3 [1 (dec (met 3 raw))] raw))))
  =/  issue  (wire 'issue' (contract-bytes:stead-run-state task) '0' '0')
  %-  expect
  !>  ?&  (refused duplicate)
          (refused (canonical (put value 'actor' [%s (id 102)])))
          (refused (canonical (put value 'session' [%s 'claimed-owner'])))
          (refused (canonical (put value 'protocol' [%s 'stead.run-command/2'])))
          (refused (canonical (put value 'operation' [%s 'execute-shell'])))
          (refused (canonical (put value 'payload' (object ~[['approved' 'yes']]))))
          (refused (canonical (put issue 'project_id' [%s (id 999)])))
          (refused (canonical (put issue 'payload' [%s (cat 3 ' ' (contract-bytes:stead-run-state task))])))
          (refused (cat 3 ' ' (fil 3 65.536 ' ')))
      ==
++  test-run-codec-bounded-distinct-doc-targets-and-exact-grant
  =/  same  task(targets [[(id 301) (id 200) (id 201) 9 (hex 64 15)] targets.task])
  =/  five
    %+  turn  ~[300 301 302 303 304]
    |=  n=@ud
    ^-  target:stead-run-state
    [(id n) (id 200) (id (add n 100)) 0 '']
  =/  nested  (parsed (contract-bytes:stead-run-state task))
  =/  unsafe  (put nested 'runtime_secret' [%s 'forbidden'])
  %-  expect
  !>  ?&  (issue-refused same)  (issue-refused task(targets five))
          (issue-refused task(targets ~))
          (issue-refused task(targets ~[[(id 300) (id 200) (id 201) 1 '']]))
          (issue-refused task(targets ~[[(id 300) (id 200) (id 201) 0 (hex 64 1)]]))
          (issue-refused task(grant grant.task(principal (id 999))))
          (issue-refused task(grant grant.task(project (id 999))))
          (issue-refused task(grant grant.task(revoked &)))
          (issue-refused task(grant grant.task(expires 300.999)))
          (issue-refused task(grant-key (scope-key:stead-core (id 999) (id 850))))
          (refused (canonical (wire 'issue' (canonical unsafe) '0' '0')))
      ==
++  test-run-codec-canonical-numbers-and-finite-text-budgets
  =/  value  (wire 'claim' '' '1' '0')
  =/  large  (fil 3 2.049 'a')
  %-  expect
  !>  ?&  (refused (canonical (put value 'expected_revision' [%s '01'])))
          (refused (canonical (put value 'expected_revision' [%s '18446744073709551616'])))
          (refused (canonical (put value 'expected_revision' [%s '0'])))
          (refused (canonical (put value 'expected_attempt' [%s '4'])))
          (refused (canonical (wire 'issue' (contract-bytes:stead-run-state task) '1' '0')))
          (refused (canonical (wire 'claim' 'unexpected' '1' '0')))
          (refused (canonical (wire 'wait' '' '1' '1')))
          (refused (canonical (wire 'wait' large '1' '1')))
          (refused (canonical (wire 'cancel' (fil 3 257 'a') '1' '1')))
          (refused (canonical (wire 'resume' '0' '1' '1')))
          (issue-refused task(budget budget.task(duration 3.600.001)))
          (issue-refused task(budget budget.task(limits limits.budget.task(tools 33))))
          (issue-refused task(budget budget.task(limits limits.budget.task(network 9))))
          (issue-refused task(budget budget.task(limits limits.budget.task(tokens 0))))
      ==
++  test-run-codec-effects-cannot-widen-kind-or-submit-fake-authority
  =/  doc=intent:stead-run-state  [(id 901) %doc-proposal '' '' (some output) [1 0 0 0 0 100]]
  =/  valid  (command [%intent doc])
  =/  item  (parsed (intent-bytes:stead-run-state doc))
  =/  unknown  (put item 'kind' [%s 'arbitrary-network'])
  =/  claims  (put item 'authorized' [%s 'yes'])
  %-  expect
  !>  ?&  =(valid (decode:stead-run-codec (command-bytes:stead-run-state valid)))
          (refused (canonical (wire 'intent' (canonical unknown) '1' '1')))
          (refused (canonical (wire 'intent' (canonical claims) '1' '1')))
          (refused (command-bytes:stead-run-state (command [%intent doc(provider (id 902))])))
          (refused (command-bytes:stead-run-state (command [%intent doc(result ~)])))
          (refused (command-bytes:stead-run-state (command [%intent doc(charge charge.doc(network 1))])))
          (refused (command-bytes:stead-run-state (command [%settle [(id 901) %unknown (hex 64 1) (hex 64 2)]])))
          (refused (command-bytes:stead-run-state (command [%reconcile [(id 901) %unknown (hex 64 1) '']])))
      ==
--
