/+  stead-http, stead-session
=,  stead-http
=/  origin  'https://home.localhost:8443'
=/  token  (token:stead-session 1 1 'test')
=/  heads=(list [@t @t])
  ~[['Host' 'home.localhost:8443'] ['Origin' origin] ['Content-Type' 'application/json']]
=/  request=inbound-request:eyre
  [| & *address:eyre [%'POST' '/stead/api/query' heads `[2 '{}']]]
=/  get  request(method.request %'GET', url.request '/stead/', body.request ~)
|%
++  test-http-transport-flags-forwarding
  ^-  tang
  ?>  ?=(^ (validate request origin ~))
  ?>  ?=(~ (validate request(secure |) origin ~))
  ?>  ?=(~ (validate request(authenticated &, secure |) origin ~))
  ?>  (levy `(list @t)`~['Forwarded' 'forwarded' 'X-FoRwArDeD-Proto' 'X-Forwarded-Host' 'x-forwarded-for'] |=(name=@t ?=(~ (validate request(header-list.request [[name 'https'] heads]) origin ~))))
  ~
++  test-http-host-origin
  ^-  tang
  ?>  ?=(~ (validate request 'https://evil.test' ~))
  ?>  ?=(~ (validate request(header-list.request ~[['Host' 'home.localhost:8443'] ['Content-Type' 'application/json']]) origin ~))
  ?>  (levy `(list @t)`~['null' 'https://evil.test' 'http://home.localhost:8443' 'https://home.localhost:8443/'] |=(o=@t ?=(~ (validate request(header-list.request ~[['Host' 'home.localhost:8443'] ['Origin' o] ['Content-Type' 'application/json']]) origin ~))))
  ?>  ?=(^ (validate get(header-list.request ~[['Host' 'home.localhost:8443']]) origin ~))
  ~
++  test-http-route-method
  ^-  tang
  ?>  ?=(~ (validate request(method.request %'PUT') origin ~))
  ?>  (levy `(list @t)`~['/~/channel/123' '/~/scry/stead-home/state.json' '/stead/api/%71uery' '/stead/api/query?actor=alice' '/stead/../api/query'] |=(url=@t ?=(~ (validate request(url.request url) origin ~))))
  ?>  ?=(~ (validate request(url.request (fil 3 513 97)) origin ~))
  ?>  ?=(^ (validate get origin ~))
  ?>  ?=(~ (validate get(url.request '/stead/unknown.js') origin ~))
  ?>  ?=(^ (validate get(url.request '/stead/app.js') origin (silt ~['/stead/app.js'])))
  ~
++  test-http-header-count
  ^-  tang
  ?>  ?=(^ (headers (turn (gulf 0 31) |=(n=@ud [(scot %ud n) 'x']))))
  ?>  ?=(~ (headers (turn (gulf 0 32) |=(n=@ud [(scot %ud n) 'x']))))
  ~
++  test-http-header-bytes
  ^-  tang
  ?>  ?=(^ (headers ~[['x' (fil 3 8.191 97)]]))
  ?>  ?=(~ (headers ~[['x' (fil 3 8.192 97)]]))
  ?>  ?=(~ (headers ~[[(fil 3 8.193 97) '']]))
  ?>  ?=(~ (headers ~[['host' 'good\0abad']]))
  ~
++  test-http-header-ambiguity
  ^-  tang
  ?>  ?=(~ (headers ~[['Host' 'home.test'] ['host' 'evil.test']]))
  ?>  ?=(~ (headers ~[['Origin' origin] ['origin' origin]]))
  ?>  ?=(~ (headers ~[['Content-Type' 'application/json'] ['content-type' 'application/json']]))
  ?>  ?=(~ (headers ~[['X-Stead-CSRF' token] ['x-stead-csrf' token]]))
  ?>  ?=(~ (validate request(header-list.request [['Cookie' 'x=one'] [['cookie' 'x=two'] heads]]) origin ~))
  ~
++  test-http-cookie-transport-fields
  ^-  tang
  =/  member  (cat 3 '__Host-stead-pending=' token)
  =/  joined  request(header-list.request [['Cookie' (cat 3 'urbauth-~zod=0v123; ' member)] heads])
  =/  split  request(header-list.request [['Cookie' 'urbauth-~zod=0v123'] [['cOoKiE' member] heads]])
  =/  accepted  (validate split origin ~)
  ?>  ?=(^ accepted)
  ?>  =(token pending.u.accepted)
  ?>  =(accepted (validate joined origin ~))
  ?>  ?=(~ (validate request(header-list.request [['cookie' member] [['Cookie' member] heads]]) origin ~))
  ?>  ?=(~ (validate request(header-list.request [['cookie' member] [['Cookie' '__Host-stead-pending=bad'] heads]]) origin ~))
  ?>  ?=(~ (validate request(header-list.request [['cookie' 'x=one'] [['Cookie' 'x=two'] heads]]) origin ~))
  ?>  ?=(~ (validate request(header-list.request [['cookie' 'x=one;'] [['Cookie' member] heads]]) origin ~))
  ?>  ?=(~ (validate request(header-list.request [['cookie' 'x="bad"'] [['Cookie' member] heads]]) origin ~))
  ?>  ?=(~ (validate request(header-list.request [['cookie' ''] [['Cookie' member] heads]]) origin ~))
  ~
++  test-http-split-cookie-limits
  ^-  tang
  =/  make-field  |=(n=@ud ['Cookie' (rap 3 ~['x' (scot %ud n) '=one'])])
  ?>  ?=(^ (validate request(header-list.request (weld (turn (gulf 0 28) make-field) heads)) origin ~))
  ?>  ?=(~ (validate request(header-list.request (weld (turn (gulf 0 29) make-field) heads)) origin ~))
  =/  make-pair  |=(n=@ud (rap 3 ~[?:(=(n 0) '' '; ') 'x' (scot %ud n) '=one']))
  ?>  ?=(^ (cookies (rap 3 (turn (gulf 0 31) make-pair))))
  ?>  ?=(~ (cookies (rap 3 (turn (gulf 0 32) make-pair))))
  ?>  ?=(~ (headers ~[['Cookie' (fil 3 8.180 97)] ['Cookie' 'x=one']]))
  ~
++  test-http-cookie-grammar
  ^-  tang
  ?>  (levy `(list @t)`~['missing-equals' 'bad,name=x' 'x="unterminated' 'x=has space' 'x=one; x=two' 'x=one;' 'x=one\0abad'] |=(c=@t ?=(~ (cookies c))))
  ?>  ?=(^ (cookies 'x=YQ=='))
  ?>  ?=(^ (cookies 'x=one; y=two'))
  ?>  ?=(^ (cookies ''))
  ~
++  test-http-cookie-identity
  ^-  tang
  =/  credentials  [['Cookie' (cat 3 '__Host-stead-session=' token)] [['X-Stead-CSRF' token] heads]]
  =/  allowed  (validate request(header-list.request credentials) origin ~)
  ?>  ?=(^ allowed)
  ?>  &(=(token session.u.allowed) =(token csrf.u.allowed))
  ?>  ?=(~ (cookies (rap 3 ~['__Host-stead-session=' token '; __Host-stead-session=' token])))
  ?>  ?=(~ (validate get(header-list.request [['Cookie' '__Host-stead-session=bad'] heads]) origin ~))
  =/  wrong-case  (validate request(header-list.request [['Cookie' (cat 3 '__host-stead-session=' token)] heads]) origin ~)
  ?>  ?=(^ wrong-case)
  ?>  =('' session.u.wrong-case)
  ~
++  test-http-body-framing
  ^-  tang
  ?>  ?=(~ (validate request(body.request ~) origin ~))
  ?>  ?=(~ (validate request(body.request `[3 '{}']) origin ~))
  ?>  ?=(^ (validate request(body.request `[65.536 (fil 3 65.536 32)]) origin ~))
  ?>  ?=(~ (validate request(body.request `[65.537 (fil 3 65.537 32)]) origin ~))
  ?>  ?=(^ (validate get(body.request `[0 0]) origin ~))
  ?>  ?=(~ (validate get(body.request `[0 1]) origin ~))
  ~
