::  Reserved closed owner commands. Actual Home sender never comes from wire.
/+  stead-codec, stead-team-codec
=,  stead-codec
|%
+$  command
  [request=@t operation=@t expected=@ud payload=object-map canonical-bytes=@t digest=@t]
++  payload-valid
  |=  [operation=@t expected=@ud payload=object-map]
  ^-  ?
  ?:  =('home.configure' operation)
    ?.  (keys payload ~['configuration'])  |
    =/  raw  (field payload 'configuration')
    ?.  (lte (met 3 raw) 65.536)  |
    =/  parsed  (need (parse-result raw))
    ?>  ?=([%o *] parsed)
    ?&  =(raw (canonical parsed))
        (keys p.parsed ~['protocol' 'expected_revision' 'home' 'origin' 'organization_id' 'team_id' 'custody' 'runtime' 'bindings' 'project_creators'])
        =('stead.team-config/1' (field p.parsed 'protocol'))
        =(expected (uint (field p.parsed 'expected_revision')))
    ==
  ?:  =('principal.declare' operation)
    ?&  (keys payload ~['principal_id' 'kind' 'display_name' 'active'])
        (uuid (field payload 'principal_id'))  (title (field payload 'display_name'))
        (~(has in (silt ~['person' 'agent' 'service'])) (field payload 'kind'))
        (~(has in (silt ~['yes' 'no'])) (field payload 'active'))
    ==
  ?:  =('runtime.put' operation)
    ?&  (keys payload ~['runtime_id' 'principal_id' 'profile' 'policy_digest'])
        (uuid (field payload 'runtime_id'))  (uuid (field payload 'principal_id'))
        (title (field payload 'profile'))  (opaque:stead-team-codec (field payload 'policy_digest'))
    ==
  ?.  =('definition.put' operation)  |
  ?&  (keys payload ~['definition_id' 'principal_id' 'instructions_digest' 'runtime_id' 'runtime_revision'])
      (uuid (field payload 'definition_id'))  (uuid (field payload 'principal_id'))
      (opaque:stead-team-codec (field payload 'instructions_digest'))
      (uuid (field payload 'runtime_id'))  (gth (uint (field payload 'runtime_revision')) 0)
  ==
++  decode
  |=  raw=@t
  ^-  command
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  data  p.value
  ?>  (keys data ~['protocol' 'request_id' 'operation' 'expected_revision' 'payload'])
  ?>  =('stead.owner-command/1' (field data 'protocol'))
  =/  request  (field data 'request_id')
  ?>  (uuid request)
  =/  operation  (field data 'operation')
  =/  expected  (uint (field data 'expected_revision'))
  =/  payload  (~(got by data) 'payload')
  ?>  ?=([%o *] payload)
  ?>  (payload-valid operation expected p.payload)
  =/  bytes  (canonical value)
  [request operation expected p.payload bytes (hash 'stead.owner-command/1' bytes)]
--
