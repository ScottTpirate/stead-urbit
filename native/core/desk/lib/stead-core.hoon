::  One home-owned state; pure transitions use trusted Gall context supplied by app.
/+  stead-codec, stead-git, stead-core-v1
=,  stead-codec
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
  ?:  (closed db project.cmd)  |
  =/  rank  (role db principal.actor project.cmd now)
  ?:  ?|  =('policy.grant' operation.cmd)  =('policy.revoke' operation.cmd)
      ==
    =/  affected=@t
      ?:  =('policy.grant' operation.cmd)  (field payload.cmd 'role')
      =/  found  (~(get by grants.db) (scope-key project.cmd (field payload.cmd 'grant_id')))
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
    =/  found  (~(get by documents.db) [project.cmd (scope-key (field payload.cmd 'container_id') resource.cmd)])
    ?&  (container-access db actor project.cmd container now)
        ?~(found & =(container container.u.found))
    ==
  ?:  =('work.update' operation.cmd)
    (~(has by works.db) [project.cmd resource.cmd])
  =('work.create' operation.cmd)
++  error
  |=  name=@t
  ^-  @t
  (canonical (object ~[['protocol' 'stead.result/2'] ['status' 'rejected'] ['error' name]]))
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
    =/  found  (~(get by documents.db) [project.cmd (scope-key (field payload.cmd 'container_id') resource.cmd)])
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
  [(public-receipt [digest.cmd resource.cmd operation.cmd canonical-bytes.cmd receipt]) db]
++  apply-command
  |=  [db=state sender=@p now=@ud cmd=command]
  ^-  transition
  =/  identity  (context db sender now)
  ?~  identity  [(error 'denied_or_not_found') db]
  =/  actor  u.identity
  ?.  (allowed db actor cmd now)  [(error 'denied_or_not_found') db]
  ?.  (read-scope db actor project.cmd resource.cmd operation.cmd (command-container cmd) now)
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
    [(public-receipt u.duplicate) db]
  ?.  =('stead.command/2' protocol.cmd)  [(error 'unsupported_version') db]
  =/  old  (revision db cmd)
  ?.  =(old expected.cmd)  [(error 'revision_conflict') db]
  ?:  ?|  =(old 18.446.744.073.709.551.615)
          ?:(=('policy.revoke' operation.cmd) (gte (security-count db project.cmd) 128) (gte (ordinary-count db) 4.096))
      ==
    [(error 'capacity_exceeded') db]
  =/  new  +(old)
  =/  pol=@ud
    ?:  =('project.create' operation.cmd)  0
    =/  pro  (~(got by projects.db) project.cmd)
    policy.pro
  ?:  =('project.create' operation.cmd)
    ?:  (gte (lent ~(tap by projects.db)) 16)  [(error 'capacity_exceeded') db]
    ::  Existing project allocation is visible only to the explicit org policy
    ::  administrator in this single-org profile. Never inspect other kinds.
    ?:  (~(has by projects.db) project.cmd)  [(error 'invalid_command') db]
    =.  projects.db  (~(put by projects.db) project.cmd [1 1 1 payload.cmd])
    ::  Reserve the creation request UUID as the explicit creator grant UUID.
    =.  grants.db  (~(put by grants.db) (scope-key project.cmd request.cmd) [project.cmd principal.actor 'maintainer' expires.actor |])
    (accept db actor cmd now old new pol '')
  ?:  =('policy.grant' operation.cmd)
    =/  gid  (field payload.cmd 'grant_id')
    ?:  (~(has by grants.db) (scope-key project.cmd gid))  [(error 'invalid_command') db]
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
    =.  grants.db  (~(put by grants.db) (scope-key project.cmd gid) [project.cmd pid (field payload.cmd 'role') expiry |])
    (accept db actor cmd now old new pol '')
  ?:  =('policy.revoke' operation.cmd)
    =/  gid  (field payload.cmd 'grant_id')
    =/  grant  (~(got by grants.db) (scope-key project.cmd gid))
    ?:  revoked.grant  [(error 'invalid_command') db]
    =/  pro  (~(got by projects.db) project.cmd)
    =.  projects.db  (~(put by projects.db) project.cmd pro(policy new))
    =.  grants.db  (~(put by grants.db) (scope-key project.cmd gid) grant(revoked &))
    (accept db actor cmd now old new pol '')
  ?:  =('document.save' operation.cmd)  (save-document db actor cmd now old new pol)
  ?:  =('work.create' operation.cmd)
    ?:  (~(has by works.db) [project.cmd resource.cmd])  [(error 'invalid_command') db]
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
  =.  documents.db  (~(put by documents.db) [project.cmd (scope-key cid resource.cmd)] [new cid oid.blob oid.commit])
  (accept db actor cmd now old new pol (oid-text:stead-git oid.commit))
