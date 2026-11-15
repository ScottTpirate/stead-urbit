::  Reserved service identity preparation. No public endpoint uses this core.
::  Owner changes and credential descriptors require one ordered Home history.
::  The live book is deliberately outside persistent state and must be replaced
::  with fresh Home entropy after load, retirement or custody transfer.
/+  stead-codec, stead-core, stead-session, stead-team, stead-principals, stead-actor
=,  stead-codec
|%
+$  binding
  $:  principal=@t  revision=@ud  custody=@t
      runtime=@t  runtime-revision=@ud  active=?  expires=@ud
  ==
+$  descriptor
  $:  principal=@t  binding=@t  revision=@ud  handle=@t
      generation=@ud  incarnation=@t  audit=@t  bearer-hash=@t
      scope=scope:stead-actor  issuer=authentication:stead-team
      issuer-grant=@t  issuer-authority=grant-state:stead-core
      target-grant=@t  target-authority=grant-state:stead-core
      issued-at=@ud  expires=@ud
  ==
+$  state
  $:  home=@p  serial=@ud  bindings=(map @t binding)
      owners=(map @t @t)  highwaters=(map @t @ud)
      descriptors=(map @t descriptor)  revoked=(set @t)
  ==
+$  live
  [incarnation=@t credentials=(map @t @t)]
+$  budget
  ::  Global counts supplied by the integrator, including every other family.
  ::  Security is a shared remainder, never an additional service-only pool.
  [ordinary=@ud security=@ud owner-security=@ud]
+$  change  [status=@tas next=state record=(unit @t)]
+$  issued
  [status=@tas next=state live=live bearer=@t handle=@t record=(unit @t)]
++  initialize
  |=  [db=state:stead-team home=@p]
  ^-  state
  ?>  ?=(^ current.registry.db)
  ?>  =(home home.u.current.registry.db)
  [home 0 ~ owners.registry.db ~ ~ ~]
++  new-live
  |=  [home=@p entropy=@]
  ^-  live
  ?>  !=(0 entropy)
  [(hash 'stead.service-incarnation/1' (bytes-hex (jam [home entropy]))) ~]
++  owner-authorized
  |=  [state=state db=state:stead-team sender=@p]
  ^-  ?
  ?&  =(sender home.state)  ?=(^ current.registry.db)
      =(home.state home.u.current.registry.db)
  ==
++  current-principal
  |=  [catalog=state:stead-principals principal=@t]
  ^-  ?
  =/  found  (~(get by principals.catalog) principal)
  ?~  found  |
  ?&  active.u.found  ?=(^ kind.u.found)
      ?|  =(%agent u.kind.u.found)  =(%service u.kind.u.found)
      ==
  ==
++  other-mechanism
  |=  [state=state db=state:stead-team principal=@t excluding=@t now=@ud]
  ^-  ?
  ?:  ?=(^ (native-member:stead-principals registry.db principal now))  &
  %+  lien  ~(tap by bindings.state)
  |=  [id=@t row=binding]
  &(!=(id excluding) =(principal principal.row) active.row (gth expires.row now))
++  runtime-valid
  |=  [catalog=state:stead-principals principal=@t runtime=@t revision=@ud]
  ^-  ?
  =/  who  (~(get by principals.catalog) principal)
  ?~  who  |
  ?~  kind.u.who  |
  ?:  =(%service u.kind.u.who)  &(=('' runtime) =(0 revision))
  ?.  =(%agent u.kind.u.who)  |
  =/  found  (~(get by runtimes.catalog) [runtime revision])
  ?~(found | =(principal principal.u.found))
++  binding-bytes
  |=  [id=@t binding=binding]
  ^-  @t
  %-  canonical
  (object ~[['binding_id' id] ['principal_id' principal.binding] ['revision' (decimal revision.binding)] ['custody' custody.binding] ['runtime_id' runtime.binding] ['runtime_revision' (decimal runtime-revision.binding)] ['active' ?:(active.binding 'yes' 'no')] ['expires_at_ms' (decimal expires.binding)]])
