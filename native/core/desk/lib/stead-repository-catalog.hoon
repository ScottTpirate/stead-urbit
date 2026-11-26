::  PRIVATE create-only repository catalog. No Home carrier/save/wire uses it.
::  Four retained roots per Home, including imports/tombstones. The current
::  callback is trusted composition, never a caller-supplied permission flag.
/+  stead-codec, stead-session, stead-code-credentials, stead-code-store
=,  stead-codec
|%
+$  profile  ?(%inline-sha1-v1 %external-sha1-pack-v1)
+$  ref  [project=@t repository=@t]
+$  origin  $%([%legacy] [%created request=@t principal=@t])
+$  entry
  $:  project=@t  name=@t  metadata-revision=@ud  profile=profile
      lifecycle=?(%active %tombstone)  legacy-alias=?  origin=origin
  ==
+$  command
  $:  request=@t  project=@t  repository=@t  expected=@ud  epoch=@ud
      name=@t  canonical-bytes=@t  digest=@t
  ==
+$  receipt
  $:  version=@ud  request=@t  project=@t  repository=@t  principal=@t
      actor=actor:stead-session  authority-epoch=@ud  expected-revision=@ud
      revision=@ud  accepted-at=@ud  digest=@t  command=@t
  ==
+$  catalog
  [revision=@ud entries=(map @t entry) creates=(map @t receipt)]
+$  facts  [home=@p epoch=@ud rank=@ud retired=?]
+$  current
  $-([who=actor:stead-session project=@t now=@ud] (unit facts))
+$  access  ?(%read %write %manage)
+$  resolved
  [destination=scope:stead-code-credentials profile=profile row=entry]
+$  error
  ?(%invalid-command %invalid-catalog %invalid-time %denied-or-not-found %authority-epoch-conflict %revision-conflict %request-id-reuse %repository-id-reuse %capacity-exceeded %unsupported-profile)
+$  decision
  $%  [%accepted next=catalog row=entry receipt=receipt initial=state:stead-code-store]
      [%replayed next=catalog row=entry receipt=receipt]
      [%denied reason=error]
  ==
++  uint64
  |=  value=@ud
  ^-  ?
  (lte value 18.446.744.073.709.551.615)
++  decode
  ::  No actor/profile/operation on input; first creation is inline SHA-1 only.
  |=  raw=@t
  ^-  command
  ?>  (lte (met 3 raw) 2.048)
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  data  p.value
  ?>  (keys data ~['request_id' 'project_id' 'repository_id' 'expected_catalog_revision' 'authority_epoch' 'display_name'])
  =/  request  (field data 'request_id')
  =/  project  (field data 'project_id')
  =/  repository  (field data 'repository_id')
  =/  expected  (uint (field data 'expected_catalog_revision'))
  =/  epoch  (uint (field data 'authority_epoch'))
  =/  name  (field data 'display_name')
  ?>  ?&  (uuid request)  (uuid project)  (uuid repository)
          (lte expected 4)  (gth epoch 0)  (title name)
      ==
  =/  bytes  (canonical value)
  [request project repository expected epoch name bytes (hash 'stead.repository-create/1' bytes)]
++  checked
  ::  Closed structural closure, not saved-history authenticity. Imports are
  ::  constructed only by the separate predecessor validator. All retained
  ::  create receipts correspond one-to-one with created entries/revisions.
  |=  db=catalog
  ^-  ?
  ?>  ?&  (lte ~(wyt by entries.db) 4)
          (lte ~(wyt by creates.db) 4)
          =(revision.db ~(wyt by entries.db))
      ==
  =/  imported=@ud  0
  =/  rows  ~(tap by entries.db)
  |-
  ?^  rows
    =/  id  p.i.rows
    =/  row  q.i.rows
    ?>  &((uuid id) (uuid project.row) =(1 metadata-revision.row))
    ?:  ?=(%legacy origin.row)
      ?>  &(legacy-alias.row =(id project.row) =('' name.row))
      $(rows t.rows, imported +(imported))
    ?>  ?&  !legacy-alias.row  =(%inline-sha1-v1 profile.row)
            (title name.row)  (uuid request.origin.row)  (uuid principal.origin.row)
        ==
    =/  saved  (~(got by creates.db) request.origin.row)
    ?>  ?&  (uuid request.saved)  =(id repository.saved)
            =(project.row project.saved)  =(principal.origin.row principal.saved)
        ==
    $(rows t.rows)
  ?>  =((sub revision.db imported) ~(wyt by creates.db))
  =/  saved  ~(tap by creates.db)
  =/  revisions=(set @ud)  ~
  |-
  ?~  saved  &
  =/  id  p.i.saved
  =/  receipt  q.i.saved
  =/  cmd  (decode command.receipt)
  =/  row  (~(got by entries.db) repository.receipt)
  ?>  ?=([%created *] origin.row)
  ?>  ?&  =(1 version.receipt)  =(id request.receipt)
          =(request.cmd request.receipt)  =(project.cmd project.receipt)
          =(repository.cmd repository.receipt)  =(name.cmd name.row)
          =(expected.cmd expected-revision.receipt)  =(epoch.cmd authority-epoch.receipt)
          =(canonical-bytes.cmd command.receipt)  =(digest.cmd digest.receipt)
          (uuid principal.receipt)  =(principal.receipt principal.actor.receipt)
          (lte (met 0 ship.actor.receipt) 128)
          (gth accepted-at.receipt 0)  (uint64 accepted-at.receipt)
          (live:stead-session actor.receipt accepted-at.receipt)
          =(+(expected-revision.receipt) revision.receipt)
          (gth revision.receipt imported)  (lte revision.receipt revision.db)
          !(~(has in revisions) revision.receipt)
          =(request.origin.row id)
          =(principal.origin.row principal.receipt)
      ==
  $(saved t.saved, revisions (~(put in revisions) revision.receipt))