++  read-result
  |=  [project=@t resource=@t revision=@ud data=json]
  ^-  @t
  =/  base  (object ~[['protocol' 'stead.result/2'] ['status' 'read'] ['project_id' project] ['resource_id' resource] ['resource_revision' (decimal revision)]])
  ?>  ?=([%o *] base)
  (canonical [%o (~(put by p.base) 'payload' data)])
++  read
  |=  [db=state sender=@p now=@ud route=path]
  ^-  @t
  =/  denied  (error 'denied_or_not_found')
  =/  identity  (context db sender now)
  ?~  identity  denied
  =/  actor  u.identity
  ?.  ?=([%v2 @ @ *] route)  denied
  =/  project  i.t.t.route
  =/  kind  i.t.route
  ?:  ?=([%v2 %receipt @ @ @ @ @ ~] route)
    =/  container  i.t.t.t.route
    =/  resource  i.t.t.t.t.route
    =/  operation  i.t.t.t.t.t.route
    =/  request  i.t.t.t.t.t.t.route
    ?.  (read-scope db actor project resource operation container now)  denied
    =/  receipt  (~(get by receipts.db) [project principal.actor request])
    ?~  receipt  denied
    ?.  &(=(resource resource.u.receipt) =(operation operation.u.receipt))  denied
    =/  cmd  (decode command.u.receipt)
    ?.  =(container (command-container cmd))  denied
    ?.  (allowed db actor cmd now)  denied
    (public-receipt u.receipt)
  ?.  (~(has by projects.db) project)  denied
  ?:  (closed db project)  denied
  ?.  (gth (role db principal.actor project now) 0)  denied
  ?:  ?=([%v2 %project @ ~] route)
    =/  pro  (~(got by projects.db) project)
    (read-result project project revision.pro [%o data.pro])
  ?:  ?=([%v2 %work @ @ ~] route)
    =/  id  i.t.t.t.route
    =/  found  (~(get by works.db) [project id])
    ?~  found  denied
    (read-result project id revision.u.found [%o data.u.found])
  ?:  ?=([%v2 %document @ @ @ ~] route)
    =/  cid  i.t.t.t.route
    =/  id  i.t.t.t.t.route
    ?.  (container-access db actor project cid now)  denied
    =/  found  (~(get by documents.db) [project (scope-key cid id)])
    ?~  found  denied
    ?.  (container-access db actor project container.u.found now)  denied
    =/  blob  (~(got by objects.db) blob.u.found)
    (read-result project id revision.u.found (object ~[['container_id' container.u.found] ['markdown' data.body.blob] ['git_commit_oid' (oid-text:stead-git commit.u.found)]]))
  ?:  ?=([%v2 %git @ @ ~] route)
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
  ?:  ?=([%v2 %git-object @ @ @ @ ~] route)
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
  |=  [db=state actor=binding project=@t resource=@t operation=@t container=@t now=@ud]
  ^-  ?
  ?:  &(!(~(has by projects.db) project) =('project.create' operation))
    administrator.actor
  ?.  (~(has by projects.db) project)  |
  ?:  (closed db project)  |
  =/  rank  (role db principal.actor project now)
  ?:  ?|(=('policy.grant' operation) =('policy.revoke' operation))
    ?|(administrator.actor =(rank 3))
  ?.  (gth rank 0)  |
  ?:  =('project.create' operation)  administrator.actor
  ?.  (gte rank 2)  |
  ?:  =('document.save' operation)
    (container-access db actor project container now)
  (~(has in (silt ~['work.create' 'work.update'])) operation)
++  scope-key
  |=  [scope=@t id=@t]
  ^-  @t
  (cat 3 scope (cat 3 '/' id))
++  command-container
  |=  cmd=command
  ^-  @t
  ?:  =('document.save' operation.cmd)  (field payload.cmd 'container_id')
  project.cmd
++  resource-kind
  |=  operation=@t
  ^-  @t
  ?:  =('project.create' operation)  'project'
  ?:  =('document.save' operation)  'document'
  ?:  ?|(=('policy.grant' operation) =('policy.revoke' operation))  'policy'
  'work'
