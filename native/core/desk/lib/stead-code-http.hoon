::  Separate Smart HTTP boundary. Explicit byte widths preserve binary packs.
/+  stead-http, stead-codec, stead-session, stead-code-service, stead-git
|%
+$  operation
  $%  [%advertise kind=service:stead-code-service]
      [%fetch ~]
      [%receive ~]
  ==
+$  incoming  [project=@t operation=operation bearer=@t body=octets:stead-git]
++  git-path
  |=  url=@t
  =('/stead/git/' (cut 3 [0 11] url))
++  endpoint
  |=  [suffix=@t method=@tas mime=@t]
  ^-  (unit operation)
  ?:  =(%'GET' method)
    ?:  =('/info/refs?service=git-upload-pack' suffix)  [~ %advertise %git-upload-pack]
    ?:  =('/info/refs?service=git-receive-pack' suffix)  [~ %advertise %git-receive-pack]
    ~
  ?.  =(%'POST' method)  ~
  ?:  &(=(suffix '/git-upload-pack') =(mime 'application/x-git-upload-pack-request'))
    [~ %fetch ~]
  ?:  &(=(suffix '/git-receive-pack') =(mime 'application/x-git-receive-pack-request'))
    [~ %receive ~]
  ~
++  basic
  |=  header=@t
  ^-  @t
  ::  Exact canonical RFC 4648 encoding of "stead:" and a 64-digit bearer.
  ?.  &(=(102 (met 3 header)) =('Basic ' (cut 3 [0 6] header)))  ''
  =/  encoded  (cut 3 [6 96] header)
  =/  decoded  (de:base64:mimes:html encoded)
  ?~  decoded  ''
  ?.  &(=(70 p.u.decoded) =('stead:' (cut 3 [0 6] q.u.decoded)) =(encoded (en:base64:mimes:html u.decoded)))
    ''
  =/  bearer  (cut 3 [6 64] q.u.decoded)
  ?:((token-valid:stead-session bearer) bearer '')
++  validate
  |=  [request=inbound-request:eyre origin=@t]
  ^-  (unit incoming)
  =/  req  request.request
  ?.  &(secure.request (origin-valid:stead-session origin) (lte (met 3 url.req) 96) (git-path url.req))
    ~
  =/  project  (cut 3 [11 36] url.req)
  ?.  &((uuid:stead-codec project) =('.git' (cut 3 [47 4] url.req)))  ~
  =/  headers  (headers:stead-http header-list.req)
  ?~  headers  ~
  =/  field  |=(key=@t (field:stead-http u.headers key))
  =/  host  (cut 3 [8 (sub (met 3 origin) 8)] origin)
  ?.  &(=(host (field 'host')) =('' (field 'cookie')) =('' (field 'x-stead-csrf')))  ~
  ?.  |(=('' (field 'origin')) =(origin (field 'origin')))  ~
  =/  suffix  (rsh [3 51] url.req)
  =/  op  (endpoint suffix method.req (field 'content-type'))
  ?~  op  ~
  =/  bearer  (basic (field 'authorization'))
  ?:  ?=(%advertise -.u.op)
    ?.  ?~(body.req & =([0 0] u.body.req))  ~
    [~ project u.op bearer [0 0]]
  ?~  body.req  ~
  ?.  &((gth p.u.body.req 0) (lte p.u.body.req 65.536) (lte (met 3 q.u.body.req) p.u.body.req))  ~
  [~ project u.op bearer u.body.req]
--
