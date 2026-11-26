::  Reserved verified actor seam. No wire decoder constructs these values.
::  The native branch preserves existing authentication and historical bytes.
::  A service has no invented ship; its verifier lives in service-bindings.
::  Service scope names its Home/project/Work. The current service profile also
::  rechecks its original native issuer context, including organization/team,
::  on every effect. These audit bytes are never a callerless authentication API.
/+  stead-codec, stead-team, stead-principals
=,  stead-codec
|%
+$  action  ?(%work-read %work-comment %doc-read %doc-propose)
+$  scope
  $:  home=@p  project=@t  epoch=@ud  work=@t
      collection=@t  document=@t  actions=(set action)
  ==
+$  service
  $:  principal=@t  binding=@t  revision=@ud
      credential=@t  generation=@ud  incarnation=@t  audit=@t
      expires=@ud  scope=scope
  ==
+$  verified
  $%  [%native context=authentication:stead-team]
      [%service context=service]
  ==
++  scope-valid
  |=  scope=scope
  ^-  ?
  ?&  (lte (met 0 home.scope) 128)
      (uuid project.scope)  (uuid work.scope)
      (gth epoch.scope 0)  (lte epoch.scope 18.446.744.073.709.551.615)
      (gth (lent ~(tap in actions.scope)) 0)  (lte (lent ~(tap in actions.scope)) 4)
      =/  docs  ?|((~(has in actions.scope) %doc-read) (~(has in actions.scope) %doc-propose))
      ?:  docs  &((uuid collection.scope) (uuid document.scope))
      &(=('' collection.scope) =('' document.scope))
  ==
++  scope-bytes
  |=  scope=scope
  ^-  @t
  ?>  (scope-valid scope)
  =/  actions
    %-  object
    (turn ~(tap in actions.scope) |=(action=action [(scot %tas action) 'yes']))
  %-  canonical
  (object ~[['home' (scot %p home.scope)] ['project_id' project.scope] ['authority_epoch' (decimal epoch.scope)] ['work_id' work.scope] ['collection_id' collection.scope] ['document_id' document.scope] ['actions' (canonical actions)]])
++  principal
  |=  actor=verified
  ^-  @t
  ?-  -.actor
    %native  principal.identity.context.actor
    %service  principal.context.actor
  ==
++  native-context
  |=  actor=verified
  ^-  (unit authentication:stead-team)
  ?-  -.actor
    %native  (some context.actor)
    %service  ~
  ==
++  verify-native
  |=  [db=state:stead-team catalog=state:stead-principals actor=authentication:stead-team now=@ud]
  ^-  (unit verified)
  ?.  (current:stead-team db actor now)  ~
  =/  principal  (~(get by principals.catalog) principal.identity.actor)
  ?~  principal  ~
  ?.  active.u.principal  ~
  (some [%native actor])
++  native-human
  |=  [db=state:stead-team catalog=state:stead-principals actor=verified now=@ud]
  ^-  ?
  ?.  ?=(%native -.actor)  |
  ?&  ?=(^ (verify-native db catalog context.actor now))
      =((some %person) (native-kind:stead-principals catalog registry.db principal.identity.context.actor now))
  ==
++  audit-bytes
  |=  actor=verified
  ^-  @t
  ?:  ?=(%native -.actor)  (authentication-json:stead-team context.actor)
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.service-auth/1']
      ['principal_id' principal.context.actor]  ['binding_id' binding.context.actor]
      ['binding_revision' (decimal revision.context.actor)]
      ['credential_handle' credential.context.actor]  ['credential_generation' (decimal generation.context.actor)]
      ['incarnation' incarnation.context.actor]  ['audit_id' audit.context.actor]
      ['expires_at_ms' (decimal expires.context.actor)]  ['scope' (scope-bytes scope.context.actor)]
  ==
--
