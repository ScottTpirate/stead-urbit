::  Owner-local configuration decoder. No fixture-principal remapping.
/+  stead-codec, stead-session
=,  stead-codec
|%
+$  member  [identity=actor:stead-session display=@t]
+$  config
  $:  revision=@ud  home=@p  origin=@t  organization=@t  team=@t
      custody=@t  runtime=@t  members=(map @p member)  creators=(set @t)
  ==
+$  registry  [current=(unit config) revisions=(map @t @ud) owners=(map @t @t)]
++  decode
  |=  [raw=@t prior=registry home=@p now=@ud]
  ^-  registry
  ~|  %stead-invalid-team-config
  ?>  (lte (met 0 home) 128)
  ?>  (validate prior home)
  ?>  (lte (met 3 raw) 65.536)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['protocol' 'expected_revision' 'home' 'origin' 'organization_id' 'team_id' 'custody' 'runtime' 'bindings' 'project_creators'])
  ?>  =('stead.team-config/1' (field obj 'protocol'))
  ?>  =((scot %p home) (field obj 'home'))
  =/  expected  (uint (field obj 'expected_revision'))
  ?>  (lth expected 18.446.744.073.709.551.615)
  ?>  =(expected ?~(current.prior 0 revision.u.current.prior))
  =/  origin  (field obj 'origin')
  =/  organization  (field obj 'organization_id')
  =/  team  (field obj 'team_id')
  =/  custody  (field obj 'custody')
  =/  runtime  (field obj 'runtime')
  ?>  &((origin-valid:stead-session origin) (uuid organization) (uuid team))
  ::  The first qualified profile is disposable fake networking. Live custody
  ::  and provisioning need their own reviewed admission before a new profile.
  ?>  &(=('local-disposable' custody) =('isolated-fake' runtime))
  ?>  ?~  current.prior  &
      ?&  =(home home.u.current.prior)
          =(organization organization.u.current.prior)
          =(team team.u.current.prior)
          =(custody custody.u.current.prior)
      ==
  =/  people  (~(got by obj) 'bindings')
  =/  creators  (~(got by obj) 'project_creators')
  ?>  &(?=([%o *] people) ?=([%o *] creators))
  =/  pairs  ~(tap by p.people)
  ?>  &((gth (lent pairs) 0) (lte (lent pairs) 32) (lte (lent ~(tap by p.creators)) 8))
  =/  members=(map @p member)  ~
  =/  principals=(set @t)  ~
  =/  ids=(set @t)  ~
  =/  history  revisions.prior
  =/  owners  owners.prior
  =/  rights=(set @t)  ~
  =/  prepared
    |-
    ?~  pairs  [members principals history owners]
    =/  ship  (need (slaw %p p.i.pairs))
    ?>  (lte (met 0 ship) 128)
    ?>  &(!=(ship home) =((scot %p ship) p.i.pairs) ?=([%o *] q.i.pairs))
    =/  person  p.q.i.pairs
    ?>  (keys person ~['principal_id' 'binding_id' 'binding_revision' 'active' 'expires_at_ms' 'display_name'])
    =/  principal  (field person 'principal_id')
    =/  binding  (field person 'binding_id')
    =/  revision  (uint (field person 'binding_revision'))
    =/  expiry  (uint (field person 'expires_at_ms'))
    =/  active  (field person 'active')
    =/  display  (field person 'display_name')
    ?>  &((uuid principal) (uuid binding) (gth revision 0) (gth expiry 0) (title display))
    ?>  ?|(=('yes' active) =('no' active))
    ?>  ?|  =('no' active)  (gth expiry now)
        ==
    ?>  &(!(~(has in principals) principal) !(~(has in ids) binding))
    =/  identity=actor:stead-session  [ship principal binding revision =('yes' active) expiry]
    =/  owner  (~(get by owners) binding)
    ?>  ?~(owner & =(principal u.owner))
    =/  last  (~(get by history) principal)
    =/  existing=(unit member)
      ?~  current.prior  ~
      (~(get by members.u.current.prior) ship)
    ?>  ?~  last  &
        ?:  &(?=(^ existing) =(identity identity.u.existing))
          =(revision u.last)
        (gth revision u.last)
    $(pairs t.pairs, members (~(put by members) ship [identity display]), principals (~(put in principals) principal), ids (~(put in ids) binding), history (~(put by history) principal revision), owners (~(put by owners) binding principal))
  =.  members  -.prepared
  =.  principals  +<.prepared
  =.  history  -.+>.prepared
  =.  owners  +.+>.prepared
  ?>  &((lte (lent ~(tap by history)) 128) (lte (lent ~(tap by owners)) 256))
  =/  create-pairs  ~(tap by p.creators)
  |-
  ?~  create-pairs
    [[~ [+(expected) home origin organization team custody runtime members rights]] history owners]
  =/  id  p.i.create-pairs
  ?>  &((~(has in principals) id) =([%s 'yes'] q.i.create-pairs))
  $(create-pairs t.create-pairs, rights (~(put in rights) id))
++  validate
  |=  [registry=registry home=@p]
  ^-  ?
  ?>  (lte (met 0 home) 128)
  ?~  current.registry  &(?=(~ revisions.registry) ?=(~ owners.registry))
  =/  config  u.current.registry
  ?>  &((gth revision.config 0) (lte revision.config 18.446.744.073.709.551.615) =(home home.config))
  ?>  &((origin-valid:stead-session origin.config) (uuid organization.config) (uuid team.config))
  ?>  &(=('local-disposable' custody.config) =('isolated-fake' runtime.config))
  ?>  &((lte (lent ~(tap by revisions.registry)) 128) (lte (lent ~(tap by owners.registry)) 256))
  ?>  (levy ~(tap by revisions.registry) |=([id=@t rev=@ud] &((uuid id) (gth rev 0) (lte rev 18.446.744.073.709.551.615))))
  ?>  (levy ~(tap by owners.registry) |=([id=@t principal=@t] &((uuid id) (~(has by revisions.registry) principal))))
  ?>  (levy ~(tap by revisions.registry) |=([id=@t rev=@ud] (lien ~(tap by owners.registry) |=([binding=@t principal=@t] =(id principal)))))
  =/  people  ~(tap by members.config)
  ?>  &((gth (lent people) 0) (lte (lent people) 32) (lte (lent ~(tap in creators.config)) 8))
  =/  principals=(set @t)  ~
  =/  bindings=(set @t)  ~
  |-
  ?~  people  (levy ~(tap in creators.config) |=(id=@t (~(has in principals) id)))
  =/  actor  identity.q.i.people
  ?>  (lte (met 0 ship.actor) 128)
  ?>  &(!=(p.i.people home) =(p.i.people ship.actor) (title display.q.i.people))
  ?>  (live:stead-session actor(active &) 0)
  ?>  &(!(~(has in principals) principal.actor) !(~(has in bindings) binding.actor))
  ?>  &(=(revision.actor (~(got by revisions.registry) principal.actor)) =(principal.actor (~(got by owners.registry) binding.actor)))
  $(people t.people, principals (~(put in principals) principal.actor), bindings (~(put in bindings) binding.actor))
++  identity
  |=  [registry=registry sender=@p now=@ud]
  ^-  (unit member)
  ?~  current.registry  ~
  =/  found  (~(get by members.u.current.registry) sender)
  ?~  found  ~
  ?.  (live:stead-session identity.u.found now)  ~
  found
--
