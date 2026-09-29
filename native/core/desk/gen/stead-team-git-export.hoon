:: Owned synthetic qualification only: inspect stored bytes, never author Git.
/+  stead-codec, stead-git, stead-team-owner
:-  %say
|=  [[now=@da eny=@uvJ bec=beak] [[mode=@tas project=@t container=@t head=@ux oid=@ux] ~] ~]
:-  %noun
^-  @ux
?>  &((uuid:stead-codec project) (uuid:stead-codec container))
?>  &((lte (met 0 head) 160) (lte (met 0 oid) 160))
=/  egg=egg-any:gall
  .^  egg-any:gall  %gv
    (scot %p p.bec)
    %stead-home
    (scot %da now)
    /$
  ==
?>  ?=([%20 %live *] egg)
=/  saved=vase  +.old-state.egg
=/  loaded  !<([%stead-home %3 team=saved:stead-team-owner] saved)
=/  db  db.team.loaded
=/  config  (need current.registry.db)
?>  &(=(~zod home.config) =('isolated-fake' runtime.config) =('local-disposable' custody.config))
=/  box  (~(got by containers.data.db) container)
?>  =(project project.box)
?>  (lien history.box |=(snapshot=@ux =(snapshot head)))
=/  reachable  (~(got by reachable.data.db) head)
?>  (lte (lent ~(tap in reachable)) 512)
=/  value
  ?:  =(%manifest mode)
    =/  types
      %-  object:stead-codec
      %+  turn  ~(tap in reachable)
      |=  key=@ux
      [(oid-text:stead-git key) kind:(~(got by objects.data.db) key)]
    =/  fields  (object:stead-codec ~[['protocol' 'stead.fixture-git/3'] ['project_id' project] ['container_id' container] ['snapshot_commit_oid' (oid-text:stead-git head)]])
    ?>  ?=([%o *] fields)
    [%o (~(put by p.fields) 'objects' types)]
  ?>  =(%object mode)
  ?>  (~(has in reachable) oid)
  =/  item  (~(got by objects.data.db) oid)
  ?>  &(=(oid oid.item) (lte length.body.item 65.536))
  =/  bytes  (hex:stead-codec (mul 2 length.body.item) (rev 3 length.body.item data.body.item))
  %-  object:stead-codec
  :~  ['protocol' 'stead.fixture-git-object/3']
      ['snapshot_commit_oid' (oid-text:stead-git head)]
      ['oid' (oid-text:stead-git oid)]  ['kind' kind.item]
      ['byte_length' (decimal:stead-codec length.body.item)]  ['hex' bytes]
  ==
=/  bytes  (canonical:stead-codec value)
?>  (lte (met 3 bytes) 196.608)
`@ux``@`bytes
