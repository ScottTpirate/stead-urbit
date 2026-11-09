::  Bounded durable quarantine. Authorization and live HTTP ownership are
::  checked by the configured Home. No bearer, response route or timer in save.
/+  stead-codec, stead-git, stead-session, stead-code-credentials
|%
+$  scope  scope:stead-code-credentials
+$  actor  actor:stead-session
+$  octets  octets:stead-git
+$  upload
  [%queued destination=scope owner=actor request=@t until=@ud wire=octets]
+$  jobs  (map @t upload)
+$  queued  [next=jobs key=@t]
++  valid-wire
  |=  wire=octets
  &((gth length.wire 0) (lte length.wire 65.536) (valid-octets:stead-git wire))
++  key
  |=  [destination=scope owner=actor wire=octets]
  ^-  @t
  ::  Include width and binding revision. An updated expiry alone does not
  ::  rename the same bytes for the same current individual.
  %-  hash:stead-codec
  :_  (bytes-hex:stead-codec (jam [destination ship.owner principal.owner binding.owner revision.owner wire]))
  'stead.git-upload/1'
++  trim
  |=  [rows=jobs now=@ud]
  ^-  jobs
  (malt (skim ~(tap by rows) |=([id=@t entry=upload] (gth until.entry now))))
++  stage
  |=  [rows=jobs destination=scope owner=actor wire=octets now=@ud request=@t]
  ^-  (each queued @tas)
  ?.  &((valid-wire wire) (scope-valid:stead-code-credentials destination) (live:stead-session owner now) (uuid:stead-codec request))
    [%| %invalid-upload]
  ?.  (lte ~(wyt by rows) 4)  [%| %upload-capacity]
  =/  active  (trim rows now)
  =/  id  (key destination owner wire)
  =/  found  (~(get by active) id)
  ?^  found
    ?.  &((same-actor:stead-session owner owner.u.found) =(wire wire.u.found) =(destination destination.u.found))
      [%| %upload-conflict]
    [%& active id]
  ?:  (gte ~(wyt by active) 4)  [%| %upload-capacity]
  =/  mine
    (skim ~(tap by active) |=([id=@t entry=upload] (same-actor:stead-session owner owner.entry)))
  ?:  (gte (lent mine) 2)  [%| %upload-capacity]
  =/  deadline  (min expires.owner (add now 300.000))
  [%& (~(put by active) id [%queued destination owner request deadline wire]) id]
++  valid
  |=  rows=jobs
  ^-  ?
  ?.  (lte ~(wyt by rows) 4)  |
  %+  levy  ~(tap by rows)
  |=  [id=@t entry=upload]
  ?&  (scope-valid:stead-code-credentials destination.entry)
      (live:stead-session owner.entry 0)
      (uuid:stead-codec request.entry)
      (gth until.entry 0)
      (lte until.entry expires.owner.entry)
      (valid-wire wire.entry)
      =(id (key destination.entry owner.entry wire.entry))
  ==
--
