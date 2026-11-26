::  One home-owned state; pure transitions use trusted Gall context supplied by app.
/+  stead-codec-v1, stead-git
=,  stead-codec-v1
|%
+$  binding
  [principal=@t id=@t kind=@t administrator=? active=? expires=@ud profile=object-map]
+$  project-state  [revision=@ud policy=@ud epoch=@ud data=object-map]
+$  work-state  [revision=@ud data=object-map]
+$  document-state  [revision=@ud container=@t blob=@ux commit=@ux]
+$  grant-state  [project=@t principal=@t role=@t expires=@ud revoked=?]
+$  container-state
  [project=@t owner=@t head=(unit @ux) history=(list @ux) entries=(map @t @ux)]
+$  receipt-state  [digest=@t resource=@t operation=@t command=@t bytes=@t]
+$  state
  $:  initialized=?
      bindings=(map @p binding)
      projects=(map @t project-state)
      works=(map [@t @t] work-state)
      documents=(map [@t @t] document-state)
      grants=(map @t grant-state)
      containers=(map @t container-state)
      objects=(map @ux object:stead-git)
      reachable=(map @ux (set @ux))
      object-bytes=@ud
      journal=(list [project=@t bytes=@t digest=@t])
      receipts=(map [@t @t @t] receipt-state)
  ==
+$  transition  [response=@t next=state]
++  fixture-id
  |=  tail=@t
  ^-  @t
  (cat 3 '019939ba-4000-7000-8000-' tail)
++  profile
  ^-  object-map
  (malt ~[['classification' [%s 'public-synthetic']] ['custody' [%s 'local-disposable']] ['runtime' [%s 'isolated-fake']] ['authentication' [%s 'fake-native/1']]])
++  initialize
  |=  raw=@t
  ^-  state
  ~|  %stead-invalid-fixture
  ?>  =('e693116efbc00b1131714f9eb7077ec678669d4fdb27ddfdce284461e0dffe74' (hex 64 (sha-256l:sha [(met 3 raw) (rev 3 (met 3 raw) raw)])))
  =/  out=state  *state
  =.  initialized.out  &
  =.  bindings.out
    %-  malt
    :~  [~zod [(fixture-id '000000000101') (fixture-id '000000000201') 'service' & & 4.102.444.800.000 profile]]
        [~bus [(fixture-id '000000000102') (fixture-id '000000000202') 'person' | & 4.102.444.800.000 profile]]
        [~nec [(fixture-id '000000000103') (fixture-id '000000000203') 'person' | & 4.102.444.800.000 profile]]
        [~bud [(fixture-id '000000000104') (fixture-id '000000000204') 'person' | & 4.102.444.800.000 profile]]
    ==
  =.  containers.out
    %-  malt
    :~  [(fixture-id '000000000004') [(fixture-id '000000000001') (fixture-id '000000000102') ~ ~ ~]]
        [(fixture-id '000000000007') [(fixture-id '000000000001') (fixture-id '000000000101') ~ ~ ~]]
    ==
  out
++  context
  |=  [db=state sender=@p now=@ud]
  ^-  (unit binding)
  ?.  initialized.db  ~
  =/  found  (~(get by bindings.db) sender)
  ?~  found  ~
  ?.  ?&  active.u.found  (gth expires.u.found now)
          ?|  &(!administrator.u.found =('person' kind.u.found))
              &(administrator.u.found =('service' kind.u.found) =(sender ~zod))
          ==
          =(profile profile.u.found)
      ==
    ~
  found
++  role
  |=  [db=state principal=@t project=@t now=@ud]
  ^-  @ud
  =/  entries  ~(tap by grants.db)
  =/  result=@ud  0
  |-
  ?~  entries  result
  =/  grant  q.i.entries
  ?.  &(!revoked.grant =(principal principal.grant) =(project project.grant) (gth expires.grant now))
    $(entries t.entries)
  =/  rank=@ud
    ?:  =('reader' role.grant)  1
    ?:  =('contributor' role.grant)  2
    ?:  =('maintainer' role.grant)  3
    0
  $(entries t.entries, result (max result rank))
