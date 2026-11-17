::  PRIVATE six authored codec/identity cases, not native execution.
::  Exact hex cords are public synthetic vector bytes. Decoding a claimed
::  native/browser authentication for hashing does not authenticate it.
/+  *test, stead-codec, stead-core, stead-team, stead-team-codec, stead-model-turn-codec
=,  stead-codec
=>
|%
++  question-wire
  ^-  @t
  0x7d223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c223130303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f74736575716572222c22312f646e616d6d6f632d6e7275742d6c65646f6d2e6461657473223a226c6f636f746f7270222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c227d225c37336530663130383134626262396364656436353166613139343232356135623164316331306262663335646365323264663964343536353264386536323737225c3a225c7473656769645f6e6f69746176726573626f5f73756f6976657270225c2c225c3031373030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f7463656666655f73756f6976657270225c2c225c30225c3a225c65636e65757165735f6e6f6974736575715f6465746365707865225c2c225c3231225c3a225c65636e65757165735f6e6f69737375637369645f6465746365707865225c7b223a2264616f6c796170222c226e6f697473657571223a226e6f6974617265706f222c2231223a226e7275745f6465746365707865222c2234223a226e6f6973697665725f6e75725f6465746365707865222c2231223a2274706d657474615f6465746365707865227b
++  answer-wire
  ^-  @t
  0x7d223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c223230303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f74736575716572222c22312f646e616d6d6f632d6e7275742d6c65646f6d2e6461657473223a226c6f636f746f7270222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c227d225c20202e73656c706d6178652080989ff0202f20bbce20646e612065746f6e2079746566617320656874207065654b6e5c5c2e736574616d6d6165742077654e225c3a225c74786574225c2c225c31225c3a225c65636e65757165735f6e6f697473657571225c2c225c62633430666531333361313236633165326631316631326435643134393365646136323930643335396532383964623963303533613662373232643234303764225c3a225c7473656769645f746e657261705f6e6f697473657571225c2c225c3331225c3a225c65636e65757165735f6e6f69737375637369645f6465746365707865225c7b223a2264616f6c796170222c22726577736e61223a226e6f6974617265706f222c2231223a226e7275745f6465746365707865222c2235223a226e6f6973697665725f6e75725f6465746365707865222c2231223a2274706d657474615f6465746365707865227b
++  clarification-wire
  ^-  @t
  0x7d223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c223330303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f74736575716572222c22312f646e616d6d6f632d6e7275742d6c65646f6d2e6461657473223a226c6f636f746f7270222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c227d225c31225c3a225c65636e65757165735f6e6f697473657571225c2c225c37336530663130383134626262396364656436353166613139343232356135623164316331306262663335646365323264663964343536353264386536323737225c3a225c7473656769645f6e6f69746176726573626f5f73756f6976657270225c2c225c3031373030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f7463656666655f73756f6976657270225c2c225c65323061383064323863383266356434393866623263663534353137313262626664396630333463633362633833386265653737313336636566323134333361225c3a225c7473656769645f746e657261705f726577736e61225c7b223a2264616f6c796170222c226e6f6974616369666972616c63223a226e6f6974617265706f222c2231223a226e7275745f6465746365707865222c2236223a226e6f6973697665725f6e75725f6465746365707865222c2231223a2274706d657474615f6465746365707865227b
++  revision-wire
  ^-  @t
  0x7d223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c223430303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f74736575716572222c22312f646e616d6d6f632d6e7275742d6c65646f6d2e6461657473223a226c6f636f746f7270222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c227d225c3530303930303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f747365757165725f776569766572225c2c225c3330313030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f6c617069636e6972705f776569766572225c2c225c33373237383633313338333066663031613836653933303936386338313535313831643231333966373166633738633331356263313964376137303135663834225c3a225c7473656769645f646e616d6d6f635f776569766572225c2c225c31225c3a225c6e6f6973697665725f746c75736572225c2c225c62336238396263636438326536623335306237366239333437326565333332306639653837326539666235303036343664306136343363653138323163323365225c3a225c7473656769645f746c75736572225c2c225c39626139336164363261316361393731623266373235626365393733363433663031303338663331366164643863353164343135353862393364613062326538225c3a225c7473656769645f6e6f69746176726573626f5f73756f6976657270225c2c225c3131373030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f7463656666655f73756f6976657270225c2c225c32225c3a225c6e6f6973697665725f65676e6168635f6465746365707865225c2c225c3230363030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f65676e616863225c7b223a2264616f6c796170222c226e6f697369766572223a226e6f6974617265706f222c2232223a226e7275745f6465746365707865222c223031223a226e6f6973697665725f6e75725f6465746365707865222c2231223a2274706d657474615f6465746365707865227b
