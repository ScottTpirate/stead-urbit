::  One initial external snapshot per project. A storage attestation only
::  stages a candidate. The Home supplies the currently authorized approver.
/+  stead-codec, stead-code-credentials, stead-session
=,  stead-codec
|%
+$  scope  scope:stead-code-credentials
+$  manifest
  $:  destination=scope  snapshot=@t  head=@t  refs=(map @t @t)
      pack-sha=@t  pack-bytes=@ud  objects=@ud  object-bytes=@ud  ids-sha=@t
  ==
+$  candidate  [pack=manifest operator=@p staged-at=@ud until=@ud]
+$  receipt  [request=@t approver=actor:stead-session accepted-at=@ud]
+$  entry  $%([%staged row=candidate ~] [%accepted row=candidate proof=receipt])
+$  state  (map @t entry)
+$  outcome  (each [next=state row=entry] @tas)
++  hex-text
  |=  [raw=@t width=@ud]
  ^-  ?
  &(=(width (met 3 raw)) (levy (rip 3 raw) |=(byte=@ ?|(&((gte byte 48) (lte byte 57)) &((gte byte 97) (lte byte 102))))))
++  ref
  |=  [name=@t branch=?]
  ^-  ?
  =/  width  (met 3 name)
  ?&  (lte width 2.048)  =(0 (mod width 2))
      (hex-text name width)
      ?|  &((gth width 22) =('726566732f68656164732f' (cut 3 [0 22] name)))
          &(!branch (gth width 20) =('726566732f746167732f' (cut 3 [0 20] name)))
      ==
  ==
++  snapshot-bytes
  |=  pack=manifest
  ^-  @t
  =/  scope-json
    %-  canonical  %-  object
    :~  ['authority_epoch' (decimal epoch.destination.pack)]
        ['home' (scot %p home.destination.pack)]
        ['project_id' project.destination.pack]
        ['repository_id' repository.destination.pack]
    ==
  ::  Same canonical bytes as scripts/urbit/git_pack_store.py, including LF.
  %-  rap  :-  3
  :~  '{"format":"stead.git-pack-snapshot/1","head":'  (quote head.pack)
      ',"object_bytes":'  (decimal object-bytes.pack)
      ',"object_count":'  (decimal objects.pack)
      ',"object_format":"sha1","object_ids_sha256":'  (quote ids-sha.pack)
      ',"pack_bytes":'  (decimal pack-bytes.pack)
      ',"pack_sha256":'  (quote pack-sha.pack)
      ',"refs":'  (canonical (object ~(tap by refs.pack)))
      ',"scope":'  scope-json  '}'  10
  ==
++  valid-manifest
  |=  pack=manifest
  ^-  ?
  ?&  (scope-valid:stead-code-credentials destination.pack)
      =(project.destination.pack repository.destination.pack)
      (token-valid:stead-session snapshot.pack)
      (token-valid:stead-session pack-sha.pack)
      (token-valid:stead-session ids-sha.pack)
      (gte pack-bytes.pack 32)  (lte pack-bytes.pack 67.108.864)
      (gth objects.pack 0)  (lte objects.pack 16.384)
      (gth object-bytes.pack 0)  (lte object-bytes.pack 268.435.456)
      (lte ~(wyt by refs.pack) 64)
      (ref head.pack &)
      (~(has by refs.pack) head.pack)
      %+  levy  ~(tap by refs.pack)
      |=  [name=@t oid=@t]
      &((ref name |) (hex-text oid 40) !=(oid '0000000000000000000000000000000000000000'))
      =/  raw  (snapshot-bytes pack)
      =/  size  (met 3 raw)
      =((hex 64 (sha-256l:sha [size (rev 3 size raw)])) snapshot.pack)
  ==