++  container-access
  |=  [db=state actor=binding project=@t container=@t now=@ud]
  ^-  ?
  =/  found  (~(get by containers.db) container)
  ?~  found  |
  ?&  =(project project.u.found)
      =(principal.actor owner.u.found)
      (~(has by projects.db) project)
      (gth (role db principal.actor project now) 0)
  ==
++  allowed
  |=  [db=state actor=binding cmd=command now=@ud]
  ^-  ?
  ?:  =('project.create' operation.cmd)
    ?&  administrator.actor
        =((fixture-id '000000000005') (field payload.cmd 'organization_id'))
        =((fixture-id '000000000006') (field payload.cmd 'owning_team_id'))
    ==
  ?.  (~(has by projects.db) project.cmd)  |
  =/  rank  (role db principal.actor project.cmd now)
  ?:  ?|  =('policy.grant' operation.cmd)  =('policy.revoke' operation.cmd)
      ==
    =/  affected=@t
      ?:  =('policy.grant' operation.cmd)  (field payload.cmd 'role')
      =/  found  (~(get by grants.db) (field payload.cmd 'grant_id'))
      ?~  found  ''
      ?.  =(project.cmd project.u.found)  ''
      role.u.found
    ?&  ?|(administrator.actor =(rank 3))
        ?|  ?&  administrator.actor
                (~(has in (silt ~['reader' 'contributor' 'maintainer'])) affected)
            ==
            (~(has in (silt ~['reader' 'contributor'])) affected)
        ==
    ==
  ?.  (gte rank 2)  |
  ?:  =('document.save' operation.cmd)
    =/  container  (field payload.cmd 'container_id')
    =/  found  (~(get by documents.db) [project.cmd resource.cmd])
    ?&  (container-access db actor project.cmd container now)
        ?~(found & =(container container.u.found))
    ==
  ?:  =('work.update' operation.cmd)
    (~(has by works.db) [project.cmd resource.cmd])
  =('work.create' operation.cmd)
++  error
  |=  name=@t
  ^-  @t
  (canonical (object ~[['protocol' 'stead.result/1'] ['status' 'rejected'] ['error' name]]))
++  revision
  |=  [db=state cmd=command]
  ^-  @ud
  ?:  =('project.create' operation.cmd)
    =/  found  (~(get by projects.db) project.cmd)
    ?~(found 0 revision.u.found)
  ?:  ?|  =('policy.grant' operation.cmd)  =('policy.revoke' operation.cmd)
      ==
    =/  found  (~(got by projects.db) project.cmd)
    policy.found
  ?:  =('document.save' operation.cmd)
    =/  found  (~(get by documents.db) [project.cmd resource.cmd])
    ?~(found 0 revision.u.found)
  =/  found  (~(get by works.db) [project.cmd resource.cmd])
  ?~(found 0 revision.u.found)