++  test-http-token-format
  ^-  tang
  ?>  (token-valid:stead-session (fil 3 64 97))
  ?>  !(token-valid:stead-session (fil 3 63 97))
  ?>  !(token-valid:stead-session (fil 3 65 97))
  ?>  !(token-valid:stead-session (fil 3 64 65))
  ?>  ?=(~ (validate request(header-list.request [['X-Stead-CSRF' 'short'] heads]) origin ~))
  ~
++  test-http-response-headers
  ^-  tang
  =/  values  (malt security-headers)
  ?>  =('no-store' (field values 'cache-control'))
  ?>  =('nosniff' (field values 'x-content-type-options'))
  ?>  =('DENY' (field values 'x-frame-options'))
  ?>  =('no-referrer' (field values 'referrer-policy'))
  ?>  =('same-origin' (field values 'cross-origin-resource-policy'))
  ?>  =((crip "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'") (field values 'content-security-policy'))
  ?>  !(~(has by values) 'access-control-allow-origin')
  ~
++  test-http-cookie-output
  ^-  tang
  ?>  =((cat 3 (cat 3 '__Host-stead-session=' token) '; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=1800') (cookie | token |))
  ?>  =((cat 3 (cat 3 '__Host-stead-pending=' token) '; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=120') (cookie & token |))
  ?>  =('__Host-stead-session=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' (cookie | '' &))
  ?>  =('__Host-stead-pending=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0' (cookie & '' &))
  ~
--
