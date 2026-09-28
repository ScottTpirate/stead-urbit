::  Public bounded subscription protocol; no home-state dependency.
/+  stead-codec, stead-team-codec
=,  stead-codec
|%
+$  envelope
  [request=@t action=@t watch=@t cursor=@t query=query:stead-team-codec]
++  decode
  |=  raw=@t
  ^-  envelope
  ?>  (lte (met 3 raw) 2.048)
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['protocol' 'request_id' 'action' 'watch_id' 'cursor' 'kind' 'project_id' 'resource_id' 'container_id' 'search'])
  ?>  =('stead.updates/3' (field obj 'protocol'))
  =/  request  (field obj 'request_id')
  =/  action  (field obj 'action')
  =/  watch  (field obj 'watch_id')
  =/  cursor  (field obj 'cursor')
  ?>  (uuid request)
  ?>  (~(has in (silt ~['open' 'poll' 'cancel' 'resume'])) action)
  =/  query=query:stead-team-codec
    [request (field obj 'kind') (field obj 'project_id') (field obj 'container_id') (field obj 'resource_id') (field obj 'search') '']
  ?:  ?|(=('poll' action) =('cancel' action))
    ?>  (opaque:stead-team-codec watch)
    ?>  ?:(=('poll' action) (opaque:stead-team-codec cursor) =('' cursor))
    ?>  =(query [request '' '' '' '' '' ''])
    [request action watch cursor query]
  ?>  =('' watch)
  ?>  ?:(=('resume' action) (opaque:stead-team-codec cursor) =('' cursor))
  ?>  &(!=('identity' kind.query) !=('capabilities' kind.query) !=('receipt' kind.query))
  =/  encoded
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.query/3']  ['request_id' request]
        ['kind' kind.query]  ['project_id' project.query]
        ['container_id' container.query]  ['resource_id' resource.query]
        ['search' search.query]  ['cursor' '']
    ==
  ?>  =(query (decode-query:stead-team-codec encoded))
  [request action watch cursor query]
--