++  accept
  |=  [db=state actor=binding cmd=command now=@ud old=@ud new=@ud policy=@ud git=@t]
  ^-  transition
  =/  chain  (skim journal.db |=([project=@t bytes=@t digest=@t] =(project.cmd project)))
  =/  previous  ?~(chain (hex 64 0) digest.i.chain)
  =/  seq  +((lent chain))
  =/  record
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.journal/1']
        ['sequence' (decimal seq)]
        ['previous_digest' previous]
        ['canonical_command' canonical-bytes.cmd]
        ['principal_id' principal.actor]
        ['binding_id' id.actor]
        ['authentication' 'fake-native/1']
        ['authentication_strength' 'synthetic-native-sender']
        ['accepted_at_ms' (decimal now)]
        ['policy_revision' (decimal policy)]
        ['authority_epoch' (decimal epoch.cmd)]
        ['old_revision' (decimal old)]
        ['new_revision' (decimal new)]
        ['git_commit_oid' git]
    ==
  =/  digest  (hash 'stead.journal/1' record)
  =/  receipt
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.receipt/1']
        ['status' 'accepted']
        ['request_id' request.cmd]
        ['canonical_sha256' digest.cmd]
        ['project_id' project.cmd]
        ['resource_id' resource.cmd]
        ['resource_revision' (decimal new)]
        ['authority_epoch' (decimal epoch.cmd)]
        ['policy_revision' (decimal policy)]
        ['journal_sequence' (decimal seq)]
        ['journal_digest' digest]
        ['principal_id' principal.actor]
        ['binding_id' id.actor]
        ['authentication' 'fake-native/1']
        ['authentication_strength' 'synthetic-native-sender']
        ['accepted_at_ms' (decimal now)]
        ['git_commit_oid' git]
    ==
  =.  journal.db  [[project.cmd record digest] journal.db]
  =.  receipts.db  (~(put by receipts.db) [project.cmd principal.actor request.cmd] [digest.cmd resource.cmd operation.cmd canonical-bytes.cmd receipt])
  [receipt db]
++  apply-command
  |=  [db=state sender=@p now=@ud cmd=command]
  ^-  transition
  =/  identity  (context db sender now)
  ?~  identity  [(error 'denied_or_not_found') db]
  =/  actor  u.identity
  ?.  (allowed db actor cmd now)  [(error 'denied_or_not_found') db]
  ?.  (read-scope db actor project.cmd resource.cmd operation.cmd now)
    [(error 'denied_or_not_found') db]
  =/  epo=@ud
    ?:  =('project.create' operation.cmd)  1
    =/  pro  (~(got by projects.db) project.cmd)
    epoch.pro
  ?.  =(epo epoch.cmd)  [(error 'authority_epoch_conflict') db]
  ::  Current authorization and epoch precede access to any old receipt.
  =/  duplicate  (~(get by receipts.db) [project.cmd principal.actor request.cmd])
  ?^  duplicate
    ?.  =(digest.cmd digest.u.duplicate)  [(error 'request_id_reuse') db]
    [bytes.u.duplicate db]
  =/  old  (revision db cmd)
  ?.  =(old expected.cmd)  [(error 'revision_conflict') db]
  ?:  ?|((gte (lent journal.db) 4.096) =(old 18.446.744.073.709.551.615))
    [(error 'capacity_exceeded') db]
  =/  new  +(old)
  =/  pol=@ud
    ?:  =('project.create' operation.cmd)  0
    =/  pro  (~(got by projects.db) project.cmd)
    policy.pro
  ?:  =('project.create' operation.cmd)
    ?:  (gte (lent ~(tap by projects.db)) 16)  [(error 'capacity_exceeded') db]
    ?:  ?|((id-used db project.cmd) (id-used db request.cmd) =(project.cmd request.cmd))
      [(error 'invalid_command') db]
    =.  projects.db  (~(put by projects.db) project.cmd [1 1 1 payload.cmd])
    ::  Reserve the creation request UUID as the explicit creator grant UUID.
    =.  grants.db  (~(put by grants.db) request.cmd [project.cmd principal.actor 'maintainer' expires.actor |])
    (accept db actor cmd now old new pol '')
  ?:  =('policy.grant' operation.cmd)
    =/  gid  (field payload.cmd 'grant_id')
    ?:  (id-used db gid)  [(error 'invalid_command') db]
    =/  pid  (field payload.cmd 'principal_id')
    ?.  (lien ~(tap by bindings.db) |=([ship=@p val=binding] =(pid principal.val)))
      [(error 'invalid_command') db]
    =/  expiry  (uint (field payload.cmd 'expires_at_ms'))
    =/  deadline
      ?:  administrator.actor  expires.actor
      =/  grants
        %+  skim  ~(tap by grants.db)
        |=  [key=@t val=grant-state]
        &(!revoked.val =(project.cmd project.val) =(principal.actor principal.val) =('maintainer' role.val) (gth expires.val now))
      (min expires.actor (roll grants |=([pair=[@t grant-state] limit=@ud] (max limit expires.+.pair))))
    ?.  &((gth expiry now) (lte expiry deadline))
      [(error 'invalid_command') db]
    =/  count  (lent (skim ~(tap by grants.db) |=([key=@t val=grant-state] =(project.cmd project.val))))
    ?:  (gte count 128)  [(error 'capacity_exceeded') db]
    =/  pro  (~(got by projects.db) project.cmd)
    =.  projects.db  (~(put by projects.db) project.cmd pro(policy new))
    =.  grants.db  (~(put by grants.db) gid [project.cmd pid (field payload.cmd 'role') expiry |])
    (accept db actor cmd now old new pol '')
  ?:  =('policy.revoke' operation.cmd)
    =/  gid  (field payload.cmd 'grant_id')
    =/  grant  (~(got by grants.db) gid)
    ?:  revoked.grant  [(error 'invalid_command') db]
    =/  pro  (~(got by projects.db) project.cmd)
    =.  projects.db  (~(put by projects.db) project.cmd pro(policy new))
    =.  grants.db  (~(put by grants.db) gid grant(revoked &))
    (accept db actor cmd now old new pol '')
  ?:  =('document.save' operation.cmd)  (save-document db actor cmd now old new pol)
  ?:  =('work.create' operation.cmd)
    ?:  (id-used db resource.cmd)  [(error 'invalid_command') db]
    =/  count  (lent (skim ~(tap by works.db) |=([key=[project=@t resource=@t] val=work-state] =(project.cmd project.key))))
    ?:  (gte count 128)  [(error 'capacity_exceeded') db]
    =.  works.db  (~(put by works.db) [project.cmd resource.cmd] [new payload.cmd])
    (accept db actor cmd now old new pol '')
  =.  works.db  (~(put by works.db) [project.cmd resource.cmd] [new payload.cmd])
  (accept db actor cmd now old new pol '')