++  question-seed
  ^-  @t
  0x7d223231313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6b726f77222c223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c2262373137663566613263396130636133333035653066653339653564316535663833366532303135313735643763306538343262663561393031636361313266223a223635326168735f74636172746e6f635f6e7572222c2231223a2265636e65757165735f6e6f697473657571222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c223130303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f747365757165725f746e65726170222c2262633430666531333361313236633165326631316631326435643134393365646136323930643335396532383964623963303533613662373232643234303764223a223635326168735f6c6163696e6f6e61635f746e65726170222c2231223a226e7275745f6d6f7266222c2235653834366431663437646464386165656366636435326630633433633062313262616634326534396162653961656332373836376466383531633430306537223a223635326168735f6e6f6974616369746e6568747561222c2231223a2274706d65747461222c223430313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6c617069636e6972705f726f746361222c2231223a226e6f6973697665725f676e69646e69625f726f746361222c223430323030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f676e69646e69625f726f746361227b
++  answer-seed
  ^-  @t
  0x7d223231313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6b726f77222c223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c2262373137663566613263396130636133333035653066653339653564316535663833366532303135313735643763306538343262663561393031636361313266223a223635326168735f74636172746e6f635f6e7572222c2231223a2265636e65757165735f6e6f697473657571222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c223230303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f747365757165725f746e65726170222c2265323061383064323863383266356434393866623263663534353137313262626664396630333463633362633833386265653737313336636566323134333361223a223635326168735f6c6163696e6f6e61635f746e65726170222c2231223a226e7275745f6d6f7266222c2235333336356236656137386438623061303131323330343538613864303133613562636265613132386337653736336630306632326134323463666434623335223a223635326168735f6e6f6974616369746e6568747561222c2231223a2274706d65747461222c223230313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6c617069636e6972705f726f746361222c2231223a226e6f6973697665725f676e69646e69625f726f746361222c223230323030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f676e69646e69625f726f746361227b
++  clarification-seed
  ^-  @t
  0x7d223231313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6b726f77222c223030363030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e7572222c2262373137663566613263396130636133333035653066653339653564316535663833366532303135313735643763306538343262663561393031636361313266223a223635326168735f74636172746e6f635f6e7572222c2231223a2265636e65757165735f6e6f697473657571222c223030313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f7463656a6f7270222c223330303930303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f747365757165725f746e65726170222c2264363863373735366163616630663330336465303335663566643462383338396337383461383462363834376562326631323939613763653937643037623366223a223635326168735f6c6163696e6f6e61635f746e65726170222c2231223a226e7275745f6d6f7266222c2235653834366431663437646464386165656366636435326630633433633062313262616634326534396162653961656332373836376466383531633430306537223a223635326168735f6e6f6974616369746e6568747561222c2231223a2274706d65747461222c223430313030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6c617069636e6972705f726f746361222c2231223a226e6f6973697665725f676e69646e69625f726f746361222c223430323030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f676e69646e69625f726f746361227b
++  agent-auth
  ^-  @t
  0x7d223630303030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6d616574222c22223a2264695f74696475615f6e6f6973736573222c22656b61662d646574616c6f7369223a22656d69746e7572222c223530303030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e6f6974617a696e6167726f222c227d225c3430313030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f6c617069636e697270225c2c225c6475627e225c3a225c706968735f797469746e656469225c2c225c31225c3a225c6e6f6973697665725f676e69646e6962225c2c225c3430323030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f676e69646e6962225c2c225c39393939393939225c3a225c736d5f74615f736572697078655f676e69646e6962225c7b223a22797469746e656469222c22646f7a7e223a22656d6f68222c2239393939393939223a22736d5f74615f736572697078655f6c6169746e6564657263222c227265646e65732d65766974616e223a226874676e657274735f6e6f6974616369746e6568747561222c22312f7265646e65732d65766974616e223a226e6f6974616369746e6568747561227b