++  owner-bind
  |=  [state=state db=state:stead-team catalog=state:stead-principals sender=@p id=@t expected=@ud principal=@t custody=@t runtime=@t runtime-revision=@ud expires=@ud now=@ud used=@ud]
  ^-  change
  ?.  (owner-authorized state db sender)  [%denied state ~]
  ?.  ?&  (uuid id)  (uuid principal)  (title custody)
          (gth now 0)  (gth expires now)  (lte expires 18.446.744.073.709.551.615)
          (current-principal catalog principal)  (runtime-valid catalog principal runtime runtime-revision)
      ==
    [%invalid state ~]
  =/  prior  (~(get by bindings.state) id)
  =/  revision  ?~(prior 0 revision.u.prior)
  ?.  =(expected revision)  [%conflict state ~]
  =/  owner  (~(get by owners.state) id)
  ?.  ?~(owner & =(principal u.owner))  [%ownership-conflict state ~]
  =/  native-owner  (~(get by owners.registry.db) id)
  ?:  ?=(^ native-owner)  [%ownership-conflict state ~]
  ?.  ?~(prior & &(=(principal principal.u.prior) =(custody custody.u.prior)))  [%ownership-conflict state ~]
  ?:  (other-mechanism state db principal id now)  [%mechanism-conflict state ~]
  =/  highwater  (~(get by highwaters.state) id)
  =/  next-revision  +((max revision ?~(highwater 0 u.highwater)))
  ?:  ?|  (gte used 4.096)  (gth next-revision 18.446.744.073.709.551.615)
          &(?=(~ prior) (gte (lent ~(tap by bindings.state)) 128))
          &(?=(~ owner) (gte (lent ~(tap by owners.state)) 256))
      ==
    [%capacity state ~]
  =/  row=binding  [principal next-revision custody runtime runtime-revision & expires]
  =/  next  state(bindings (~(put by bindings.state) id row), owners (~(put by owners.state) id principal), highwaters (~(put by highwaters.state) id next-revision))
  [%accepted next (some (binding-bytes id row))]
++  owner-revoke
  |=  [state=state db=state:stead-team sender=@p id=@t expected=@ud now=@ud used=budget]
  ^-  change
  ?.  (owner-authorized state db sender)  [%denied state ~]
  ?.  &((gth now 0) (uint64 now))  [%invalid state ~]
  =/  prior  (~(get by bindings.state) id)
  ?~  prior  [%missing state ~]
  ?.  =(expected revision.u.prior)  [%conflict state ~]
  ?.  active.u.prior  [%unchanged state ~]
  =/  reducing
    ?&  (gth expires.u.prior now)
        =((some principal.u.prior) (~(get by owners.state) id))
        =((some revision.u.prior) (~(get by highwaters.state) id))
    ==
  =/  capacity  (reduction-capacity used reducing)
  ?:  ?|  ?=(~ capacity)  (gte revision.u.prior 18.446.744.073.709.551.615)
      ==
    [%capacity state ~]
  ?>  ?=(^ capacity)
  =/  row  u.prior(revision +(revision.u.prior), active |)
  =/  next  state(bindings (~(put by bindings.state) id row), highwaters (~(put by highwaters.state) id revision.row))
  =/  record
    (canonical (object ~[['protocol' 'stead.service-binding-revoke/1'] ['binding' (binding-bytes id row)] ['capacity_class' ?:(u.capacity 'security' 'ordinary')]]))
  [%accepted next (some record)]
++  reduction-capacity
  |=  [used=budget reducing=?]
  ^-  (unit ?)
  ?.  &((lte ordinary.used 4.096) (lte security.used 2.048) (lte owner-security.used 128))  ~
  ?:  (lth ordinary.used 4.096)  (some |)
  ?.  reducing  ~
  ?:  ?|((gte security.used 2.048) (gte owner-security.used 128))  ~
  (some &)
++  grant
  |=  [db=state:stead-team project=@t principal=@t maintainer=? now=@ud]
  ^-  (unit [key=@t value=grant-state:stead-core])
  =/  rows  ~(tap by grants.data.db)
  |-
  ?~  rows  ~
  =/  row  q.i.rows
  ?:  ?&  =(project project.row)  =(principal principal.row)
          !revoked.row  (gth expires.row now)
          ?:(maintainer =('maintainer' role.row) ?|(=('maintainer' role.row) =('contributor' role.row)))
      ==
    (some i.rows)
  $(rows t.rows)
