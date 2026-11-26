::  PRIVATE closed model parent decoder. These are typed CLAIMED bytes only.
::  No identity/current authority, effect admission, response normalization,
::  Run mutation, model dispatch, receipt acceptance or saved format is enabled.
/+  stead-codec, stead-run-state, stead-run-codec, stead-model-material
=,  stead-codec
|%
+$  observation
  [disposition=?(%response %unknown) reason=@t present=? response=octets:stead-model-material digest=@t]
+$  operation
  $%  [%reserve material=material:stead-model-material]
      [%observe reservation=@t item=observation]
  ==
+$  command
  [request=@t project=@t run=@t expected=@ud attempt=@ud effect=@t operation=operation canonical-bytes=@t digest=@t]
++  raw-response
  |=  text=@t
  ^-  octets:stead-model-material
  ?>  &((lte (met 3 text) 65.536) =(0 (mod (met 3 text) 2)))
  =/  length  (div (met 3 text) 2)
  =/  offset=@ud  0
  =/  data=@  0
  |-  ^-  octets:stead-model-material
  ?:  =(offset length)  [length data]
  =/  high  (nibble:stead-model-material (cut 3 [(mul offset 2) 1] text))
  =/  low  (nibble:stead-model-material (cut 3 [+(mul offset 2) 1] text))
  =/  byte  (add (mul 16 high) low)
  $(offset +(offset), data (mix data (lsh [3 offset] byte)))
++  observation-of
  |=  raw=@t
  ^-  observation
  =/  rows  (object-of:stead-run-codec raw ~['disposition' 'reason' 'response_hex' 'response_sha256'])
  =/  disposition  (field rows 'disposition')
  ?>  ?|(=('response' disposition) =('unknown' disposition))
  =/  reason  (field rows 'reason')
  =/  encoded  (field rows 'response_hex')
  =/  response  (raw-response encoded)
  =/  digest  (field rows 'response_sha256')
  =/  present  !=('' digest)
  ?>  ?:  present
        &((digest-valid:stead-run-state digest) =(digest (sha256:stead-model-material response)))
      &(=('unknown' disposition) =('' encoded))
  ?>  ?:  =('response' disposition)
        &(present =('' reason))
      ?&  ?|  =('timeout' reason)  =('transport' reason)  =('canceled' reason)
              =('invalid-response' reason)  =('incomplete-publication' reason)
          ==
          ?|(!=('invalid-response' reason) present)
      ==
  [?:(=('response' disposition) %response %unknown) reason present response digest]
++  decode
  |=  raw=@t
  ^-  command
  ?>  (lte (met 3 raw) 65.536)
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  rows  p.value
  =/  name  (field rows 'operation')
  ?>  ?|(=('reserve' name) =('observe' name))
  =/  names=(list @t)
    ?:  =('reserve' name)
      ~['protocol' 'operation' 'request_id' 'project_id' 'run_id' 'expected_run_revision' 'attempt' 'effect_id' 'materialization']
    ~['protocol' 'operation' 'request_id' 'project_id' 'run_id' 'expected_run_revision' 'attempt' 'effect_id' 'reservation_command_digest' 'observation']
  ?>  &((keys rows names) =(raw (canonical value)))
  ?>  (levy ~(tap by rows) |=([key=@t val=json] ?=([%s *] val)))
  ?>  =('stead.model-effect-command/1' (field rows 'protocol'))
  =/  request  (identity:stead-run-codec (field rows 'request_id'))
  =/  project  (identity:stead-run-codec (field rows 'project_id'))
  =/  run  (identity:stead-run-codec (field rows 'run_id'))
  =/  expected  (positive:stead-run-codec (field rows 'expected_run_revision'))
  =/  attempt  (positive:stead-run-codec (field rows 'attempt'))
  =/  effect  (identity:stead-run-codec (field rows 'effect_id'))
  ?>  (lte attempt 3)
  =/  operation=operation
    ?:  =('reserve' name)
      =/  material  (material-of:stead-model-material (field rows 'materialization'))
      ?>  ?&  =(project (field scope.material 'project_id'))
              =(run (field scope.material 'run_id'))
              =(attempt (uint (field scope.material 'attempt')))
              =(effect id.intent.material)
          ==
      [%reserve material]
    [%observe (digest:stead-run-codec (field rows 'reservation_command_digest')) (observation-of (field rows 'observation'))]
  [request project run expected attempt effect operation raw (hash 'stead.model-effect-command/1' raw)]
++  derived-request
  ::  Identity calculation only: caller must check the real global request
  ::  ownership ledger before staging. This pure gate grants no authority.
  |=  [cmd=command contract-digest=@t]
  ^-  @t
  ?>  (digest-valid:stead-run-state contract-digest)
  =/  seed
    %-  hash  :-  'stead.model-run-request-id/1'
    %-  canonical  %-  object
    :~  ['parent_operation' (scot %tas -.operation.cmd)]
        ['parent_request_id' request.cmd]  ['project_id' project.cmd]
        ['run_id' run.cmd]  ['attempt' (decimal attempt.cmd)]
        ['effect_id' effect.cmd]  ['run_contract_sha256' contract-digest]
        ['parent_canonical_sha256' digest.cmd]
    ==
  (id-from-seed:stead-model-material request.cmd seed)
--
