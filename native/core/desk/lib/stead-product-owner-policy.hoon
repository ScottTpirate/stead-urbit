::  Native registry/catalog reconciliation and exact reserve eligibility.
::  No mutation, external effect, live sender check or timeline append here.
/+  stead-codec, stead-session, stead-team-config, stead-principals
=,  stead-codec
|%
++  reconcile
  |=  [catalog=state:stead-principals registry=registry:stead-team-config home=@p]
  ^-  state:stead-principals
  =/  imported  (import:stead-principals registry home)
  ?>  %+  levy  ~(tap by binding-owners.catalog)
      |=  [binding=@t principal=@t]
      =((some principal) (~(get by owners.registry) binding))
  ?>  %+  levy  ~(tap by principal-highwaters.catalog)
      |=  [principal=@t high=@ud]
      =/  next  (~(get by revisions.registry) principal)
      ?~(next | (gte u.next high))
  =/  people  principals.catalog
  =/  rows  ~(tap by principals.imported)
  |-
  ?~  rows
    ?>  (lte (lent ~(tap by people)) 128)
    catalog(principals people, binding-owners owners.registry, principal-highwaters revisions.registry)
  =/  key  p.i.rows
  ?:  (~(has by people) key)  $(rows t.rows)
  $(rows t.rows, people (~(put by people) key q.i.rows))
++  config-reduces
  |=  [before=registry:stead-team-config after=registry:stead-team-config now=@ud]
  ^-  ?
  ?~  current.before  |
  ?~  current.after  |
  =/  old  u.current.before
  =/  new  u.current.after
  ?.  ?&  =(home.old home.new)  =(origin.old origin.new)
          =(organization.old organization.new)  =(team.old team.new)
          =(custody.old custody.new)  =(runtime.old runtime.new)
          %+  levy  ~(tap in creators.new)
          |=  id=@t
          (~(has in creators.old) id)
      ==
    |
  =/  subset
    %+  levy  ~(tap by members.new)
    |=  [ship=@p member=member:stead-team-config]
    =/  prior  (~(get by members.old) ship)
    ?~  prior  |
    =/  left  identity.u.prior
    =/  right  identity.member
    ?&  =(principal.left principal.right)  =(binding.left binding.right)
        ?|(!active.right active.left)
        (lte expires.right expires.left)
    ==
  ?.  subset  |
  ?|  %+  lien  ~(tap in creators.old)
      |=  id=@t
      !(~(has in creators.new) id)
      %+  lien  ~(tap by members.old)
      |=  [ship=@p member=member:stead-team-config]
      ?.  (live:stead-session identity.member now)  |
      =/  next  (~(get by members.new) ship)
      ?~  next  &
      ?|(!active.identity.u.next (lth expires.identity.u.next expires.identity.member))
  ==
++  principal-reduces
  |=  [before=state:stead-principals after=state:stead-principals id=@t]
  ^-  ?
  =/  old  (~(get by principals.before) id)
  =/  new  (~(get by principals.after) id)
  ?~  old  |
  ?~  new  |
  ?&  active.u.old  !active.u.new  ?=(^ kind.u.old)
      =(kind.u.old kind.u.new)
  ==
--
