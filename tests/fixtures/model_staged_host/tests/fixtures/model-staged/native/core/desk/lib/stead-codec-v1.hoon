::  Stead command/1 codec. Newly authored bounded composition of pinned parsers.
::  String parser follows MIT Urbit zuse +stri, preserving/rejecting NUL first.
|%
+$  object-map  (map @t json)
+$  command
  $:  request=@t  project=@t  resource=@t  expected=@ud  epoch=@ud
      operation=@t  payload=object-map  canonical-bytes=@t  digest=@t
  ==
++  string-rule
  %+  sear
    |=  chunks=(list @t)
    ^-  (unit @t)
    ?:  (lien chunks |=(part=@t =(0 part)))  ~
    =/  text  (crip chunks)
    ?.  (sune:de:json:html text)  ~
    (some text)
  (ifix [doq doq] (star jcha:de:json:html))
++  unique-map
  |=  pairs=(list [key=@t value=json])
  ^-  (unit object-map)
  (unique-map-limit 16 pairs)
++  unique-map-limit
  |=  [limit=@ud pairs=(list [key=@t value=json])]
  ^-  (unit object-map)
  ?:  (gth (lent pairs) limit)  ~
  =/  result=object-map  *object-map
  |-
  ?~  pairs  (some result)
  ?:  (~(has by result) key.i.pairs)  ~
  $(pairs t.pairs, result (~(put by result) key.i.pairs value.i.pairs))
++  dict-rule
  |*  value-rule=rule
  %+  sear  unique-map
  %+  ifix  [(wish:de:json:html kel) (wish:de:json:html ker)]
  %+  more  (wish:de:json:html com)
  ;~  plug
    ;~(sfix (wish:de:json:html string-rule) (wish:de:json:html col))
    (wish:de:json:html value-rule)
  ==
++  result-dict
  |*  value-rule=rule
  %+  sear  |=(pairs=(list [@t json]) (unique-map-limit 512 pairs))
  %+  ifix  [(wish:de:json:html kel) (wish:de:json:html ker)]
  %+  more  (wish:de:json:html com)
  ;~  plug
    ;~(sfix (wish:de:json:html string-rule) (wish:de:json:html col))
    (wish:de:json:html value-rule)
  ==
++  parse-result
  |=  raw=@t
  ^-  (unit json)
  ?:  (gth (met 3 raw) 262.144)  ~
  %+  rush  raw
  %+  ifix  [spac:de:json:html spac:de:json:html]
  %+  stag  %o
  %-  result-dict
  ;~  pose
    (stag %s string-rule)
    (stag %o (result-dict ;~(pose (stag %s string-rule) (stag %o (result-dict (stag %s string-rule))))))
  ==
++  parse
  |=  raw=@t
  ^-  (unit json)
  ?:  (gth (met 3 raw) 65.536)  ~
  %+  rush  raw
  %+  ifix  [spac:de:json:html spac:de:json:html]
  %+  stag  %o
  %-  dict-rule
  ;~  pose
    (stag %s string-rule)
    (stag %o (dict-rule (stag %s string-rule)))
  ==
++  quote
  |=  text=@t
  ^-  @t
  =/  parts=(list @t)
    %+  turn  (rip 3 text)
    |=  byte=@
    ^-  @t
    ?:  ?|(=(34 byte) =(92 byte))  (cat 3 92 byte)
    ?:  =(8 byte)   (cat 3 92 'b')
    ?:  =(9 byte)   (cat 3 92 't')
    ?:  =(10 byte)  (cat 3 92 'n')
    ?:  =(12 byte)  (cat 3 92 'f')
    ?:  =(13 byte)  (cat 3 92 'r')
    ?:  (lth byte 32)
      =/  hex  '0123456789abcdef'
      =/  tail  (cat 3 (cut 3 [(div byte 16) 1] hex) (cut 3 [(mod byte 16) 1] hex))
      (cat 3 0x3030.755c tail)
    byte
  (rap 3 (weld ['"' ~] (weld parts ['"' ~])))
