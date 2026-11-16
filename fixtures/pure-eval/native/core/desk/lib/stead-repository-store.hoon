::  PRIVATE repository-keyed retained Code closure. No save/carrier allocation.
::  This is structural validation, not authentic history or present authority.
::  Never project independent repositories through old project-keyed validators.
/+  stead-codec, stead-team, stead-code-home, stead-code-store, stead-code-git-objects, stead-code-credentials, stead-code-upload, stead-code-review-home, stead-code-build-home, stead-code-pack-anchor, stead-code-pack-ledger, stead-code-pack-review-board, stead-repository-catalog, stead-repository-import, stead-repository-authority
|%
+$  state
  $:  catalog=catalog:stead-repository-catalog  code=persisted:stead-code-home
      packs=state:stead-code-pack-anchor  external=external:stead-repository-import
      boards=boards:stead-repository-import
  ==
+$  selected
  [resolved=resolved:stead-repository-catalog repository=repository:stead-code-home]
++  inline-valid
  |=  [destination=scope:stead-code-credentials repo=repository:stead-code-home]
  ^-  ?
  =/  db  data.repo
  ?&  =(1 version.db)  =(destination destination.db)
      ?=(~ pending.db)
      (lte ~(wyt by refs.db) 16)  (lte ~(wyt in protected.repo) 16)
      (levy ~(tap in protected.repo) |=(ref=@t &((lte (met 3 ref) 128) =('refs/heads/' (cut 3 [0 11] ref)) (valid-ref:stead-code-git-objects [(met 3 ref) ref]))))
      (lte (lent (scag 33 journal.db)) 32)
      =(revision.db (lent journal.db))
      =(revision.db ~(wyt by receipts.db))
      (validate-objects:stead-code-home db)
      (validate-journal:stead-code-home db)
  ==
++  checked
  |=  [home=@p team=state:stead-team value=state]
  ^-  ?
  ?>  &(initialized.data.team ?=(^ current.registry.team))
  ?>  &((lte (met 0 home) 128) =(home home.u.current.registry.team))
  ?>  (valid:stead-repository-catalog catalog.value)
  =/  code  code.value
  ?>  ?&  (lte ~(wyt by repos.code) 4)  (lte ~(wyt by packs.value) 4)
          =(~(wyt by entries.catalog.value) (add ~(wyt by repos.code) ~(wyt by packs.value)))
          (lte ~(wyt by reviews.code) 4)  (lte ~(wyt by builds.code) 4)
          (lte ~(wyt by external.value) 4)  (lte ~(wyt by boards.value) 4)
      ==
  ::  Exact root bijection. Every entry retains one root, including tombstones.
  ?>  %+  levy  ~(tap by entries.catalog.value)
      |=  [id=@t row=entry:stead-repository-catalog]
      =/  project  (~(get by projects.data.team) project.row)
      ?~  project  |
      =/  destination=scope:stead-code-credentials  [home project.row id epoch.u.project]
      ?.  (scope-valid:stead-code-credentials destination)  |
      ?:  =(%inline-sha1-v1 profile.row)
        ?:  (~(has by packs.value) id)  |
        =/  repo  (~(get by repos.code) id)
        ?~  repo  |
        ?.  (inline-valid destination u.repo)  |
        ?:  ?=(%legacy -.origin.row)  &
        =/  created  (~(get by creates.catalog.value) request.origin.row)
        ?~  created  |
        =(epoch.destination authority-epoch.u.created)
      ?.  ?&  legacy-alias.row  ?=(%legacy -.origin.row)
              =(id project.row)  !(~(has by repos.code) id)
          ==
        |
      =/  anchor  (~(get by packs.value) id)
      ?~  anchor  |
      &((valid:stead-code-pack-anchor u.anchor) =(destination destination.pack.row.u.anchor))
  ::  Review/build leaves are already repository-scoped; reuse real validators.
  ?>  (levy ~(tap by builds.code) |=([id=@t extras=state:stead-code-build-home] (~(has by reviews.code) id)))
  ?>  %+  levy  ~(tap by reviews.code)
      |=  [id=@t board=state:stead-code-review-home]
      =/  repo  (~(get by repos.code) id)
      ?~  repo  |
      =/  extras  (fall (~(get by builds.code) id) *state:stead-code-build-home)
      &((validate-saved:stead-code-review-home board data.u.repo) (validate-saved:stead-code-build-home board extras data.u.repo))
  ?>  (valid:stead-code-upload uploads.code)
  ?>  %+  levy  ~(tap by uploads.code)
      |=  [key=@t job=upload:stead-code-upload]
      =/  destination  destination.job
      =/  repo  (~(get by repos.code) repository.destination)
      ?~  repo  |
      =(destination destination.data.u.repo)
  ::  External aliases keep the exact old load-v9 joins, in both directions.
  ?>  %+  levy  ~(tap by external.value)
      |=  [id=@t row=ledger:stead-code-pack-ledger]
      =/  genesis  (~(get by packs.value) id)
      ?~  genesis  |
      ?.  (valid:stead-code-pack-ledger row u.genesis)  |
      ?~  promotions.row  &
      =/  board  (~(get by boards.value) id)
      ?~  board  |
      =(promotions.row promotions.u.board)
  ?>  %+  levy  ~(tap by boards.value)
      |=  [id=@t row=state:stead-code-pack-review-board]
      =/  genesis  (~(get by packs.value) id)
      ?.  ?=([~ %accepted *] genesis)  |
      ?.  =(destination.row destination.pack.row.u.genesis)  |
      ?.  (valid:stead-code-pack-review-board row)  |
      ?.  (gth ~(wyt by requests.row) 0)  |
      =/  ledger  (~(get by external.value) id)
      =(promotions.row ?~(ledger ~ promotions.u.ledger))
  &
++  valid
  |=  [home=@p team=state:stead-team value=state]
  ^-  ?
  =/  out  (mule |.((checked home team value)))
  ?:  ?=(%| -.out)  |
  p.out
++  import-legacy
  ::  The original tuple alone reaches the old validators. No pruning/rekeying.
  |=  $:  home=@p  team=state:stead-team  code=persisted:stead-code-home
          packs=state:stead-code-pack-anchor  external=external:stead-repository-import
          boards=boards:stead-repository-import
      ==
  ^-  (each state @tas)
  =/  out  (import-legacy:stead-repository-import team code packs external boards)
  ?:  ?=(%| -.out)  [%| %invalid-predecessor]
  =/  value=state  [catalog.p.out code.p.out packs.p.out external.p.out boards.p.out]
  ?.  (valid home team value)  [%| %invalid-predecessor]
  [%& value]
++  select-inline
  ::  Internal Home value only: never serialize the historical object map.
  ::  Current sender/session is rederived for every call; no queued allowance.
  |=  $:  authority=snapshot:stead-repository-authority  value=state
          source=source:stead-repository-authority  target=ref:stead-repository-catalog
          access=access:stead-repository-catalog  now=@ud
      ==
  ^-  (unit selected)
  ?.  =(repositories.authority catalog.value)  ~
  =/  current  (resolve:stead-repository-authority authority source target access now)
  ?~  current  ~
  ?.  &((valid home.authority db.authority value) =(%inline-sha1-v1 profile.u.current))  ~
  =/  repo  (~(get by repos.code.value) repository.target)
  ?~  repo  ~
  ?.  =(destination.u.current destination.data.u.repo)  ~
  [~ u.current u.repo]
--