++  scope-access
  ::  Uses shared core grants. A credential only narrows existing permission.
  |=  [db=state:stead-team principal=@t scope=scope:stead-actor operation=action:stead-actor now=@ud]
  ^-  ?
  ?.  (scope-valid:stead-actor scope)  |
  ?.  ?=(^ current.registry.db)  |
  ?.  =(home.scope home.u.current.registry.db)  |
  =/  project  (~(get by projects.data.db) project.scope)
  ?~  project  |
  ?.  ?&  !(closed:stead-core data.db project.scope)
          =(epoch.scope epoch.u.project)
          (gte (role:stead-core data.db principal project.scope now) 2)
          (~(has in actions.scope) operation)
          (~(has by works.data.db) [project.scope work.scope])
          !(~(has in tombs.db) [project.scope 'work' '' work.scope])
      ==
    |
  ?:  ?|  =(%work-read operation)  =(%work-comment operation)
      ==
    &
  =/  box  (~(get by boxes.db) collection.scope)
  ?~  box  |
  ?&  =(project.scope project.u.box)  =('shared' visibility.u.box)
      !(~(has in tombs.db) [project.scope 'document' collection.scope document.scope])
      ?:  =(%doc-propose operation)  &
      (~(has by documents.data.db) [project.scope (scope-key:stead-core collection.scope document.scope)])
  ==
++  current-binding
  |=  [state=state db=state:stead-team catalog=state:stead-principals id=@t now=@ud]
  ^-  (unit binding)
  ?.  ?=(^ current.registry.db)  ~
  ?.  =(home.state home.u.current.registry.db)  ~
  =/  found  (~(get by bindings.state) id)
  ?~  found  ~
  =/  row  u.found
  ?.  ?&  active.row  (gth expires.row now)
          !(~(has by owners.registry.db) id)
          =((some principal.row) (~(get by owners.state) id))
          =((some revision.row) (~(get by highwaters.state) id))
          (current-principal catalog principal.row)
          (runtime-valid catalog principal.row runtime.row runtime-revision.row)
          !(other-mechanism state db principal.row id now)
      ==
    ~
  found
++  grant-bytes
  |=  [key=@t grant=grant-state:stead-core]
  ^-  @t
  %-  canonical
  (object ~[['grant_key' key] ['project_id' project.grant] ['principal_id' principal.grant] ['role' role.grant] ['expires_at_ms' (decimal expires.grant)] ['revoked' ?:(revoked.grant 'yes' 'no')]])
++  descriptor-bytes
  |=  descriptor=descriptor
  ^-  @t
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.service-credential/1']
      ['principal_id' principal.descriptor]  ['binding_id' binding.descriptor]
      ['binding_revision' (decimal revision.descriptor)]
      ['handle' handle.descriptor]  ['generation' (decimal generation.descriptor)]
      ['incarnation' incarnation.descriptor]  ['audit_id' audit.descriptor]
      ['bearer_hash' bearer-hash.descriptor]  ['scope' (scope-bytes:stead-actor scope.descriptor)]
      ['issuer_authentication' (authentication-json:stead-team issuer.descriptor)]
      ['issuer_grant' (grant-bytes issuer-grant.descriptor issuer-authority.descriptor)]
      ['target_grant' (grant-bytes target-grant.descriptor target-authority.descriptor)]
      ['issued_at_ms' (decimal issued-at.descriptor)]  ['expires_at_ms' (decimal expires.descriptor)]
  ==
++  proof
  |=  descriptor=descriptor
  ^-  service:stead-actor
  [principal.descriptor binding.descriptor revision.descriptor handle.descriptor generation.descriptor incarnation.descriptor audit.descriptor expires.descriptor scope.descriptor]
