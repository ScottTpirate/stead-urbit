::  Reserved principal catalog. No saved envelope or public route uses it yet.
::  Administrative gates take the actual Gall sender supplied by Home, never
::  a payload actor. Project grants and transport verification remain separate.
/+  stead-codec, stead-session, stead-team-config
=,  stead-codec
|%
+$  kind  ?(%person %agent %service)
+$  principal
  $:  revision=@ud  kind=(unit kind)  display=@t  active=?
      imported=?  declared-at=@ud
  ==
+$  runtime
  $:  principal=@t  revision=@ud  profile=@t  policy-digest=@t
      declared-at=@ud
  ==
+$  definition
  $:  principal=@t  revision=@ud  instructions-digest=@t
      runtime-id=@t  runtime-revision=@ud  declared-at=@ud
  ==
+$  state
  $:  source=@t  principals=(map @t principal)
      binding-owners=(map @t @t)  principal-highwaters=(map @t @ud)
      runtimes=(map [id=@t revision=@ud] runtime)
      runtime-heads=(map @t @ud)
      definitions=(map [id=@t revision=@ud] definition)
      definition-heads=(map @t @ud)
  ==
+$  result  [status=@tas next=state]
++  empty  *state
++  valid-digest
  |=  text=@t
  ^-  ?
  (token-valid:stead-session text)
++  import
  |=  [registry=registry:stead-team-config home=@p]
  ^-  state
  ?>  (validate:stead-team-config registry home)
  =/  people  ~(tap by revisions.registry)
  =/  current=(list [ship=@p person=member:stead-team-config])
    ?~(current.registry ~ ~(tap by members.u.current.registry))
  =/  records=(map @t principal)  ~
  |-
  ?~  people
    :*  (hash 'stead.principal-import/1' (bytes-hex (jam registry)))
        records  owners.registry  revisions.registry  ~  ~  ~  ~
    ==
  =/  matches  (skim current |=([ship=@p person=member:stead-team-config] =(p.i.people principal.identity.person)))
  =/  display  ?~(matches '' display.person.i.matches)
  ::  Native identity is not evidence of a human kind. Removed members retain
  ::  their stable identity and binding ownership without invented display.
  =/  record=principal  [1 ~ display & & 0]
  $(people t.people, records (~(put by records) p.i.people record))
++  native-member
  |=  [registry=registry:stead-team-config id=@t now=@ud]
  ^-  (unit member:stead-team-config)
  ?~  current.registry  ~
  =/  people  ~(tap by members.u.current.registry)
  |-
  ?~  people  ~
  =/  member  q.i.people
  ?:  &(=(id principal.identity.member) (live:stead-session identity.member now))
    (some member)
  $(people t.people)
++  native-kind
  ::  Current binding and catalog activity both matter. This provides only
  ::  the kind; the caller still resolves current project membership/grants.
  |=  [db=state registry=registry:stead-team-config id=@t now=@ud]
  ^-  (unit kind)
  =/  found  (~(get by principals.db) id)
  ?~  found  ~
  ?.  active.u.found  ~
  =/  member  (native-member registry id now)
  ?~  member  ~
  =/  owner  (~(get by owners.registry) binding.identity.u.member)
  ?.  ?~(owner | =(id u.owner))  ~
  =/  original-owner  (~(get by binding-owners.db) binding.identity.u.member)
  ?.  ?~(original-owner & =(id u.original-owner))  ~
  =/  highwater  (~(get by principal-highwaters.db) id)
  ?.  ?~(highwater & (gte revision.identity.u.member u.highwater))  ~
  kind.u.found
++  declare
  ::  Kind is immutable once declared, including after deactivation. Display
  ::  and activity can change through CAS without rewriting earlier authors.
  |=  [db=state sender=@p home=@p id=@t expected=@ud selected=kind display=@t active=? now=@ud]
  ^-  result
  ?.  =(sender home)  [%denied db]
  ?.  &((uuid id) (title display) (gth now 0) (lte now 18.446.744.073.709.551.615))  [%invalid db]
  =/  found  (~(get by principals.db) id)
  =/  revision  ?~(found 0 revision.u.found)
  ?.  =(expected revision)  [%conflict db]
  ?:  (gte revision 18.446.744.073.709.551.615)  [%capacity db]
  ?:  &(?=(~ found) (gte (lent ~(tap by principals.db)) 128))  [%capacity db]
  ?.  ?~  found  &
      ?~  kind.u.found  &
      =(selected u.kind.u.found)
    [%kind-conflict db]
  =/  record=principal
    [+(revision) (some selected) display active ?~(found | imported.u.found) now]
  [%accepted db(principals (~(put by principals.db) id record))]
++  agent-active
  |=  [db=state id=@t]
  ^-  ?
  =/  person  (~(get by principals.db) id)
  ?~  person  |
  ?&  active.u.person
      ?~(kind.u.person | =(%agent u.kind.u.person))
  ==
++  runtime-put
  ::  Runtime profiles contain no credential. A new immutable version never
  ::  changes an existing definition or a run's pinned policy.
  |=  [db=state sender=@p home=@p id=@t expected=@ud principal=@t profile=@t policy=@t now=@ud]
  ^-  result
  ?.  =(sender home)  [%denied db]
  ?.  ?&  (uuid id)  (agent-active db principal)
          (title profile)  (valid-digest policy)
          (gth now 0)  (lte now 18.446.744.073.709.551.615)
      ==
    [%invalid db]
  =/  head  (~(get by runtime-heads.db) id)
  =/  revision  ?~(head 0 u.head)
  ?.  =(expected revision)  [%conflict db]
  ?:  ?|  (gte revision 18.446.744.073.709.551.615)
          (gte (lent ~(tap by runtimes.db)) 128)
          &(?=(~ head) (gte (lent ~(tap by runtime-heads.db)) 32))
      ==
    [%capacity db]
  ?:  ?~  head  |
      !=(principal principal:(~(got by runtimes.db) [id u.head]))
    [%ownership-conflict db]
  =/  record=runtime  [principal +(revision) profile policy now]
  [%accepted db(runtimes (~(put by runtimes.db) [id +(revision)] record), runtime-heads (~(put by runtime-heads.db) id +(revision)))]
++  definition-put
  |=  [db=state sender=@p home=@p id=@t expected=@ud principal=@t instructions=@t runtime-id=@t runtime-revision=@ud now=@ud]
  ^-  result
  ?.  =(sender home)  [%denied db]
  ?.  ?&  (uuid id)  (agent-active db principal)  (valid-digest instructions)
          (uuid runtime-id)  (gth runtime-revision 0)
          (gth now 0)  (lte now 18.446.744.073.709.551.615)
      ==
    [%invalid db]
  =/  runtime  (~(get by runtimes.db) [runtime-id runtime-revision])
  ?.  ?~(runtime | =(principal principal.u.runtime))  [%invalid db]
  =/  head  (~(get by definition-heads.db) id)
  =/  revision  ?~(head 0 u.head)
  ?.  =(expected revision)  [%conflict db]
  ?:  ?|  (gte revision 18.446.744.073.709.551.615)
          (gte (lent ~(tap by definitions.db)) 128)
          &(?=(~ head) (gte (lent ~(tap by definition-heads.db)) 32))
      ==
    [%capacity db]
  ?:  ?~  head  |
      !=(principal principal:(~(got by definitions.db) [id u.head]))
    [%ownership-conflict db]
  =/  record=definition  [principal +(revision) instructions runtime-id runtime-revision now]
  [%accepted db(definitions (~(put by definitions.db) [id +(revision)] record), definition-heads (~(put by definition-heads.db) id +(revision)))]
--