++  save-document
  |=  [db=state actor=binding cmd=command now=@ud old=@ud new=@ud pol=@ud]
  ^-  transition
  =/  markdown  (field payload.cmd 'markdown')
  ?:  &(=(old 0) (id-used db resource.cmd))  [(error 'invalid_command') db]
  =/  header  (rap 3 ~['---' 10 'id: ' resource.cmd 10 'type: page' 10 'state: draft' 10 '---' 10])
  ?.  =(header (cut 3 [0 (met 3 header)] markdown))
    [(error 'invalid_document') db]
  =/  cid  (field payload.cmd 'container_id')
  =/  container  (~(got by containers.db) cid)
  ?:  ?|  (gte (lent history.container) 128)
          &(!(~(has by entries.container) resource.cmd) (gte (lent ~(tap by entries.container)) 32))
      ==
    [(error 'capacity_exceeded') db]
  =/  blob  (make-blob:stead-git [(met 3 markdown) markdown])
  =.  entries.container  (~(put by entries.container) resource.cmd oid.blob)
  =/  tree
    %-  make-tree:stead-git
    (turn ~(tap by entries.container) |=([id=@t oid=@ux] [(cat 3 id '.md') oid]))
  =/  commit  (make-commit:stead-git oid.tree head.container principal.actor (div now 1.000) resource.cmd new)
  ?.  &((immutable-object objects.db blob) (immutable-object objects.db tree) (immutable-object objects.db commit))
    [(error 'invalid_document') db]
  ::  Reject collisions within this staged event as well as against history.
  ?.  &(?|(=(blob tree) !=(oid.blob oid.tree)) ?|(=(blob commit) !=(oid.blob oid.commit)) ?|(=(tree commit) !=(oid.tree oid.commit)))
    [(error 'invalid_document') db]
  =/  objects  (~(put by (~(put by (~(put by objects.db) oid.blob blob)) oid.tree tree)) oid.commit commit)
  =/  total  (roll ~(tap by objects) |=([pair=[@ux object:stead-git] sum=@ud] (add sum length.body.+.pair)))
  ?:  (gth total 8.388.608)  [(error 'capacity_exceeded') db]
  =/  reachable=(set @ux)
    ?~  head.container  ~
    (~(got by reachable.db) u.head.container)
  =.  reachable  (~(uni in reachable) (silt ~[oid.blob oid.tree oid.commit]))
  =.  reachable.db  (~(put by reachable.db) oid.commit reachable)
  =.  objects.db  objects
  =.  object-bytes.db  total
  =.  containers.db  (~(put by containers.db) cid container(head [~ oid.commit], history [oid.commit history.container]))
  =.  documents.db  (~(put by documents.db) [project.cmd resource.cmd] [new cid oid.blob oid.commit])
  (accept db actor cmd now old new pol (oid-text:stead-git oid.commit))
