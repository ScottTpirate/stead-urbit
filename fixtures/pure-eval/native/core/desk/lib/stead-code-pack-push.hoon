::  Pure ref decision for complete immutable external packs. The Home supplies
::  current policy and authenticated worker evidence. No state is saved here.
/+  stead-codec, stead-code-credentials, stead-code-pack-anchor, stead-code-receive, stead-session, stead-code-git-graph, stead-code-git-objects, stead-git
|%
+$  scope  scope:stead-code-credentials
+$  manifest  manifest:stead-code-pack-anchor
+$  update  update:stead-code-receive
::  Scope, generations, and wire digest must already belong to one admitted
::  job. Kinds and ancestry are worker-verified facts about this exact pack.
+$  evidence
  $:  destination=scope  base=@t  generation=@ud  wire=@t  request=@t
      changes=(list update)  pack=manifest
      kinds=(map @ux object-kind:stead-code-git-graph)
      lineage=(set [@ux @ux])
  ==
+$  candidate
  [destination=scope base=@t generation=@ud wire=@t request=@t changes=(list update) pack=manifest]
+$  receipt
  [version=@ud decision=candidate owner=actor:stead-session accepted-at=@ud]
+$  outcome
  $%([%candidate next=candidate] [%rejected reason=@tas])
++  raw-ref
  |=  key=@t
  ^-  @t
  ::  Called only with lowercase hex validated by the manifest gate.
  =/  width  (met 3 key)
  =/  index=@ud  0
  =/  value=@t  ''
  |-  ^-  @t
  ?:  =(index width)  value
  =/  byte  (cut 3 [index 1] key)
  =/  digit  ?:((lte byte 57) (sub byte 48) (sub byte 87))
  $(index +(index), value (add (mul value 16) digit))
++  encode-refs
  |=  refs=refs:stead-code-receive
  ^-  (map @t @t)
  %-  malt
  %+  turn  ~(tap by refs)
  |=  [name=@t oid=@ux]
  [(bytes-hex:stead-codec name) (oid-text:stead-git oid)]
++  decide
  |=  $:  destination=scope  generation=@ud  current=manifest
          checked=evidence  protected=(set @t)
          authorize=$-([action:stead-code-receive update] ?)
      ==
  ^-  outcome
  ?.  ?&  =(destination destination.current)
          =(destination destination.checked)
          =(destination destination.pack.checked)
      ==
    [%rejected %scope-conflict]
  ?.  &((lth generation 18.446.744.073.709.551.615) =(generation generation.checked))
    [%rejected %generation-conflict]
  ?.  =(base.checked snapshot.current)  [%rejected %snapshot-conflict]
  ?.  ?&  (token-valid:stead-session wire.checked)
          (token-valid:stead-session base.checked)
          (uuid:stead-codec request.checked)
          (lte (lent (scag 33 changes.checked)) 32)
          (lte ~(wyt by kinds.checked) 32)
          (lte ~(wyt in lineage.checked) 32)
          (lte ~(wyt in protected) 16)
          (levy changes.checked |=(change=update (lte (met 3 name.change) 1.024)))
      ==
    [%rejected %invalid-candidate]
  ?.  ?&  (valid-manifest:stead-code-pack-anchor current)
          (valid-manifest:stead-code-pack-anchor pack.checked)
          =(head.current head.pack.checked)
      ==
    [%rejected %manifest-conflict]
  =/  changes  changes.checked
  ?:  (lien changes |=(change=update =(0 target.change)))  [%rejected %delete-unsupported]
  ?:  (lien changes |=(change=update (~(has in protected) name.change)))  [%rejected %protected-ref]
  ::  The stock manifest spells ref names as byte-preserving hex. Pass every
  ::  old ref to the shared CAS gate, including unchanged refs and prefixes.
  =/  prior=refs:stead-code-receive
    %-  malt
    %+  turn  ~(tap by refs.current)
    |=  [key=@t value=@t]
    =/  size  (div (met 3 key) 2)
    [`@t`(rev 3 size (raw-ref key)) (need (parse-oid:stead-code-git-objects [40 value]))]
  ?.  ?&  =(refs.current (encode-refs prior))
          %+  levy  ~(tap by prior)
          |=  [name=@t oid=@ux]
          (valid-ref:stead-code-git-objects [(met 3 name) name])
      ==
    [%rejected %manifest-conflict]
  =/  kind=$-(@ux (unit @tas))
    |=  oid=@ux
    =/  found  (~(get by kinds.checked) oid)
    ?~  found  ~
    [~ u.found]
  =/  descends=$-([@ux @ux] ?)
    |=  [old=@ux new=@ux]
    (~(has in lineage.checked) [old new])
  =/  result
    (decide:stead-code-receive prior epoch.destination epoch.destination.checked changes protected authorize kind descends)
  ?:  ?=(%| -.result)  [%rejected p.result]
  ?.  =((encode-refs p.result) refs.pack.checked)  [%rejected %manifest-conflict]
  [%candidate destination snapshot.current +(generation) wire.checked request.checked changes pack.checked]
--