++  human-auth
  ^-  @t
  0x7d223630303030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6d616574222c22223a2264695f74696475615f6e6f6973736573222c22656b61662d646574616c6f7369223a22656d69746e7572222c223530303030303030303030302d303030382d303030372d303030342d6162393339393130223a2264695f6e6f6974617a696e6167726f222c227d225c3230313030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f6c617069636e697270225c2c225c7375627e225c3a225c706968735f797469746e656469225c2c225c31225c3a225c6e6f6973697665725f676e69646e6962225c2c225c3230323030303030303030302d303030382d303030372d303030342d6162393339393130225c3a225c64695f676e69646e6962225c2c225c39393939393939225c3a225c736d5f74615f736572697078655f676e69646e6962225c7b223a22797469746e656469222c22646f7a7e223a22656d6f68222c2239393939393939223a22736d5f74615f736572697078655f6c6169746e6564657263222c227265646e65732d65766974616e223a226874676e657274735f6e6f6974616369746e6568747561222c22312f7265646e65732d65766974616e223a226e6f6974616369746e6568747561227b
++  answer-exact
  ^-  @t
  0x20202e73656c706d6178652080989ff0202f20bbce20646e612065746f6e2079746566617320656874207065654b0a2e736574616d6d6165742077654e
++  id
  |=  n=@ud
  ^-  @t
  ?>  (lte n 9.999)
  =/  text  (decimal n)
  (fixture-id:stead-core (cat 3 (fil 3 (sub 12 (met 3 text)) '0') text))
++  parsed
  |=  raw=@t
  ^-  json
  (need (parse-result raw))
++  put
  |=  [value=json key=@t next=json]
  ^-  json
  ?>  ?=([%o *] value)
  [%o (~(put by p.value) key next)]
++  outer
  |=  [raw=@t key=@t next=json]
  ^-  @t
  (canonical (put (parsed raw) key next))
++  payload
  |=  raw=@t
  ^-  @t
  =/  value  (parsed raw)
  ?>  ?=([%o *] value)
  (field p.value 'payload')
++  inner
  |=  [raw=@t key=@t next=json]
  ^-  @t
  (outer raw 'payload' [%s (canonical (put (parsed (payload raw)) key next))])
++  refused
  |=  raw=@t
  ^-  ?
  ?=([%| *] (mule |.((decode:stead-model-turn-codec raw))))
++  duplicate
  |=  [raw=@t key=@t text=@t]
  ^-  @t
  (rap 3 ~['{' (quote key) ':' (quote text) ',' (cut 3 [1 (dec (met 3 raw))] raw)])
++  unquoted
  ::  Emit the invalid number/boolean token directly; the production canonical
  ::  writer intentionally supports neither and must not be the failing gate.
  |=  [raw=@t key=@t token=@t]
  ^-  @t
  =/  value  (parsed raw)
  ?>  ?=([%o *] value)
  =/  rest  (canonical [%o (~(del by p.value) key)])
  (rap 3 ~['{' (quote key) ':' token ',' (cut 3 [1 (dec (met 3 rest))] rest)])
++  child-refused
  |=  [cmd=command:stead-model-turn-codec role=@tas actor=authentication:stead-team work=@t contract=@t question=@ud]
  ^-  ?
  ?=([%| *] (mule |.((child-request:stead-model-turn-codec cmd role actor work contract question))))
++  contract
  ^-  @t
  'f21acc109a5fb248e0c7d5715102e638f5e1d5e93ef0e5033ac0a9c2af5f717b'
