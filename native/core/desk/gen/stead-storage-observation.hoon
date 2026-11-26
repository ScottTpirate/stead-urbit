::  T06 read-only bounded counters from an actually suspended disposable Home.
::  No noun input, restoration, authored state or application mutation.
/+  stead-team, stead-core, stead-codec
:-  %say
|=  [[now=@da eny=@uvJ bec=beak] ~ ~]
:-  %noun
?>  =(~zod p.bec)
?>  .^(? %j /(scot %p p.bec)/fake/(scot %da now))
?>  =(%.n .^(? %gu /=stead-home=/$))
?>  =(%base .^(desk %gd /=stead-home=/$))
=/  egg=egg-any:gall  .^(egg-any:gall %gv /=stead-home=/$)
?>  ?=([%20 %live *] egg)
=/  saved=vase  +.old-state.egg
=/  retained
  !<  [%stead-home %3 team=[db=state:stead-team projection=*]]
  saved
=/  db  db.team.retained
?>  ?=(^ current.registry.db)
?>  ?&  =('local-disposable' custody.u.current.registry.db)
        =('isolated-fake' runtime.u.current.registry.db)
    ==
=/  comments
  %+  roll  ~(tap by works.data.db)
  |=  [entry=[key=[project=@t id=@t] row=work-state:stead-core] total=@ud]
  (add total (lent (discussion:stead-team data.row.entry)))
^-  @ux
^-  @
%-  canonical:stead-codec
%-  object:stead-codec
:~  ['protocol' 'stead.storage-observation/1']
    ['saved_version' '3']
    ['vase_bytes' (decimal:stead-codec (met 3 (jam saved)))]
    ['payload_bytes' (decimal:stead-codec (met 3 (jam q.saved)))]
    ['journal_bytes' (decimal:stead-codec (met 3 (jam journal.data.db)))]
    ['receipt_bytes' (decimal:stead-codec (met 3 (jam receipts.data.db)))]
    ['object_bytes' (decimal:stead-codec object-bytes.data.db)]
    ['objects' (decimal:stead-codec (lent ~(tap by objects.data.db)))]
    ['projects' (decimal:stead-codec (lent ~(tap by projects.data.db)))]
    ['work_items' (decimal:stead-codec (lent ~(tap by works.data.db)))]
    ['documents' (decimal:stead-codec (lent ~(tap by documents.data.db)))]
    ['comments' (decimal:stead-codec comments)]
    ['journal_events' (decimal:stead-codec (lent journal.data.db)))]
    ['receipts' (decimal:stead-codec (lent ~(tap by receipts.data.db)))]
    ['saved_vase_sha256' (hex:stead-codec 64 (shax (jam saved)))]
==