++  read-result
  |=  [project=@t resource=@t revision=@ud data=json]
  ^-  @t
  =/  base  (object ~[['protocol' 'stead.result/1'] ['status' 'read'] ['project_id' project] ['resource_id' resource] ['resource_revision' (decimal revision)]])
  ?>  ?=([%o *] base)
  (canonical [%o (~(put by p.base) 'payload' data)])
++  read
  |=  [db=state sender=@p now=@ud route=path]
  ^-  @t
  =/  denied  (error 'denied_or_not_found')
  =/  identity  (context db sender now)
  ?~  identity  denied
  =/  actor  u.identity
  ?.  ?=([%v1 @ @ *] route)  denied
  =/  project  i.t.t.route
  =/  kind  i.t.route
  ?:  ?=([%v1 %receipt @ @ @ @ ~] route)
    =/  resource  i.t.t.t.route
    =/  operation  i.t.t.t.t.route
    =/  request  i.t.t.t.t.t.route
    ?.  (read-scope db actor project resource operation now)  denied
    =/  receipt  (~(get by receipts.db) [project principal.actor request])
    ?~  receipt  denied
    ?.  &(=(resource resource.u.receipt) =(operation operation.u.receipt))  denied
    ?.  (allowed db actor (decode command.u.receipt) now)  denied
    bytes.u.receipt
  ?.  (~(has by projects.db) project)  denied
  ?.  (gth (role db principal.actor project now) 0)  denied
  ?:  ?=([%v1 %project @ ~] route)
    =/  pro  (~(got by projects.db) project)
    =/  data  (~(put by data.pro) 'policy_revision' [%s (decimal policy.pro)])
    (read-result project project revision.pro [%o data])
  ?:  ?=([%v1 %work @ @ ~] route)
    =/  id  i.t.t.t.route
    =/  found  (~(get by works.db) [project id])
    ?~  found  denied
    (read-result project id revision.u.found [%o data.u.found])
  ?:  ?=([%v1 %document @ @ ~] route)
    =/  id  i.t.t.t.route
    =/  found  (~(get by documents.db) [project id])
    ?~  found  denied
    ?.  (container-access db actor project container.u.found now)  denied
    =/  blob  (~(got by objects.db) blob.u.found)
    (read-result project id revision.u.found (object ~[['container_id' container.u.found] ['markdown' data.body.blob] ['git_commit_oid' (oid-text:stead-git commit.u.found)]]))
  ?:  ?=([%v1 %git @ @ ~] route)
    =/  cid  i.t.t.t.route
    ?.  (container-access db actor project cid now)  denied
    =/  container  (~(got by containers.db) cid)
    ?~  head.container  denied
    =/  reachable  (~(got by reachable.db) u.head.container)
    =/  objects-json
      %-  object
      %+  turn  ~(tap in reachable)
      |=  oid=@ux
      =/  obj  (~(got by objects.db) oid)
      [(oid-text:stead-git oid) kind.obj]
    =/  data  (object ~[['snapshot_commit_oid' (oid-text:stead-git u.head.container)]])
    ?>  ?=([%o *] data)
    (read-result project cid (lent history.container) [%o (~(put by p.data) 'objects' objects-json)])
  ?:  ?=([%v1 %git-object @ @ @ @ ~] route)
    =/  cid  i.t.t.t.route
    ?.  (container-access db actor project cid now)  denied
    =/  container  (~(got by containers.db) cid)
    =/  snapshot  (parse-oid i.t.t.t.t.route)
    =/  oid  (parse-oid i.t.t.t.t.t.route)
    ?~  snapshot  denied
    ?~  oid  denied
    ?.  (lien history.container |=(x=@ux =(x u.snapshot)))  denied
    =/  reach  (~(got by reachable.db) u.snapshot)
    ?.  (~(has in reach) u.oid)  denied
    =/  obj  (~(got by objects.db) u.oid)
    =/  bytes  (hex (mul 2 length.body.obj) (rev 3 length.body.obj data.body.obj))
    (read-result project cid (lent history.container) (object ~[['snapshot_commit_oid' (oid-text:stead-git u.snapshot)] ['oid' (oid-text:stead-git u.oid)] ['kind' kind.obj] ['byte_length' (decimal length.body.obj)] ['hex' bytes]]))
  denied