--
|%
++  test-model-turn-codec-four-exact-parent-vectors
  =/  question  (decode:stead-model-turn-codec question-wire)
  =/  answer  (decode:stead-model-turn-codec answer-wire)
  =/  clarification  (decode:stead-model-turn-codec clarification-wire)
  =/  revision  (decode:stead-model-turn-codec revision-wire)
  =/  roundtrips=(list [raw=@t digest=@t size=@ud])
    :~  [question-wire 'd7042d227b6a350c9bd982e953d0926ade3941d5d21f11f2e1c621a331ef04cb' 543]
        [answer-wire 'a33412fec63177eeb838cb3cc430f9dfbb2171545fc2bf894d5f28c82d08a02e' 540]
        [clarification-wire 'f3b70d79ec7a9921f2be7486b48a487c9838b4df5f530ed303f0faca6577c86d' 593]
        [revision-wire '29aa70680af7f658ca121418fd9cc83dc28bffaf5ba16e0ea29c5f439e6ccb3d' 893]
    ==
  =/  question-op=operation:stead-model-turn-codec
    [%question (id 710) '7726e8d25654d9fd22ecd53fbb01c1d1b5a522491af156dedc9bbb41801f0e37' 0 12]
  =/  answer-op=operation:stead-model-turn-codec
    [%answer 1 digest.question 13 answer-exact]
  =/  clarification-op=operation:stead-model-turn-codec
    [%clarification (id 710) '7726e8d25654d9fd22ecd53fbb01c1d1b5a522491af156dedc9bbb41801f0e37' 1 digest.answer]
  =/  revision-op=operation:stead-model-turn-codec
    :*  %revision  (id 711)  '8e2b0ad39b85514d15c8dda613f83010f346379ecb527f2b179ac1a26da39ab9'
        (id 602)  1  'e32c1281ec346a0d646005bf9e278e9f0233ee27439b67b053b6e28dccb98b3b'  2
        (id 103)  (id 9.005)  '48f5107a7d91cb513c87cf17f9312d1815518c869039e68a10ff038313687273'
    ==
  %-  expect
  !>  ?&  =(question-op operation.question)  =(answer-op operation.answer)
          =(clarification-op operation.clarification)  =(revision-op operation.revision)
          =([4 1 1] [expected.question attempt.question turn.question])
          =([5 1 1] [expected.answer attempt.answer turn.answer])
          =([6 1 1] [expected.clarification attempt.clarification turn.clarification])
          =([10 1 2] [expected.revision attempt.revision turn.revision])
          =((id 9.001) request.question)  =((id 9.002) request.answer)
          =((id 9.003) request.clarification)  =((id 9.004) request.revision)
          %+  levy  roundtrips
          |=  row=[raw=@t digest=@t size=@ud]
          =/  cmd  (decode:stead-model-turn-codec raw.row)
          ?&  =(raw.row canonical-bytes.cmd)  =(digest.row digest.cmd)
              =(size.row (met 3 raw.row))  =((id 100) project.cmd)  =((id 600) run.cmd)
              =(raw.row (command-bytes:stead-model-turn-codec cmd))
          ==
      ==
++  test-model-turn-codec-closed-canonical-claim-boundary
  =/  names=(list @t)  ~['actor' 'ship' 'principal_id' 'clock' 'permission' 'accepted']
  %-  expect
  !>  ?&  (refused (duplicate question-wire 'request_id' (id 9.001)))
          (refused (cat 3 ' ' question-wire))
          (refused (outer question-wire 'payload' [%s (cat 3 ' ' (payload question-wire))]))
          (refused (outer question-wire 'payload' [%s (duplicate (payload question-wire) 'expected_question_sequence' '0')]))
          (refused (unquoted question-wire 'expected_attempt' '1'))
          (refused (outer question-wire 'payload' (parsed (payload question-wire))))
          (refused (outer question-wire 'payload' [%s (unquoted (payload question-wire) 'expected_question_sequence' '0')]))
          (refused (inner question-wire 'question' [%s 'Operator-injected question']))
          (refused (outer question-wire 'operation' [%s 'resume']))
          (refused (outer question-wire 'protocol' [%s 'stead.model-turn-command/2']))
          (refused (outer question-wire 'protocol' [%s 'stead.run-command/1']))
          (refused (outer question-wire 'protocol' [%s 'stead.model-effect-command/1']))
          %+  levy  names
          |=  name=@t
          &((refused (outer question-wire name [%s 'claimed'])) (refused (inner question-wire name [%s 'claimed'])))
      ==