++  valid
  |=  db=catalog
  ^-  ?
  =/  out  (mule |.((checked db)))
  ?:  ?=(%| -.out)  |
  p.out
++  current-facts
  |=  [who=actor:stead-session project=@t now=@ud read=current]
  ^-  (unit facts)
  ?.  ?&  (uuid project)  (gth now 0)  (uint64 now)
          (lte (met 0 ship.who) 128)  (live:stead-session who now)
      ==
    ~
  =/  out  (mule |.((read who project now)))
  ?:  ?=(%| -.out)  ~
  ?~  p.out  ~
  =/  facts  u.p.out
  ?.  ?&  (lte (met 0 home.facts) 128)  (gth epoch.facts 0)
          (uint64 epoch.facts)  (lte rank.facts 3)
      ==
    ~
  [~ facts]
++  resolve
  |=  [db=catalog target=ref who=actor:stead-session operation=access now=@ud read=current]
  ^-  (unit resolved)
  ?.  &((valid db) (uuid project.target) (uuid repository.target))  ~
  =/  found  (~(get by entries.db) repository.target)
  ?~  found  ~
  =/  row  u.found
  ?.  &(=(project.target project.row) =(%active lifecycle.row))  ~
  =/  facts  (current-facts who project.target now read)
  ?~  facts  ~
  =/  required=@ud  ?-(operation %read 1, %write 2, %manage 3)
  ?.  &((gte rank.u.facts required) ?:(=(%read operation) & !retired.u.facts))  ~
  [~ [home.u.facts project.target repository.target epoch.u.facts] profile.row row]
++  legacy-resolve
  ::  Equality of typed IDs alone never invents a legacy URL alias.
  |=  [db=catalog project=@t who=actor:stead-session operation=access now=@ud read=current]
  ^-  (unit resolved)
  ?.  (valid db)  ~
  =/  found  (~(get by entries.db) project)
  ?~  found  ~
  ?.  legacy-alias.u.found  ~
  (resolve db [project project] who operation now read)
++  create
  ::  Return catalog+new store together; an eventual carrier must publish both
  ::  atomically. A retry never returns a new initializer or external effect.
  |=  [db=catalog raw=@t who=actor:stead-session now=@ud read=current]
  ^-  decision
  ?.  (valid db)  [%denied %invalid-catalog]
  ?.  &((gth now 0) (uint64 now))  [%denied %invalid-time]
  =/  parsed  (mule |.((decode raw)))
  ?:  ?=(%| -.parsed)  [%denied %invalid-command]
  =/  cmd  p.parsed
  =/  facts  (current-facts who project.cmd now read)
  ?~  facts  [%denied %denied-or-not-found]
  ?.  &(=(3 rank.u.facts) !retired.u.facts)  [%denied %denied-or-not-found]
  =/  prior  (~(get by creates.db) request.cmd)
  ?^  prior
    ?.  ?&  =(principal.who principal.u.prior)  =(project.cmd project.u.prior)
            =(canonical-bytes.cmd command.u.prior)
        ==
      [%denied %request-id-reuse]
    [%replayed db (~(got by entries.db) repository.u.prior) u.prior]
  ?.  =(epoch.cmd epoch.u.facts)  [%denied %authority-epoch-conflict]
  ?.  =(expected.cmd revision.db)  [%denied %revision-conflict]
  ?:  (~(has by entries.db) repository.cmd)  [%denied %repository-id-reuse]
  ?:  (gte ~(wyt by entries.db) 4)  [%denied %capacity-exceeded]
  =/  row=entry
    [project.cmd name.cmd 1 %inline-sha1-v1 %active | [%created request.cmd principal.who]]
  =/  receipt=receipt
    [1 request.cmd project.cmd repository.cmd principal.who who epoch.cmd expected.cmd +(revision.db) now digest.cmd canonical-bytes.cmd]
  =/  next=catalog
    [+(revision.db) (~(put by entries.db) repository.cmd row) (~(put by creates.db) request.cmd receipt)]
  ?>  (valid next)
  =/  destination=scope:stead-code-credentials
    [home.u.facts project.cmd repository.cmd epoch.u.facts]
  [%accepted next row receipt (empty:stead-code-store destination)]
--