++  public-receipt
  |=  accepted=receipt-state
  ^-  @t
  =/  value  (need (parse-result bytes.accepted))
  ?>  ?=([%o *] value)
  ::  Closed projection: no unknown historical field can become a public field.
  =/  names
    ~['status' 'request_id' 'canonical_sha256' 'project_id' 'resource_id' 'resource_revision' 'authority_epoch' 'principal_id' 'binding_id' 'authentication' 'authentication_strength' 'accepted_at_ms' 'git_commit_oid']
  =/  fields
    %-  malt
    (turn names |=(name=@t [name [%s (field p.value name)]]))
  =.  fields  (~(put by fields) 'protocol' [%s 'stead.receipt/2'])
  =.  fields  (~(put by fields) 'resource_kind' [%s (resource-kind operation.accepted)])
  =/  container
    ?:  =('document.save' operation.accepted)
      (command-container (decode command.accepted))
    ''
  =.  fields  (~(put by fields) 'container_id' [%s container])
  (canonical [%o fields])
++  ordinary-count
  |=  db=state
  ^-  @ud
  %-  lent
  %+  skim  ~(tap by receipts.db)
  |=  [key=[@t @t @t] val=receipt-state]
  !=('policy.revoke' operation.val)
++  security-count
  |=  [db=state project=@t]
  ^-  @ud
  %-  lent
  %+  skim  ~(tap by receipts.db)
  |=  [key=[project-id=@t principal=@t request=@t] val=receipt-state]
  &(=(project project-id.key) =('policy.revoke' operation.val))
++  closed
  |=  [db=state project=@t]
  ^-  ?
  =/  found  (~(get by projects.db) project)
  ?~  found  |
  ?|  (gte (security-count db project) 128)
      (gte policy.u.found 18.446.744.073.709.551.615)
  ==
++  migrate-v1
  |=  old=state:stead-core-v1
  ^-  state
  ::  Exact supported predecessor, not a reset or a current-format roundtrip.
  ?>  (lte (lent journal.old) 4.096)
  ?>  =((lent journal.old) (lent ~(tap by receipts.old)))
  ?>  (lte (lent ~(tap by projects.old)) 16)
  ?>  (lte object-bytes.old 8.388.608)
  ?>  (validate-predecessor old)
  =/  out=state  old
  =.  grants.out
    %-  malt
    %+  turn  ~(tap by grants.old)
    |=  [key=@t val=grant-state]
    [(scope-key project.val key) val]
  =.  documents.out
    %-  malt
    %+  turn  ~(tap by documents.old)
    |=  [key=[project=@t id=@t] val=document-state]
    [[project.key (scope-key container.val id.key)] val]
  out