++  issue
  ::  entropy and bearer belong only to the current carrier turn. Neither is
  ::  included in the returned persistent state or descriptor record.
  |=  [state=state book=live db=state:stead-team catalog=state:stead-principals issuer=verified:stead-actor id=@t scope=scope:stead-actor now=@ud entropy=@ used=@ud]
  ^-  issued
  ?.  (native-human:stead-actor db catalog issuer now)  [%denied state book '' '' ~]
  ?>  ?=(%native -.issuer)
  =/  actor  context.issuer
  ?.  &(=(home.state home.scope) (scope-valid:stead-actor scope))  [%denied state book '' '' ~]
  =/  binding  (current-binding state db catalog id now)
  ?~  binding  [%denied state book '' '' ~]
  ?.  (gte (role:stead-team db actor project.scope now) 3)  [%denied state book '' '' ~]
  =/  authorizing  (grant db project.scope principal.identity.actor & now)
  =/  target  (grant db project.scope principal.u.binding | now)
  ?.  &(?=(^ authorizing) ?=(^ target))  [%denied state book '' '' ~]
  ?.  %+  levy  ~(tap in actions.scope)
      |=(action=action:stead-actor (scope-access db principal.u.binding scope action now))
    [%denied state book '' '' ~]
  ?.  &(!=(0 entropy) (token-valid:stead-session incarnation.book) (gth now 0))
    [%invalid state book '' '' ~]
  =/  remaining
    %-  malt
    %+  skim  ~(tap by credentials.book)
    |=  [hash=@t handle=@t]
    =/  row  (~(get by descriptors.state) handle)
    ?~  row  |
    =/  binding  (current-binding state db catalog binding.u.row now)
    ?~  binding  |
    ?&  (gth expires.u.row now)  !(~(has in revoked.state) handle)
        =(incarnation.book incarnation.u.row)  =(revision.u.row revision.u.binding)
    ==
  ?:  ?|  (gte used 4.096)  (gte serial.state 18.446.744.073.709.551.615)
          (gte (lent ~(tap by descriptors.state)) 4.096)  (gte (lent ~(tap by remaining)) 64)
      ==
    [%capacity state book '' '' ~]
  =/  until
    (min (add now 900.000) (min expires.u.binding (min expires.actor (min expires.value.u.authorizing expires.value.u.target))))
  ?.  (gth until now)  [%denied state book '' '' ~]
  =/  serial  +(serial.state)
  =/  bearer  (token:stead-session entropy serial 'stead.service-bearer/1')
  =/  hash  (digest:stead-session 'stead.service-credential/1' bearer)
  =/  handle  (token:stead-session entropy serial 'stead.service-handle/1')
  =/  audit  (token:stead-session entropy serial 'stead.service-audit/1')
  ?:  ?|  (~(has by descriptors.state) handle)  (~(has by remaining) hash)
      ==
    [%capacity state book '' '' ~]
  =/  row=descriptor
    [principal.u.binding id revision.u.binding handle serial incarnation.book audit hash scope actor key.u.authorizing value.u.authorizing key.u.target value.u.target now until]
  =/  next  state(serial serial, descriptors (~(put by descriptors.state) handle row))
  =/  live  book(credentials (~(put by remaining) hash handle))
  [%accepted next live bearer handle (some (descriptor-bytes row))]
++  recheck-effect
  |=  [state=state book=live db=state:stead-team catalog=state:stead-principals actor=verified:stead-actor scope=scope:stead-actor operation=action:stead-actor now=@ud]
  ^-  ?
  ?.  ?=(%service -.actor)  |
  ?.  (lte (lent ~(tap by credentials.book)) 64)  |
  =/  context  context.actor
  ?.  &(=(incarnation.book incarnation.context) =(scope scope.context))  |
  =/  found  (~(get by descriptors.state) credential.context)
  ?~  found  |
  =/  row  u.found
  ?.  ?&  =(context (proof row))
          (gth expires.row now)  !(~(has in revoked.state) handle.row)
          =((some handle.row) (~(get by credentials.book) bearer-hash.row))
      ==
    |
  =/  binding  (current-binding state db catalog binding.row now)
  ?~  binding  |
  ?.  &(=(principal.row principal.u.binding) =(revision.row revision.u.binding))  |
  ?.  ?&  =((some issuer-authority.row) (~(get by grants.data.db) issuer-grant.row))
          =((some target-authority.row) (~(get by grants.data.db) target-grant.row))
          !revoked.issuer-authority.row  !revoked.target-authority.row
          (gth expires.issuer-authority.row now)  (gth expires.target-authority.row now)
          (native-human:stead-actor db catalog [%native issuer.row] now)
      ==
    |
  (scope-access db principal.row scope operation now)
