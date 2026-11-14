::  Decode the narrow owner-local policy command for the installed relay.
/+  stead-codec, stead-code-pack-relay-pin
=,  stead-codec
|%
++  decode
  |=  [raw=@t home=@p]
  ^-  command:stead-code-pack-relay-pin
  ?>  (lte (met 3 raw) 2.048)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  fields  p.value
  ?>  =('stead.git-pack-relay-policy/1' (field fields 'protocol'))
  =/  expected  (uint (field fields 'expected_generation'))
  =/  base  ~['protocol' 'expected_generation' 'operation']
  =/  action  (field fields 'operation')
  ?:  =('close' action)
    ?>  (keys fields base)
    [%close expected ~]
  ?>  =('open' action)
  ?>  (keys fields ['project' 'authority_epoch' 'incarnation' 'worker_generation' 'worker_public_key' 'relay_capability_sha256' base])
  =/  project  (field fields 'project')
  =/  epoch  (uint (field fields 'authority_epoch'))
  =/  incarnation  (field fields 'incarnation')
  =/  gen  (uint (field fields 'worker_generation'))
  =/  desired=policy:stead-code-pack-relay-pin
    [[home project project epoch] incarnation [gen (field fields 'worker_public_key')] (field fields 'relay_capability_sha256')]
  [%open expected desired]
--
