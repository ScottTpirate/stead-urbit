::  Repository credentials issued and checked by the authoritative Home.
::  The caller resolves authenticated and current member actors itself.
::  Bearers are returned once; state retains only domain-separated hashes.
/+  stead-codec, stead-session
|%
+$  actor  actor:stead-session
+$  scope  [home=@p project=@t repository=@t epoch=@ud]
+$  access  ?(%read %write)
+$  allowance  $-([actor scope access] ?)
+$  membership  $-(@p (unit actor))
+$  credential
  [handle=@t owner=actor destination=scope writable=? expires=@ud]
+$  ledger  [serial=@ud credentials=(map @t credential)]
+$  issue-result
  (each [next=ledger handle=@t bearer=@t expires=@ud] @tas)
+$  revoke-result  (each ledger @tas)
::
++  scope-valid
  |=  destination=scope
  ^-  ?
  ?&  (lte (met 0 home.destination) 128)
      (uuid:stead-codec project.destination)
      (uuid:stead-codec repository.destination)
      (gth epoch.destination 0)
      (lte epoch.destination 18.446.744.073.709.551.615)
  ==
::
++  issue
  |=  $:  book=ledger  owner=actor  destination=scope  writable=?
          session-until=@ud  now=@ud  entropy=@  allows=allowance
      ==
  ^-  issue-result
  ?.  &((scope-valid destination) (live:stead-session owner now) !=(ship.owner home.destination))
    [%| %denied]
  ?.  &((allows owner destination %read) ?:(writable (allows owner destination %write) &))
    [%| %denied]
  =/  expires=@ud  (min expires.owner (min session-until (add now 900.000)))
  ?:  (lte expires now)  [%| %denied]
  ?:  |(=(0 entropy) (gte serial.book 18.446.744.073.709.551.615) (gth ~(wyt by credentials.book) 64))
    [%| %capacity]
  =/  remaining=(list [key=@t row=credential])
    (skim ~(tap by credentials.book) |=([key=@t row=credential] (gth expires.row now)))
  ?:  (gte (lent remaining) 64)  [%| %capacity]
  =/  serial=@ud  +(serial.book)
  =/  bearer=@t  (token:stead-session entropy serial 'stead.git-bearer/1')
  =/  key=@t  (digest:stead-session 'stead.git-credential/1' bearer)
  =/  handle=@t  (token:stead-session entropy serial 'stead.git-handle/1')
  =/  rows=(map @t credential)  (malt remaining)
  ?:  |((~(has by rows) key) (lien remaining |=([key=@t row=credential] =(handle.row handle))))
    [%| %capacity]
  [%& [serial (~(put by rows) key [handle owner destination writable expires])] handle bearer expires]
::
++  check
  |=  $:  book=ledger  bearer=@t  destination=scope  operation=access
          now=@ud  resolve=membership  allows=allowance
      ==
  ^-  (unit actor)
  ?.  &((scope-valid destination) (token-valid:stead-session bearer) (lte ~(wyt by credentials.book) 64))
    ~
  =/  key=@t  (digest:stead-session 'stead.git-credential/1' bearer)
  =/  found  (~(get by credentials.book) key)
  ?~  found  ~
  =/  row  u.found
  ?.  &((gth expires.row now) =(destination destination.row) ?:(=(%write operation) writable.row &))
    ~
  =/  active  (resolve ship.owner.row)
  ?~  active  ~
  ?.  &((live:stead-session u.active now) (same-actor:stead-session owner.row u.active))
    ~
  ?.  (allows u.active destination operation)  ~
  active
::
++  revoke
  |=  [book=ledger handle=@t owner=actor home=@p now=@ud]
  ^-  revoke-result
  ?.  &((live:stead-session owner now) (token-valid:stead-session handle) (lte ~(wyt by credentials.book) 64))
    [%| %denied]
  =/  matches=(list [key=@t row=credential])
    (skim ~(tap by credentials.book) |=([key=@t row=credential] =(handle.row handle)))
  ?.  ?=([* ~] matches)  [%| %denied]
  ?.  &((same-actor:stead-session owner.row.i.matches owner) =(home home.destination.row.i.matches))
    [%| %denied]
  [%& book(credentials (~(del by credentials.book) key.i.matches))]
--