++  test-model-turn-codec-ids-digests-and-finite-uints
  =/  bad=(list @t)  ~['01' '-1' '1e0' '' '18446744073709551616']
  =/  maximum  '18446744073709551615'
  =/  edge
    (decode:stead-model-turn-codec (inner (outer question-wire 'expected_run_revision' [%s maximum]) 'expected_discussion_sequence' [%s maximum]))
  =/  three  (decode:stead-model-turn-codec (outer (outer answer-wire 'expected_attempt' [%s '3']) 'expected_turn' [%s '3']))
  %-  expect
  !>  ?&  =(18.446.744.073.709.551.615 expected.edge)
          =(3 attempt.three)  =(3 turn.three)
          !(refused (inner question-wire 'expected_discussion_sequence' [%s '0']))
          (refused (outer question-wire 'expected_run_revision' [%s '0']))
          (refused (outer question-wire 'expected_attempt' [%s '0']))
          (refused (outer question-wire 'expected_attempt' [%s '4']))
          (refused (outer question-wire 'expected_turn' [%s '0']))
          (refused (outer question-wire 'expected_turn' [%s '4']))
          (refused (inner answer-wire 'question_sequence' [%s '0']))
          (refused (inner clarification-wire 'question_sequence' [%s '0']))
          (refused (inner revision-wire 'result_revision' [%s '0']))
          (refused (inner revision-wire 'expected_change_revision' [%s '0']))
          (refused (outer question-wire 'request_id' [%s '019939ba-4000-4000-8000-000000009001']))
          (refused (outer question-wire 'project_id' [%s '019939bA-4000-7000-8000-000000000100']))
          (refused (outer question-wire 'run_id' [%s '019939ba-4000-7000-7000-000000000600']))
          (refused (inner question-wire 'previous_effect_id' [%s 'wrong']))
          (refused (inner question-wire 'previous_observation_digest' [%s (fil 3 64 'A')]))
          (refused (inner answer-wire 'question_parent_digest' [%s (fil 3 63 'a')]))
          (refused (inner clarification-wire 'answer_parent_digest' [%s '']))
          (refused (inner revision-wire 'review_principal_id' [%s 'wrong']))
          (refused (inner revision-wire 'review_request_id' [%s 'wrong']))
          (refused (inner revision-wire 'review_command_digest' [%s 'wrong']))
          %+  levy  bad
          |=  text=@t
          ?&  (refused (outer question-wire 'expected_run_revision' [%s text]))
              (refused (inner question-wire 'expected_question_sequence' [%s text]))
              (refused (inner answer-wire 'expected_discussion_sequence' [%s text]))
          ==
      ==
++  test-model-turn-codec-exact-answer-utf8-and-comment-bounds
  =/  full  (cat 3 (fil 3 2.044 'a') '😀')
  =/  cmd  (decode:stead-model-turn-codec (inner answer-wire 'text' [%s full]))
  ?>  ?=(%answer -.operation.cmd)
  =/  original  (decode:stead-model-turn-codec answer-wire)
  ?>  ?=(%answer -.operation.original)
  =/  invalid=(list @t)
    :~  ''  '  '  (rap 3 ~[9 10 ' '])  (cat 3 'a' 13)
        (cat 3 'a' 1)  (cat 3 'a' 31)  (cat 3 full 'x')  (cat 3 'a' 255)
    ==
  %-  expect
  !>  ?&  =(2.048 (met 3 full))  =(full text.operation.cmd)
          =(answer-exact text.operation.original)
          !(refused (inner answer-wire 'text' [%s (rap 3 ~['Yes' 9 'λ' 10 '😀  '])]))
          !(refused (inner answer-wire 'text' [%s (fil 5 512 '😀')]))
          (refused (inner answer-wire 'text' [%s (fil 5 513 '😀')]))
          %+  levy  invalid
          |=  text=@t
          (refused (inner answer-wire 'text' [%s text]))
      ==