++  decode
  |=  raw=@t
  ^-  manifest
  ?>  (lte (met 3 raw) 65.536)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  %+  keys  obj
      ~['protocol' 'home' 'project_id' 'repository_id' 'authority_epoch' 'snapshot' 'head' 'refs' 'pack_sha256' 'pack_bytes' 'object_count' 'object_bytes' 'object_ids_sha256']
  ?>  =('stead.code-pack-attestation/1' (field obj 'protocol'))
  =/  home-text  (field obj 'home')
  =/  ship  (slav %p home-text)
  ?>  =(home-text (scot %p ship))
  =/  roots  (~(got by obj) 'refs')
  ?>  ?=([%o *] roots)
  ?>  (lte ~(wyt by p.roots) 64)
  =/  pack=manifest
    :*  [ship (field obj 'project_id') (field obj 'repository_id') (uint (field obj 'authority_epoch'))]
        (field obj 'snapshot')
        (field obj 'head')
        (malt (turn ~(tap by p.roots) |=([name=@t value=json] [name (field p.roots name)])))
        (field obj 'pack_sha256')
        (uint (field obj 'pack_bytes'))
        (uint (field obj 'object_count'))
        (uint (field obj 'object_bytes'))
        (field obj 'object_ids_sha256')
    ==
  ?>  (valid-manifest pack)
  pack
++  valid
  |=  value=entry
  ^-  ?
  =/  row  row.value
  ?&  (valid-manifest pack.row)
      =(operator.row home.destination.pack.row)
      (gth staged-at.row 0)  (lte until.row 18.446.744.073.709.551.615)
      =(until.row (add staged-at.row 900.000))
      ?:  ?=(%staged -.value)  &
      ?&  (uuid request.proof.value)
          (gte accepted-at.proof.value staged-at.row)
          (lth accepted-at.proof.value until.row)
          !=(ship.approver.proof.value operator.row)
          (live:stead-session approver.proof.value accepted-at.proof.value)
      ==
  ==
++  active
  |=  [value=entry now=@ud]
  ^-  ?
  |(?=(%accepted -.value) (gth until.row.value now))
++  prune
  |=  [db=state now=@ud]
  ^-  state
  (malt (skim ~(tap by db) |=([key=@t value=entry] (active value now))))
++  stage
  |=  [db=state pack=manifest operator=@p now=@ud]
  ^-  outcome
  =/  row=entry  [%staged [pack operator now (add now 900.000)] ~]
  ?.  (valid row)  [%| %pack-attestation-invalid]
  =/  project  project.destination.pack
  =/  prior  (~(get by db) project)
  ?:  ?=([~ %accepted *] prior)  [%| %pack-already-accepted]
  ?:  &(=(~ prior) (gte ~(wyt by db) 4))  [%| %capacity-exceeded]
  [%& (~(put by db) project row) row]
++  accept
  |=  $:  db=state  destination=scope  who=actor:stead-session  role=@ud  now=@ud
          expected=@t  request=@t  inline=?
      ==
  ^-  outcome
  ?.  &(=(3 role) (live:stead-session who now) !=(ship.who home.destination))
    [%| %denied-or-not-found]
  ?.  &((token-valid:stead-session expected) (uuid request))  [%| %invalid-request]
  ?:  inline  [%| %inline-repository-exists]
  =/  project  project.destination
  =/  found  (~(get by db) project)
  ?~  found  [%| %pack-unavailable]
  =/  row  row.u.found
  ?.  =(destination destination.pack.row)  [%| %authority-epoch-conflict]
  ?.  =(expected snapshot.pack.row)  [%| %pack-snapshot-conflict]
  ?:  ?=(%accepted -.u.found)
    ?:  &(=(request request.proof.u.found) (same-actor:stead-session approver.proof.u.found who))
      [%& db u.found]
    [%| %pack-already-accepted]
  ?.  &((gte now staged-at.row) (active u.found now))  [%| %pack-unavailable]
  =/  next=entry  [%accepted row [request who now]]
  [%& (~(put by db) project next) next]
--
