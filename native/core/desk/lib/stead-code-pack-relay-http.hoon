::  Fixed TLS request for the internal relay. Eyre source is checked by Home.
::  The trusted ingress must keep this path private and strip private headers.
/+  stead-codec, stead-http, stead-code-http, stead-session
|%
+$  input  [project=@t capability=@t bearer=@t raw=@t]
++  prefix  '/stead/_pack-relay/'
++  route
  |=  url=@t
  =(prefix (cut 3 [0 (met 3 prefix)] url))
++  validate
  |=  [inbound=inbound-request:eyre origin=@t]
  ^-  (unit input)
  =/  req  request.inbound
  =/  size  (met 3 prefix)
  ?.  ?&  secure.inbound
          (origin-valid:stead-session origin)
          =(%'POST' method.req)
          =((add size 36) (met 3 url.req))
          (route url.req)
      ==
    ~
  =/  project  (rsh [3 size] url.req)
  ?.  (uuid:stead-codec project)  ~
  =/  headers  (headers:stead-http header-list.req)
  ?~  headers  ~
  =/  field  |=(name=@t (field:stead-http u.headers name))
  =/  forbidden=(list @t)  ~['cookie' 'origin' 'x-stead-csrf' 'content-encoding' 'transfer-encoding']
  ?.  ?&  =((rsh [3 8] origin) (field 'host'))
          =('application/x-stead-git-relay' (field 'content-type'))
          !(lien forbidden |=(name=@t (~(has by u.headers) name)))
      ==
    ~
  =/  capability  (field 'x-stead-relay')
  =/  bearer  (basic:stead-code-http (field 'authorization'))
  ?.  &((token-valid:stead-session capability) (token-valid:stead-session bearer))  ~
  ?~  body.req  ~
  ?.  &((lte p.u.body.req 196.608) =(p.u.body.req (met 3 q.u.body.req)))  ~
  [~ project capability bearer q.u.body.req]
--