++  canonical
  |=  value=json
  ^-  @t
  ?~  value  !!
  ?+  -.value  !!
    %s  (quote p.value)
    %o
      =/  pairs
        %+  sort  ~(tap by p.value)
        |=  [a=[@t json] b=[@t json]]
        (aor -.a -.b)
      =/  parts=(list @t)
        %+  turn  pairs
        |=  pair=[key=@t data=json]
        (cat 3 (quote key.pair) (cat 3 ':' (canonical data.pair)))
      =/  inner=@t
        ?~  parts  ''
        =/  out=@t  i.parts
        |-  ^-  @t
        ?~  t.parts  out
        $(parts t.parts, out (cat 3 out (cat 3 ',' i.t.parts)))
      (cat 3 '{' (cat 3 inner '}'))
  ==
++  decimal
  |=  number=@ud
  ^-  @t
  (crip (skip (trip (scot %ud number)) |=(c=@t =(c '.'))))
++  field
  |=  [object=object-map key=@t]
  ^-  @t
  =/  found  (~(got by object) key)
  ?>  ?=(%s -.found)
  p.found
++  uint
  |=  text=@t
  ^-  @ud
  =/  bytes  (rip 3 text)
  ?>  ?=(^ bytes)
  ?>  (lte (lent bytes) 20)
  ?>  ?|(!=(48 i.bytes) =(1 (lent bytes)))
  (uint-fold bytes 0)
++  uint-fold
  |=  [bytes=(list @) number=@ud]
  ^-  @ud
  |-
  ?~  bytes
    ?>  (lte number 18.446.744.073.709.551.615)
    number
  ?>  &((gte i.bytes 48) (lte i.bytes 57))
  $(bytes t.bytes, number (add (mul number 10) (sub i.bytes 48)))
++  uuid
  |=  id=@t
  ^-  ?
  ?.  =(36 (met 3 id))  |
  =/  index=@ud  0
  |-
  ?:  =(36 index)  &
  =/  byte  (cut 3 [index 1] id)
  ?:  ?|(=(index 8) =(index 13) =(index 18) =(index 23))
    ?&  =(byte '-')
        $(index +(index))
    ==
  ?.  ?|(&((gte byte 48) (lte byte 57)) &((gte byte 97) (lte byte 102)))  |
  ?.  ?|(=(index 14) =(index 19))  $(index +(index))
  ?:  =(index 14)
    &(=(byte '7') $(index +(index)))
  &(?|(=(byte '8') =(byte '9') =(byte 'a') =(byte 'b')) $(index +(index)))
++  keys
  |=  [object=object-map names=(list @t)]
  ^-  ?
  ?&  =((lent names) (lent ~(tap by object)))
      (levy names |=(key=@t (~(has by object) key)))
  ==
++  title
  |=  text=@t
  ^-  ?
  =/  bytes  (rip 3 text)
  ?&  (gte (met 3 text) 1)
      (lte (met 3 text) 800)
      (levy bytes |=(c=@ (gte c 32)))
      (lte (lent (skim bytes |=(c=@ ?|((lth c 128) (gte c 192))))) 200)
  ==
++  prose
  |=  [text=@t bound=@ud]
  ^-  ?
  &((lte (met 3 text) bound) !(lien (rip 3 text) |=(c=@ ?|(=(c 0) =(c 13)))))
++  project-key
  |=  text=@t
  ^-  ?
  ?&  (gte (met 3 text) 2)
      (lte (met 3 text) 10)
      (gte (cut 3 [0 1] text) 65)
      (lte (cut 3 [0 1] text) 90)
      (levy (rip 3 text) |=(c=@ ?|(&((gte c 65) (lte c 90)) &((gte c 48) (lte c 57)))))
  ==