++  verify-bearer
  |=  [state=state book=live db=state:stead-team catalog=state:stead-principals bearer=@t scope=scope:stead-actor operation=action:stead-actor now=@ud]
  ^-  (unit verified:stead-actor)
  ?.  (token-valid:stead-session bearer)  ~
  =/  hash  (digest:stead-session 'stead.service-credential/1' bearer)
  =/  handle  (~(get by credentials.book) hash)
  ?~  handle  ~
  =/  row  (~(get by descriptors.state) u.handle)
  ?~  row  ~
  ?.  =(hash bearer-hash.u.row)  ~
  =/  actor=verified:stead-actor  [%service (proof u.row)]
  ?:((recheck-effect state book db catalog actor scope operation now) (some actor) ~)
++  revoke-credential
  |=  [state=state book=live db=state:stead-team catalog=state:stead-principals issuer=verified:stead-actor handle=@t now=@ud used=budget]
  ^-  change
  ?.  &((gth now 0) (uint64 now))  [%invalid state ~]
  ?.  (native-human:stead-actor db catalog issuer now)  [%denied state ~]
  ?>  ?=(%native -.issuer)
  =/  found  (~(get by descriptors.state) handle)
  ?~  found  [%missing state ~]
  ?.  (gte (role:stead-team db context.issuer project.scope.u.found now) 3)  [%denied state ~]
  ?:  (~(has in revoked.state) handle)  [%unchanged state ~]
  ::  Catalog/grant disablement is not permanent credential revocation. A
  ::  retained current-incarnation capability may still need the shared reserve
  ::  so later catalog/grant reactivation cannot revive a compromised bearer.
  =/  reducing
    ?&  (gth expires.u.found now)
        =(incarnation.book incarnation.u.found)
        =((some handle) (~(get by credentials.book) bearer-hash.u.found))
        (lte (lent ~(tap by credentials.book)) 64)
    ==
  =/  capacity  (reduction-capacity used reducing)
  ?~  capacity  [%capacity state ~]
  =/  record
    %-  canonical
    (object ~[['protocol' 'stead.service-revoke/1'] ['handle' handle] ['issuer_authentication' (authentication-json:stead-team context.issuer)] ['recorded_at_ms' (decimal now)] ['capacity_class' ?:(u.capacity 'security' 'ordinary')]])
  [%accepted state(revoked (~(put in revoked.state) handle)) (some record)]
++  uint64
  |=  value=@ud
  ^-  ?
  (lte value 18.446.744.073.709.551.615)
++  scoped-key
  |=  [project=@t key=@t]
  ^-  ?
  ?&  =(73 (met 3 key))
      =/  id  (cut 3 [37 36] key)
      &((uuid id) =(key (scope-key:stead-core project id)))
  ==
++  auth-bounded
  |=  actor=authentication:stead-team
  ^-  ?
  ?&  (lte (met 0 ship.identity.actor) 128)  (lte (met 0 home.actor) 128)
      (uuid principal.identity.actor)  (uuid binding.identity.actor)
      (uuid organization.actor)  (uuid team.actor)
      (uint64 revision.identity.actor)  (uint64 expires.identity.actor)  (uint64 expires.actor)
      (lte (met 3 method.actor) 64)  (lte (met 3 strength.actor) 64)
      (lte (met 3 audit.actor) 64)  (lte (met 3 runtime.actor) 64)
      =(actor (decode-authentication:stead-team (authentication-json:stead-team actor)))
  ==
++  bounded-state
  ::  Early admission only. Ordered owner/issuance history must still regenerate
  ::  this whole value; recorded actor fields do not authenticate themselves.
  |=  state=state
  ^-  ?
  =/  checked  (mule |.((state-bounds state)))
  ?:  ?=(%| -.checked)  |
  p.checked
