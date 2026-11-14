::  A signed exact reviewed source tip. The Home reconstructs the resulting
::  manifest from the current selection and one approved prior/target pair.
/+  stead-codec, stead-code-pack-anchor, stead-code-pack-proof, stead-code-pack-push, stead-code-pack-review, stead-code-pack-worker-signature, stead-code-git-graph, stead-git
=,  stead-codec
|%
++  decode
  |=  $:  raw=@t  row=proposal:stead-code-pack-review
          base=manifest:stead-code-pack-anchor  request=@t
          worker=pin:stead-code-pack-worker-signature  epoch=@ud  signature=@t
      ==
  ^-  (unit evidence:stead-code-pack-push)
  ?.  (verify:stead-code-pack-worker-signature worker epoch raw signature)  ~
  =/  out
    %-  mule  |.
    ^-  evidence:stead-code-pack-push
    =/  proof  (read-wire:stead-code-pack-proof raw)
    ?>  (keys proof ~['protocol' 'request_id' 'scope' 'base_snapshot' 'candidate_snapshot' 'generation' 'proposal_id' 'revision' 'work_id' 'source' 'target' 'base_oid' 'head_oid'])
    =/  item  item.row
    =/  target  target.location.item
    ?>  ?&  =('stead.git-pack-reviewed-proof/1' (field proof 'protocol'))
            =(request (field proof 'request_id'))
            =(destination.row (read-scope:stead-code-pack-proof (nested:stead-code-pack-proof proof 'scope')))
            =(snapshot.row (field proof 'base_snapshot'))
            =(snapshot.row snapshot.base)
            =((decimal generation.row) (field proof 'generation'))
            =(id.item (field proof 'proposal_id'))
            =((decimal number.change.item) (field proof 'revision'))
            =(work.item (field proof 'work_id'))
            =((bytes-hex source.row) (field proof 'source'))
            =((bytes-hex target) (field proof 'target'))
            =((oid-text:stead-git base.change.item) (field proof 'base_oid'))
            =((oid-text:stead-git head.change.item) (field proof 'head_oid'))
        ==
    =/  next  base(snapshot (field proof 'candidate_snapshot'), refs (~(put by refs.base) (bytes-hex target) (field proof 'head_oid')))
    ?>  (valid-manifest:stead-code-pack-anchor next)
    :*  destination.row  snapshot.row  generation.row  (hash-wire:stead-code-pack-proof raw)  request
        ~[[target base.change.item head.change.item]]  next
        (~(put by *(map @ux object-kind:stead-code-git-graph)) head.change.item %commit)
        (silt ~[[base.change.item head.change.item]])
    ==
  ?:  ?=(%| -.out)  ~
  [~ p.out]
--