++  validate-predecessor
  |=  old=state:stead-core-v1
  ^-  ?
  ::  Verification only: never reauthorize history or execute its commands.
  ?.  initialized.old
    =/  pristine=state:stead-core-v1  *state:stead-core-v1
    =(old pristine(initialized |))
  ?>  =((silt (turn ~(tap by containers.old) |=([key=@t val=container-state] key))) (silt ~[(fixture-id '000000000004') (fixture-id '000000000007')]))
  ?>  %+  levy  ~(tap by objects.old)
      |=  [key=@ux val=object:stead-git]
      &(=(key oid.val) =((make-object:stead-git kind.val body.val) val))
  ?>  =((roll ~(tap by objects.old) |=([pair=[@ux object:stead-git] sum=@ud] (add sum length.body.+.pair))) object-bytes.old)
  ?>  (levy ~(tap by containers.old) |=([key=@t val=container-state] &((lte (lent history.val) 128) (lte (lent ~(tap by entries.val)) 32))))
  ?>  %+  levy  ~(tap by projects.old)
      |=  [id=@t val=project-state]
      =/  grants  (skim ~(tap by grants.old) |=([key=@t val=grant-state] =(id project.val)))
      =/  works  (skim ~(tap by works.old) |=([key=[project=@t resource=@t] val=work-state] =(id project.key)))
      &((lte (lent grants) 128) (lte (lent works) 128))
  =/  rows  (flop journal.old)
  =/  heads=(map @t [sequence=@ud digest=@t])  ~
  =/  seen=(set [@t @t @t])  ~
  =/  revoked=(set @t)  ~
  =/  policies=(map @t @ud)  ~
  =/  grants=(map @t grant-state)  ~
  =/  works=(map [@t @t] work-state)  ~
  =/  documents=(map [@t @t] document-state)  ~
  =/  objects=(map @ux object:stead-git)  ~
  =/  reachable=(map @ux (set @ux))  ~
  =/  containers
    %-  malt
    %+  turn  ~(tap by containers.old)
    |=  [key=@t val=container-state]
    ?>  =(project.val (fixture-id '000000000001'))
    ?>  ?|  &(=(key (fixture-id '000000000004')) =(owner.val (fixture-id '000000000102')))
            &(=(key (fixture-id '000000000007')) =(owner.val (fixture-id '000000000101')))
        ==
    [key val(head ~, history ~, entries ~)]
  |-
  ?~  rows
    ?>  =((lent ~(tap in seen)) (lent ~(tap by receipts.old)))
    ?>  (levy ~(tap by grants.old) |=([key=@t val=grant-state] =(revoked.val (~(has in revoked) key))))
    ?>  =((lent ~(tap by policies)) (lent ~(tap by projects.old)))
    ?>  (levy ~(tap by projects.old) |=([id=@t val=project-state] &(=(1 revision.val) =(1 epoch.val) =(policy.val (~(got by policies) id)))))
    ?>  &(=(grants grants.old) =(works works.old) =(documents documents.old) =(objects objects.old) =(reachable reachable.old) =(containers containers.old))
    &
  =/  row  i.rows
  =/  parsed  (need (parse-result bytes.row))
  ?>  ?=([%o *] parsed)
  =/  record  p.parsed
  ?>  =('stead.journal/1' (field record 'protocol'))
  ?>  =(bytes.row (canonical parsed))
  ?>  =(digest.row (hash 'stead.journal/1' bytes.row))
  =/  cmd  (decode (field record 'canonical_command'))
  ?>  =('stead.command/1' protocol.cmd)
  ?>  =(project.row project.cmd)
  =/  key  [project.cmd (field record 'principal_id') request.cmd]
  ?>  !(~(has in seen) key)
  =/  receipt  (~(got by receipts.old) key)
  ?>  &(=(digest.cmd digest.receipt) =(resource.cmd resource.receipt) =(operation.cmd operation.receipt) =(canonical-bytes.cmd command.receipt))
  =/  receipt-json  (need (parse-result bytes.receipt))
  ?>  ?=([%o *] receipt-json)
  =/  receipt-fields  p.receipt-json
  ?>  (keys receipt-fields ~['protocol' 'status' 'request_id' 'canonical_sha256' 'project_id' 'resource_id' 'resource_revision' 'authority_epoch' 'policy_revision' 'journal_sequence' 'journal_digest' 'principal_id' 'binding_id' 'authentication' 'authentication_strength' 'accepted_at_ms' 'git_commit_oid'])
  ?>  =('accepted' (field receipt-fields 'status'))
  ?>  =(bytes.receipt (canonical receipt-json))
  ?>  =('stead.receipt/1' (field receipt-fields 'protocol'))
  ?>  &(=(digest.row (field receipt-fields 'journal_digest')) =(digest.cmd (field receipt-fields 'canonical_sha256')))
  ?>  (levy ~['principal_id' 'binding_id' 'authentication' 'authentication_strength' 'accepted_at_ms' 'policy_revision' 'authority_epoch' 'git_commit_oid'] |=(name=@t =((field record name) (field receipt-fields name))))
  ?>  &(=(project.cmd (field receipt-fields 'project_id')) =(resource.cmd (field receipt-fields 'resource_id')) =(request.cmd (field receipt-fields 'request_id')))
  =/  previous  (~(get by heads) project.cmd)
  =/  seq  ?~(previous 1 +(sequence.u.previous))
  ?>  &(=(seq (uint (field record 'sequence'))) =((decimal seq) (field receipt-fields 'journal_sequence')))
  ?>  =(?~(previous (hex 64 0) digest.u.previous) (field record 'previous_digest'))
  ?>  =((field record 'new_revision') (field receipt-fields 'resource_revision'))
  =/  old-revision  (uint (field record 'old_revision'))
  =/  new-revision  (uint (field record 'new_revision'))
  ?>  &(=(old-revision expected.cmd) =(new-revision +(old-revision)))
  =/  policy  (~(get by policies) project.cmd)
  =.  policies
    ?:  =('project.create' operation.cmd)
      ?>  &(=(~ policy) =(0 old-revision) =('0' (field record 'policy_revision')))
      =/  project  (~(got by projects.old) project.cmd)
      ?>  =(payload.cmd data.project)
      (~(put by policies) project.cmd 1)
    ?>  ?=(^ policy)
    ?>  =(u.policy (uint (field record 'policy_revision')))
    ?:  ?|(=('policy.grant' operation.cmd) =('policy.revoke' operation.cmd))
      ?>  =(u.policy old-revision)
      (~(put by policies) project.cmd new-revision)
    policies
  =.  works
    ?.  ?|(=('work.create' operation.cmd) =('work.update' operation.cmd))  works
    =/  prior  (~(get by works) [project.cmd resource.cmd])
    ?>  =(old-revision ?~(prior 0 revision.u.prior))
    (~(put by works) [project.cmd resource.cmd] [new-revision payload.cmd])
  =.  grants
    ?:  =('project.create' operation.cmd)
      ?>  !(~(has by grants) request.cmd)
      =/  original  (~(got by grants.old) request.cmd)
      ::  Creator expiry was implicit in v1 and is not a journal field. Preserve
      ::  the bounded existing value; do not infer it from today's binding.
      ?>  &((gth expires.original (uint (field record 'accepted_at_ms'))) (lte expires.original 18.446.744.073.709.551.615))
      (~(put by grants) request.cmd [project.cmd (field record 'principal_id') 'maintainer' expires.original |])
    ?:  =('policy.grant' operation.cmd)
      =/  gid  (field payload.cmd 'grant_id')
      ?>  !(~(has by grants) gid)
      (~(put by grants) gid [project.cmd (field payload.cmd 'principal_id') (field payload.cmd 'role') (uint (field payload.cmd 'expires_at_ms')) |])
    ?:  =('policy.revoke' operation.cmd)
      =/  gid  (field payload.cmd 'grant_id')
      =/  prior  (~(got by grants) gid)
      ?>  &(=(project.cmd project.prior) !revoked.prior)
      (~(put by grants) gid prior(revoked &))
    grants
  =/  projected
    ?.  =('document.save' operation.cmd)  [documents containers objects reachable]
    =/  cid  (field payload.cmd 'container_id')
    =/  container  (~(got by containers) cid)
    ?>  &(=(project.cmd project.container) =(owner.container (field record 'principal_id')))
    =/  prior  (~(get by documents) [project.cmd resource.cmd])
    ?>  =(old-revision ?~(prior 0 revision.u.prior))
    =/  markdown  (field payload.cmd 'markdown')
    =/  blob  (make-blob:stead-git [(met 3 markdown) markdown])
    =.  entries.container  (~(put by entries.container) resource.cmd oid.blob)
    =/  tree  (make-tree:stead-git (turn ~(tap by entries.container) |=([id=@t oid=@ux] [(cat 3 id '.md') oid])))
    =/  commit  (make-commit:stead-git oid.tree head.container (field record 'principal_id') (div (uint (field record 'accepted_at_ms')) 1.000) resource.cmd new-revision)
    ?>  =((oid-text:stead-git oid.commit) (field record 'git_commit_oid'))
    =/  reach  ?~(head.container *(set @ux) (~(got by reachable) u.head.container))
    =.  reach  (~(uni in reach) (silt ~[oid.blob oid.tree oid.commit]))
    :*  (~(put by documents) [project.cmd resource.cmd] [new-revision cid oid.blob oid.commit])
        (~(put by containers) cid container(head [~ oid.commit], history [oid.commit history.container]))
        (~(put by (~(put by (~(put by objects) oid.blob blob)) oid.tree tree)) oid.commit commit)
        (~(put by reachable) oid.commit reach)
    ==
  =.  documents  -.projected
  =.  containers  +<.projected
  =.  objects  +>-.projected
  =.  reachable  +>+.projected
  =.  revoked
    ?:  =('policy.revoke' operation.cmd)
      =/  gid  (field payload.cmd 'grant_id')
      ?>  !(~(has in revoked) gid)
      (~(put in revoked) gid)
    revoked
  $(rows t.rows, heads (~(put by heads) project.cmd [seq digest.row]), seen (~(put in seen) key))
++  immutable-object
  |=  [objects=(map @ux object:stead-git) obj=object:stead-git]
  ^-  ?
  =/  old  (~(get by objects) oid.obj)
  ?~(old & =(u.old obj))
--