++  state-bounds
  |=  state=state
  ^-  ?
  ?&  (lte (met 0 home.state) 128)  (uint64 serial.state)
      (lte (lent ~(tap by bindings.state)) 128)
      (lte (lent ~(tap by owners.state)) 256)
      (lte (lent ~(tap by highwaters.state)) 128)
      (lte (lent ~(tap by descriptors.state)) 4.096)
      (lte (lent ~(tap in revoked.state)) 4.096)
      %+  levy  ~(tap by owners.state)
      |=  [id=@t principal=@t]
      &((uuid id) (uuid principal))
      %+  levy  ~(tap by highwaters.state)
      |=  [id=@t revision=@ud]
      ?&  (uuid id)  (gth revision 0)  (uint64 revision)
          =/  row  (~(get by bindings.state) id)
          ?~(row | =(revision revision.u.row))
      ==
      %+  levy  ~(tap by bindings.state)
      |=  [id=@t row=binding]
      ?&  (uuid id)  (uuid principal.row)  (title custody.row)
          (gth revision.row 0)  (uint64 revision.row)
          =((some principal.row) (~(get by owners.state) id))
          =((some revision.row) (~(get by highwaters.state) id))
          ?:(=('' runtime.row) =(0 runtime-revision.row) &((uuid runtime.row) (gth runtime-revision.row 0) (uint64 runtime-revision.row)))
          (gth expires.row 0)  (uint64 expires.row)
      ==
      %+  levy  ~(tap in revoked.state)
      |=  handle=@t
      &((token-valid:stead-session handle) (~(has by descriptors.state) handle))
      %+  levy  ~(tap by descriptors.state)
      |=  [handle=@t row=descriptor]
      ?&  (token-valid:stead-session handle)  =(handle handle.row)
          (uuid principal.row)  (uuid binding.row)
          (gth revision.row 0)  (uint64 revision.row)
          =((some principal.row) (~(get by owners.state) binding.row))
          =/  highwater  (~(get by highwaters.state) binding.row)
          ?~(highwater | (gte u.highwater revision.row))
          (gth generation.row 0)  (lte generation.row serial.state)
          (token-valid:stead-session incarnation.row)  (token-valid:stead-session audit.row)
          (token-valid:stead-session bearer-hash.row)
          (scope-valid:stead-actor scope.row)  =(home.state home.scope.row)
          (auth-bounded issuer.row)  =(home.state home.issuer.row)
          (scoped-key project.scope.row issuer-grant.row)
          (scoped-key project.scope.row target-grant.row)
          =(project.scope.row project.issuer-authority.row)
          =(project.scope.row project.target-authority.row)
          =(principal.identity.issuer.row principal.issuer-authority.row)
          =(principal.row principal.target-authority.row)
          =('maintainer' role.issuer-authority.row)
          ?|(=('contributor' role.target-authority.row) =('maintainer' role.target-authority.row))
          !revoked.issuer-authority.row  !revoked.target-authority.row
          (uint64 expires.issuer-authority.row)  (uint64 expires.target-authority.row)
          (gth issued-at.row 0)  (gth expires.row issued-at.row)  (uint64 expires.row)
          (lte (sub expires.row issued-at.row) 900.000)
          (lte expires.row expires.issuer.row)
          (lte expires.row expires.issuer-authority.row)  (lte expires.row expires.target-authority.row)
          (lte (met 3 (descriptor-bytes row)) 8.192)
      ==
  ==
++  bounded-live
  ::  This validates an already-current ephemeral book; it never rebuilds one
  ::  from the persistent descriptors or makes an old incarnation current.
  |=  [state=state book=live]
  ^-  ?
  ?&  (token-valid:stead-session incarnation.book)
      (lte (lent ~(tap by credentials.book)) 64)
      %+  levy  ~(tap by credentials.book)
      |=  [hash=@t handle=@t]
      ?&  (token-valid:stead-session hash)  (token-valid:stead-session handle)
          =/  row  (~(get by descriptors.state) handle)
          ?~  row  |
          &(=(hash bearer-hash.u.row) =(handle handle.u.row) =(incarnation.book incarnation.u.row))
      ==
  ==
--