++  hex
  |=  [width=@ud value=@]
  ^-  @t
  ?>  (lte (met 2 value) width)
  =/  out=@t  ''
  =/  index=@ud  width
  |-
  ?:  =(0 index)  out
  =/  digit  (cut 2 [(dec index) 1] value)
  $(index (dec index), out (cat 3 out (cut 3 [digit 1] '0123456789abcdef')))
++  hash
  |=  [domain=@t bytes=@t]
  ^-  @t
  ::  Explicit shift reserves the zero domain byte, even for an empty body.
  =/  prefix  +((met 3 domain))
  =/  size  (add prefix (met 3 bytes))
  =/  data  (mix domain (lsh [3 prefix] bytes))
  (hex 64 (sha-256l:sha [size (rev 3 size data)]))
++  bytes-hex
  |=  text=@t
  ^-  @t
  (hex (mul 2 (met 3 text)) (rev 3 (met 3 text) text))
++  object
  |=  pairs=(list [@t @t])
  ^-  json
  [%o (malt (turn pairs |=([key=@t text=@t] [key [%s text]])))]
++  decode
  |=  raw=@t
  ^-  command
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['protocol' 'request_id' 'project_id' 'resource_id' 'expected_revision' 'authority_epoch' 'operation' 'payload'])
  ?>  =('stead.command/1' (field obj 'protocol'))
  =/  req  (field obj 'request_id')
  =/  pro  (field obj 'project_id')
  =/  res  (field obj 'resource_id')
  ?>  &((uuid req) (uuid pro) (uuid res))
  =/  exp  (uint (field obj 'expected_revision'))
  =/  epo  (uint (field obj 'authority_epoch'))
  ?>  (gth epo 0)
  =/  op  (field obj 'operation')
  =/  data  (~(got by obj) 'payload')
  ?>  ?=([%o *] data)
  =/  pay  p.data
  ?>
    ?:  =('project.create' op)
        ?&  =(exp 0)  =(pro res)
            (keys pay ~['organization_id' 'owning_team_id' 'title' 'project_key' 'preset'])
            (uuid (field pay 'organization_id'))
            (uuid (field pay 'owning_team_id'))
            (title (field pay 'title'))
            (project-key (field pay 'project_key'))
            (~(has in (silt ~['general' 'software' 'controlled_knowledge'])) (field pay 'preset'))
        ==
    ?:  =('work.create' op)  &(=(exp 0) (work-payload pay))
    ?:  =('work.update' op)  &((gth exp 0) (work-payload pay))
    ?:  =('document.save' op)
        ?&  (keys pay ~['container_id' 'markdown'])
            (uuid (field pay 'container_id'))
            (prose (field pay 'markdown') 32.768)
        ==
    ?:  =('policy.grant' op)
        ?&  (gth exp 0)  =(pro res)
            (keys pay ~['grant_id' 'principal_id' 'role' 'expires_at_ms'])
            (uuid (field pay 'grant_id'))
            (uuid (field pay 'principal_id'))
            (~(has in (silt ~['reader' 'contributor' 'maintainer'])) (field pay 'role'))
            (gth (uint (field pay 'expires_at_ms')) 0)
        ==
    ?:  =('policy.revoke' op)
        ?&  (gth exp 0)  =(pro res)
            (keys pay ~['grant_id'])
            (uuid (field pay 'grant_id'))
        ==
    |
  =/  canon  (canonical value)
  [req pro res exp epo op pay canon (hash 'stead.command/1' canon)]
++  work-payload
  |=  pay=object-map
  ^-  ?
  ?&  (keys pay ~['title' 'description' 'type' 'status' 'priority'])
      (title (field pay 'title'))
      (prose (field pay 'description') 8.192)
      (~(has in (silt ~['deliverable' 'task' 'problem'])) (field pay 'type'))
      (~(has in (silt ~['backlog' 'todo' 'in_progress' 'blocked' 'done' 'canceled'])) (field pay 'status'))
      (~(has in (silt ~['none' 'low' 'medium' 'high' 'urgent'])) (field pay 'priority'))
  ==
--