++  parse-oid
  |=  text=@t
  ^-  (unit @ux)
  ?.  =(40 (met 3 text))  ~
  =/  bytes  (rip 3 text)
  =/  value=@ux  0x0
  |-
  ?~  bytes  (some value)
  =/  c  i.bytes
  =/  digit=(unit @ud)
    ?:  &((gte c 48) (lte c 57))  (some (sub c 48))
    ?:  &((gte c 97) (lte c 102))  (some (sub c 87))
    ~
  ?~  digit  ~
  $(bytes t.bytes, value (add (mul value 16) u.digit))
++  read-scope
  |=  [db=state actor=binding project=@t resource=@t operation=@t now=@ud]
  ^-  ?
  ?:  &(!(~(has by projects.db) project) =('project.create' operation))
    administrator.actor
  ?.  (~(has by projects.db) project)  |
  =/  rank  (role db principal.actor project now)
  ?:  ?|(=('policy.grant' operation) =('policy.revoke' operation))
    ?|(administrator.actor =(rank 3))
  ?.  (gth rank 0)  |
  ?:  =('project.create' operation)  administrator.actor
  ?.  (gte rank 2)  |
  ?:  =('document.save' operation)
    =/  found  (~(get by documents.db) [project resource])
    ?~  found  &
    (container-access db actor project container.u.found now)
  (~(has in (silt ~['work.create' 'work.update'])) operation)
++  id-used
  |=  [db=state id=@t]
  ^-  ?
  ?|  (~(has by projects.db) id)
      (~(has by grants.db) id)
      (~(has by containers.db) id)
      =(id (fixture-id '000000000005'))
      =(id (fixture-id '000000000006'))
      (lien ~(tap by bindings.db) |=([ship=@p val=binding] ?|(=(id principal.val) =(id id.val))))
      (lien ~(tap by works.db) |=([key=[project=@t resource=@t] val=work-state] =(id resource.key)))
      (lien ~(tap by documents.db) |=([key=[project=@t resource=@t] val=document-state] =(id resource.key)))
  ==
++  immutable-object
  |=  [objects=(map @ux object:stead-git) obj=object:stead-git]
  ^-  ?
  =/  old  (~(get by objects) oid.obj)
  ?~(old & =(u.old obj))
--
