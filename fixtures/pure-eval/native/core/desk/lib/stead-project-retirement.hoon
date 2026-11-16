::  Source-only cross-ship project fence. No operation reopens this project.
/+  stead-codec, stead-core, stead-session, stead-team
=,  stead-codec
|%
+$  intent  [project=@t migration=@t epoch=@ud destination=@p journal-head=@t]
+$  record  [request=intent retired-at=@ud]
+$  ledger  (map @t record)
::  Match the portable journal verifier's limits, including the LF per row.
++  journal-max-rows  6.144
++  journal-max-row-bytes  262.144
++  journal-max-stream-bytes  67.108.864
++  decode
  |=  raw=@t
  ^-  intent
  ?>  (lte (met 3 raw) 2.048)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  fields  p.value
  ?>  (keys fields ~['protocol' 'project_id' 'migration_id' 'authority_epoch' 'destination_home' 'expected_journal_head'])
  ?>  =('stead.project-retire/1' (field fields 'protocol'))
  =/  destination  (need (slaw %p (field fields 'destination_home')))
  ?>  =((scot %p destination) (field fields 'destination_home'))
  :*  (field fields 'project_id')
      (field fields 'migration_id')
      (uint (field fields 'authority_epoch'))
      destination
      (field fields 'expected_journal_head')
  ==
++  head
  |=  [data=state:stead-core project=@t]
  ^-  (unit @t)
  =/  rows  journal.data
  |-
  ?~  rows  ~
  ?:  =(project project.i.rows)  [~ digest.i.rows]
  $(rows t.rows)
++  current
  |=  [data=state:stead-core request=intent]
  ^-  ?
  =/  row  (~(get by projects.data) project.request)
  ?~  row  |
  &((gth epoch.request 0) (lth epoch.request 18.446.744.073.709.551.615) =(epoch.request epoch.u.row) =([~ journal-head.request] (head data project.request)))
++  valid-record
  |=  [home=@p data=state:stead-core row=record]
  ^-  ?
  =/  request  request.row
  ?&  (uuid project.request)
      (uuid migration.request)
      !=(destination.request home)
      (lte (met 0 destination.request) 128)
      (gth retired-at.row 0)
      (lte retired-at.row 18.446.744.073.709.551.615)
      (token-valid:stead-session journal-head.request)
      (current data request)
  ==
++  journal-admissible
  |=  [data=state:stead-core project=@t]
  ^-  ?
  =/  rows  journal.data
  =/  count=@ud  0
  =/  total=@ud  0
  |-
  ?~  rows  (gth count 0)
  ?.  =(project project.i.rows)  $(rows t.rows)
  =/  size  (met 3 bytes.i.rows)
  =/  next-total  (add total +(size))
  ?:  ?|  =(0 size)
          (gth size journal-max-row-bytes)
          (gte count journal-max-rows)
          (gth next-total journal-max-stream-bytes)
      ==  |
  $(rows t.rows, count +(count), total next-total)
++  retire
  |=  [home=@p data=state:stead-core retired=ledger request=intent now=@ud]
  ^-  (unit ledger)
  =/  previous  (~(get by retired) project.request)
  ?^  previous
    ?:  =(request request.u.previous)  [~ retired]
    ~
  ?:  (gte ~(wyt by retired) 16)  ~
  ?.  (valid-record home data [request now])  ~
  ?:  (lien ~(tap by retired) |=([key=@t row=record] =(migration.request migration.request.row)))  ~
  ?.  (journal-admissible data project.request)  ~
  [~ (~(put by retired) project.request [request now])]
++  validate
  |=  [home=@p data=state:stead-core retired=ledger]
  ^-  ?
  ?.  (lte ~(wyt by retired) 16)  |
  =/  rows  ~(tap by retired)
  =/  seen=(set @t)  ~
  |-
  ?~  rows  &
  =/  [key=@t row=record]  i.rows
  ?.  &((valid-record home data row) =(key project.request.row) !(~(has in seen) migration.request.row))  |
  $(rows t.rows, seen (~(put in seen) migration.request.row))
++  status
  |=  [home=@p data=state:stead-core retired=ledger project=@t]
  ^-  (unit @t)
  =/  row  (~(get by projects.data) project)
  ?~  row  ~
  =/  tip  (head data project)
  ?~  tip  ~
  =/  previous  (~(get by retired) project)
  =/  fields=(list [@t @t])
    :~  ['protocol' 'stead.project-retirement-status/1']
        ['home' (scot %p home)]
        ['project_id' project]
        ['authority_epoch' (decimal epoch.u.row)]
        ['journal_head' u.tip]
        ['writer_state' ?~(previous 'active' 'retired')]
    ==
  =?  fields  ?=(^ previous)
    :*  ['migration_id' migration.request.u.previous]
        ['destination_home' (scot %p destination.request.u.previous)]
        ['retired_at_ms' (decimal retired-at.u.previous)]
        fields
    ==
  [~ (canonical (object fields))]
++  apply
  |=  [retired=ledger db=state:stead-team actor=authentication:stead-team cmd=command now=@ud]
  ^-  transition:stead-team
  ?.  (~(has by retired) project.cmd)  (apply-command:stead-team db actor cmd now)
  =/  reason  ?:((allowed:stead-team db actor cmd now) 'authority_retired' 'denied_or_not_found')
  :_  db
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.result/3']
      ['status' 'rejected']
      ['error' reason]
      ['request_id' request.cmd]
      ['canonical_sha256' digest.cmd]
  ==
--