++  test-model-turn-codec-five-child-identities-are-not-authority
  =/  agent  (decode-authentication:stead-team agent-auth)
  =/  human  (decode-authentication:stead-team human-auth)
  =/  question  (decode:stead-model-turn-codec question-wire)
  =/  answer  (decode:stead-model-turn-codec answer-wire)
  =/  clarification  (decode:stead-model-turn-codec clarification-wire)
  =/  revision  (decode:stead-model-turn-codec revision-wire)
  ::  This is synthetic approved-browser audit DATA only: no session/CSRF
  ::  lookup is performed and no permission/receipt is returned by this core.
  =/  browser  human(method 'native-approved-browser/1', strength 'native-approved-browser', audit (hex 64 77), expires 9.000.000)
  =/  rows=(list [raw=@t actor=authentication:stead-team seed=@t role=@tas digest=@t request=@t])
    :~  [question-wire agent question-seed %question-run '8107530243a9fe81f47647e1de4d8acdd914f13959916048e9a396b8d64f2407' '019939ba-4000-7810-8753-0243a9fe81f4']
        [question-wire agent question-seed %question-comment 'cfd4055dc17d913e924d56a6304d6543f0f83a47cad6014db0da070c6c12c817' '019939ba-4000-7cfd-8405-5dc17d913e92']
        [answer-wire human answer-seed %answer-run '9eef7f36e67766cd291ddd97d0f626bbb6243bafcab8af4de9121c7871a9d894' '019939ba-4000-79ee-8f7f-36e67766cd29']
        [answer-wire human answer-seed %answer-comment '3ddc879b9db5f20944188ce1e43ff73b1350ce08a9e2c7b0f6e5a9545228f3d6' '019939ba-4000-73dd-8c87-9b9db5f20944']
        [clarification-wire agent clarification-seed %clarification-run '60fe1368d70ad3be3a311cc256aa8c0eba383b8915e6065c85eb39f22e22a484' '019939ba-4000-760f-8e13-68d70ad3be3a']
    ==
  =/  original-id  (child-request:stead-model-turn-codec question %question-run agent (id 112) contract 1)
  %-  expect
  !>  ?&  =(agent-auth (authentication-json:stead-team agent))
          =(human-auth (authentication-json:stead-team human))
          (child-refused question %answer-run agent (id 112) contract 1)
          (child-refused answer %question-comment human (id 112) contract 1)
          (child-refused clarification %answer-run agent (id 112) contract 1)
          (child-refused revision %clarification-run agent (id 112) contract 1)
          (child-refused question %unknown-role agent (id 112) contract 1)
          (child-refused question %question-run agent (id 112) contract 2)
          (child-refused question %question-run agent (id 112) 'wrong' 1)
          (child-refused question(digest (hex 64 1)) %question-run agent (id 112) contract 1)
          !=(original-id (child-request:stead-model-turn-codec question %question-run agent (id 113) contract 1))
          !=(original-id (child-request:stead-model-turn-codec question %question-run agent (id 112) (hex 64 2) 1))
          !=(original-id (child-request:stead-model-turn-codec question %question-run agent(identity identity.agent(revision 2)) (id 112) contract 1))
          !=((child-request:stead-model-turn-codec answer %answer-run human (id 112) contract 1) (child-request:stead-model-turn-codec answer %answer-run browser (id 112) contract 1))
          %+  levy  rows
          |=  row=[raw=@t actor=authentication:stead-team seed=@t role=@tas digest=@t request=@t]
          =/  cmd  (decode:stead-model-turn-codec raw.row)
          =/  seed  (seed-bytes:stead-model-turn-codec cmd actor.row (id 112) contract 1)
          ?&  =(seed.row seed)
              =(digest.row (hash (child-domain:stead-model-turn-codec operation.cmd role.row) seed))
              =(request.row (child-request:stead-model-turn-codec cmd role.row actor.row (id 112) contract 1))
          ==
      ==
++  test-model-turn-codec-escaped-limits-and-nested-shape-denials
  ::  Individual scalar ceilings do not promise a valid 65536-byte command.
  ::  A maximal legal quote answer expands twice but stays under that cap.
  =/  escaped  (fil 3 2.048 '"')
  =/  raw  (inner answer-wire 'text' [%s escaped])
  =/  cmd  (decode:stead-model-turn-codec raw)
  ?>  ?=(%answer -.operation.cmd)
  =/  oversized  (cat 3 (fil 3 65.537 ' ') question-wire)
  =/  unknown  (object ~[['unknown' 'nested']])
  =/  deep=json  [%o (malt ~[['a' [%o (malt ~[['b' unknown]])]]])]
  %-  expect
  !>  ?&  =(escaped text.operation.cmd)
          =(raw (command-bytes:stead-model-turn-codec cmd))
          (gth (met 3 raw) 6.000)  (lte (met 3 raw) 65.536)
          (refused oversized)
          (refused (outer question-wire 'payload' [%s (fil 3 65.537 ' ')]))
          (refused (outer question-wire 'payload' [%s (canonical deep)]))
          (refused (inner question-wire 'previous_observation_digest' unknown))
          (refused (inner answer-wire 'text' unknown))
          (refused (inner revision-wire 'review_command_digest' deep))
          (refused (inner clarification-wire 'new_context' [%s 'untrusted transcript']))
          (refused (outer answer-wire 'payload' [%s '{"question_sequence":"1","question_parent_digest":"x","expected_discussion_sequence":"0","text":true}']))
      ==
--
