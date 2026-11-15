::  Reserved query/4 decoder. Sharing an internal query mold does not admit
::  command/3 or query/3 bytes on the future versioned carrier.
/+  stead-codec, stead-team-codec
=,  stead-codec
|%
++  decode
  |=  raw=@t
  ^-  query:stead-team-codec
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['protocol' 'request_id' 'kind' 'project_id' 'container_id' 'resource_id' 'search' 'cursor'])
  ?>  =('stead.query/4' (field obj 'protocol'))
  =/  request  (field obj 'request_id')
  =/  kind  (field obj 'kind')
  =/  project  (field obj 'project_id')
  =/  resource  (field obj 'resource_id')
  =/  cursor  (field obj 'cursor')
  ?>  &((uuid request) (uuid project) =('' (field obj 'container_id')) =('' (field obj 'search')))
  ?>  ?|  &(=('work' kind) ?|(=('' resource) (uuid resource)))
          &(=('comments' kind) (uuid resource))
      ==
  ?>  ?|(=('' cursor) (opaque:stead-team-codec cursor))
  [request kind project '' resource '' cursor]
++  bytes
  |=  query=query:stead-team-codec
  ^-  @t
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.query/4']  ['request_id' request.query]
      ['kind' kind.query]  ['project_id' project.query]
      ['container_id' container.query]  ['resource_id' resource.query]
      ['search' search.query]  ['cursor' cursor.query]
  ==
--
