::  PRIVATE trusted old Code tuple importer. Calls actual old validators;
::  returns every existing tail unchanged. No Gall save/load/carrier activation.
/+  stead-team, stead-code-home, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-review-board, stead-repository-catalog
|%
+$  external  (map @t ledger:stead-code-pack-ledger)
+$  boards  (map @t state:stead-code-pack-review-board)
+$  imported
  $:  catalog=catalog:stead-repository-catalog  code=persisted:stead-code-home
      packs=state:stead-code-pack-anchor  external=external  boards=boards
  ==
++  checked
  |=  $:  team=state:stead-team  code=persisted:stead-code-home
          packs=state:stead-code-pack-anchor  external=external  boards=boards
      ==
  ^-  imported
  ?>  (validate-persisted:stead-code-home team code)
  ?>  (validate-packs:stead-code-home team repos.code packs)
  ::  Exact load-v9 ledger/board closure. Its nonempty version-selection test
  ::  is deliberately absent: a normalized empty predecessor is valid here.
  ?>  &((lte ~(wyt by external) 4) (lte ~(wyt by boards) 4))
  ?>  %+  levy  ~(tap by external)
      |=  [id=@t row=ledger:stead-code-pack-ledger]
      =/  genesis  (~(get by packs) id)
      ?~  genesis  |
      ?.  (valid:stead-code-pack-ledger row u.genesis)  |
      ?~  promotions.row  &
      =/  board  (~(get by boards) id)
      ?~  board  |
      =(promotions.row promotions.u.board)
  ?>  %+  levy  ~(tap by boards)
      |=  [id=@t row=state:stead-code-pack-review-board]
      =/  genesis  (~(get by packs) id)
      ?.  ?=([~ %accepted *] genesis)  |
      ?.  =(destination.row destination.pack.row.u.genesis)  |
      ?.  (valid:stead-code-pack-review-board row)  |
      ?.  (gth ~(wyt by requests.row) 0)  |
      =/  ledger  (~(get by external) id)
      =(promotions.row ?~(ledger ~ promotions.u.ledger))
  =/  entries=(map @t entry:stead-repository-catalog)
    %-  malt
    %+  turn  ~(tap by repos.code)
    |=  [project=@t repository=repository:stead-code-home]
    [project [project '' 1 %inline-sha1-v1 %active & [%legacy]]]
  =/  pending  ~(tap by packs)
  |-
  ?^  pending
    =/  project  p.i.pending
    =/  entry=entry:stead-repository-catalog
      [project '' 1 %external-sha1-pack-v1 %active & [%legacy]]
    $(pending t.pending, entries (~(put by entries) project entry))
  =/  catalog=catalog:stead-repository-catalog  [~(wyt by entries) entries ~]
  ?>  (valid:stead-repository-catalog catalog)
  [catalog code packs external boards]
++  import-legacy
  ::  The normalized team is the caller's exact already-validated old team,
  ::  not an authorization grant. This gate validates the complete Code tuple.
  |=  $:  team=state:stead-team  code=persisted:stead-code-home
          packs=state:stead-code-pack-anchor  external=external  boards=boards
      ==
  ^-  (each imported @tas)
  =/  result  (mule |.((checked team code packs external boards)))
  ?:  ?=(%| -.result)  [%| %invalid-predecessor]
  [%& p.result]
--
