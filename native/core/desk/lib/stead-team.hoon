::  Configured-team authority. All external paths must call these same gates.
/+  stead-codec, stead-core, stead-git, stead-session, stead-team-config, stead-team-codec
=,  stead-codec
|%
+$  authentication
  $:  identity=actor:stead-session  method=@t  strength=@t  audit=@t
      expires=@ud  home=@p  organization=@t  team=@t  runtime=@t
  ==
+$  box  [project=@t owner=@t visibility=@t title=@t]
+$  link  [revision=@ud data=object-map]
+$  state
  $:  registry=registry:stead-team-config  data=state:stead-core
      boxes=(map @t box)  tombs=(set [@t @t @t @t])
      links=(map [@t @t] link)  generations=(map [@t @t] @ud)
  ==
+$  transition  [response=@t next=state]
++  empty
  ^-  state
  =/  db=state  *state
  db(data data.db(initialized |))
++  configure
  |=  [db=state raw=@t home=@p now=@ud]
  ^-  state
  ?>  ?~  current.registry.db
        =(empty db)
      &
  =/  next  (decode:stead-team-config raw registry.db home now)
  db(registry next, data data.db(initialized &))
++  native-context
  |=  [db=state sender=@p now=@ud]
  ^-  (unit authentication)
  =/  who  (identity:stead-team-config registry.db sender now)
  ?~  who  ~
  =/  config  (need current.registry.db)
  =/  actor  identity.u.who
  (some [actor 'native-sender/1' 'native-sender' '' expires.actor home.config organization.config team.config runtime.config])
++  browser-context
  |=  [db=state session=session:stead-session now=@ud]
  ^-  (unit authentication)
  =/  native  (native-context db ship.identity.session now)
  ?~  native  ~
  =/  config  (need current.registry.db)
  ?.  ?&  (same-actor:stead-session identity.session identity.u.native)
          =(home.session home.config)  =(origin.session origin.config)
          (gth expires.session now)  (lte expires.session expires.u.native)
          (token-valid:stead-session audit.session)
      ==
    ~
  (some u.native(method 'native-approved-browser/1', strength 'native-approved-browser', audit audit.session, expires expires.session))
++  current
  |=  [db=state actor=authentication now=@ud]
  ^-  ?
  =/  fresh  (native-context db ship.identity.actor now)
  ?~  fresh  |
  ?&  =(identity.actor identity.u.fresh)
      =(home.actor home.u.fresh)  =(organization.actor organization.u.fresh)
      =(team.actor team.u.fresh)  =(runtime.actor runtime.u.fresh)
      (gth expires.actor now)  (lte expires.actor expires.u.fresh)
      ?|  =(actor u.fresh)
          ?&  =('native-approved-browser/1' method.actor)
              =('native-approved-browser' strength.actor)
              (token-valid:stead-session audit.actor)
          ==
      ==
  ==
++  role
  |=  [db=state actor=authentication project=@t now=@ud]
  ^-  @ud
  ?.  (current db actor now)  0
  ?.  (~(has by projects.data.db) project)  0
  ?:  (closed:stead-core data.db project)  0
  (role:stead-core data.db principal.identity.actor project now)
++  box-access
  |=  [db=state actor=authentication project=@t container=@t now=@ud]
  ^-  ?
  ?.  (gth (role db actor project now) 0)  |
  =/  found  (~(get by boxes.db) container)
  ?~  found  |
  ?&  =(project project.u.found)
      ?|  =('shared' visibility.u.found)
          &(=('private' visibility.u.found) =(principal.identity.actor owner.u.found))
      ==
  ==
++  subject
  |=  [db=state actor=authentication project=@t kind=@t container=@t id=@t now=@ud]
  ^-  ?
  ?.  (gth (role db actor project now) 0)  |
  ?:  (~(has in tombs.db) [project kind container id])  |
  ?:  =('project' kind)  =(project id)
  ?:  =('work' kind)  &(=('' container) (~(has by works.data.db) [project id]))
  ?:  =('container' kind)  (box-access db actor project id now)
  ?:  =('document' kind)
    &((box-access db actor project container now) (~(has by documents.data.db) [project (scope-key:stead-core container id)]))
  ?:  =('relation' kind)
    =/  found  (~(get by links.db) [project id])
    ?~  found  |
    (link-access db actor project data.u.found now)
  |
++  link-access
  |=  [db=state actor=authentication project=@t payload=object-map now=@ud]
  ^-  ?
  ?&  (subject db actor project (field payload 'source_kind') (field payload 'source_container_id') (field payload 'source_id') now)
      (subject db actor project (field payload 'target_kind') (field payload 'target_container_id') (field payload 'target_id') now)
  ==
++  allowed
  |=  [db=state actor=authentication cmd=command now=@ud]
  ^-  ?
  ?.  (current db actor now)  |
  =/  config  (need current.registry.db)
  ?:  =('project.create' operation.cmd)
    ?&  (~(has in creators.config) principal.identity.actor)
        ?|  !(~(has by projects.data.db) project.cmd)
            (gth (role db actor project.cmd now) 0)
        ==
        =(organization.config (field payload.cmd 'organization_id'))
        =(team.config (field payload.cmd 'owning_team_id'))
    ==
  =/  rank  (role db actor project.cmd now)
  ?.  (gte rank 2)  |
  ?:  =('policy.grant' operation.cmd)  =(rank 3)
  ?:  =('policy.revoke' operation.cmd)
    &(=(rank 3) (~(has by grants.data.db) (scope-key:stead-core project.cmd (field payload.cmd 'grant_id'))))
  ?:  =('container.create' operation.cmd)
    ?|(=('private' (field payload.cmd 'visibility')) =(rank 3))
  ?:  =('work.create' operation.cmd)  &
  ?:  =('work.update' operation.cmd)
    (subject db actor project.cmd 'work' '' resource.cmd now)
  ?:  =('work.delete' operation.cmd)
    (~(has by works.data.db) [project.cmd resource.cmd])
  ?:  =('relation.create' operation.cmd)
    (link-access db actor project.cmd payload.cmd now)
  ?:  =('relation.delete' operation.cmd)
    =/  found  (~(get by links.db) [project.cmd resource.cmd])
    ?~  found  |
    (link-access db actor project.cmd data.u.found now)
  =/  container  (container:stead-team-codec cmd)
  ?.  (box-access db actor project.cmd container now)  |
  ?:  =('document.publish' operation.cmd)
    =/  source  (field payload.cmd 'source_container_id')
    =/  from  (~(get by boxes.db) source)
    ?~  from  |
    =/  destination  (~(got by boxes.db) container)
    ?&  =(project.cmd (field payload.cmd 'source_project_id'))
        =('private' visibility.u.from)  =(principal.identity.actor owner.u.from)
        =('shared' visibility.destination)
        (subject db actor project.cmd 'document' source (field payload.cmd 'source_document_id') now)
    ==
  ?:  =('document.delete' operation.cmd)
    (~(has by documents.data.db) [project.cmd (scope-key:stead-core container resource.cmd)])
  &(=('document.save' operation.cmd) !(~(has in tombs.db) [project.cmd 'document' container resource.cmd]))
++  error
  |=  name=@t
  ^-  @t
  (canonical (object ~[['protocol' 'stead.result/3'] ['status' 'rejected'] ['error' name]]))
++  revision
  |=  [db=state cmd=command]
  ^-  @ud
  =/  kind  (kind:stead-team-codec operation.cmd)
  ?:  =('project' kind)
    =/  row  (~(get by projects.data.db) project.cmd)
    ?~(row 0 revision.u.row)
  ?:  =('policy' kind)  policy:(~(got by projects.data.db) project.cmd)
  ?:  =('container' kind)
    ?:  (~(has by boxes.db) resource.cmd)  1
    0
  ?:  =('document' kind)
    =/  row  (~(get by documents.data.db) [project.cmd (scope-key:stead-core (container:stead-team-codec cmd) resource.cmd)])
    ?~(row 0 revision.u.row)
  ?:  =('relation' kind)
    =/  row  (~(get by links.db) [project.cmd resource.cmd])
    ?~(row 0 revision.u.row)
  =/  row  (~(get by works.data.db) [project.cmd resource.cmd])
  ?~(row 0 revision.u.row)
++  event-count
  |=  [db=state project=@t security=?]
  ^-  @ud
  %-  lent
  %+  skim  ~(tap by receipts.data.db)
  |=  [key=[project=@t principal=@t request=@t] val=receipt-state:stead-core]
  &(?:(security =(project project.key) &) =(security =('policy.revoke' operation.val)))
++  actor-json
  |=  actor=actor:stead-session
  ^-  @t
  %-  canonical
  %-  object
  :~  ['identity_ship' (scot %p ship.actor)]  ['principal_id' principal.actor]
      ['binding_id' binding.actor]  ['binding_revision' (decimal revision.actor)]
      ['binding_expires_at_ms' (decimal expires.actor)]
  ==
++  decode-actor
  |=  raw=@t
  ^-  actor:stead-session
  ?>  (lte (met 3 raw) 1.024)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['identity_ship' 'principal_id' 'binding_id' 'binding_revision' 'binding_expires_at_ms'])
  ?>  =(raw (canonical value))
  =/  ship  (need (slaw %p (field obj 'identity_ship')))
  ?>  &((lte (met 0 ship) 128) =((scot %p ship) (field obj 'identity_ship')))
  =/  actor=actor:stead-session
    [ship (field obj 'principal_id') (field obj 'binding_id') (uint (field obj 'binding_revision')) & (uint (field obj 'binding_expires_at_ms'))]
  ?>  (live:stead-session actor 0)
  actor
++  authentication-json
  |=  actor=authentication
  ^-  @t
  %-  canonical
  %-  object
  :~  ['identity' (actor-json identity.actor)]  ['authentication' method.actor]
      ['authentication_strength' strength.actor]  ['session_audit_id' audit.actor]
      ['credential_expires_at_ms' (decimal expires.actor)]  ['home' (scot %p home.actor)]
      ['organization_id' organization.actor]  ['team_id' team.actor]  ['runtime' runtime.actor]
  ==
++  decode-authentication
  |=  raw=@t
  ^-  authentication
  ?>  (lte (met 3 raw) 4.096)
  =/  value  (need (parse-result raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['identity' 'authentication' 'authentication_strength' 'session_audit_id' 'credential_expires_at_ms' 'home' 'organization_id' 'team_id' 'runtime'])
  ?>  =(raw (canonical value))
  =/  identity  (decode-actor (field obj 'identity'))
  =/  home  (need (slaw %p (field obj 'home')))
  ?>  &((lte (met 0 home) 128) !=(home ship.identity) =((scot %p home) (field obj 'home')))
  =/  actor=authentication
    [identity (field obj 'authentication') (field obj 'authentication_strength') (field obj 'session_audit_id') (uint (field obj 'credential_expires_at_ms')) home (field obj 'organization_id') (field obj 'team_id') (field obj 'runtime')]
  ?>  &((uuid organization.actor) (uuid team.actor) =('isolated-fake' runtime.actor))
  ?>  &((gth expires.actor 0) (lte expires.actor expires.identity))
  ?>  ?|  &(=('native-sender/1' method.actor) =('native-sender' strength.actor) =('' audit.actor) =(expires.actor expires.identity))
          &(=('native-approved-browser/1' method.actor) =('native-approved-browser' strength.actor) (token-valid:stead-session audit.actor))
      ==
  actor
++  grant-target
  |=  [db=state cmd=command now=@ud]
  ^-  @t
  ?.  =('policy.grant' operation.cmd)  ''
  =/  config  (need current.registry.db)
  =/  targets
    %+  skim  ~(tap by members.config)
    |=  [ship=@p val=member:stead-team-config]
    &(=((field payload.cmd 'principal_id') principal.identity.val) (live:stead-session identity.val now))
  ?>  ?=(^ targets)
  ?>  ?=(~ t.targets)
  (actor-json identity.q.i.targets)
++  accept
  |=  [db=state actor=authentication cmd=command now=@ud old=@ud new=@ud git=@t]
  ^-  transition
  =/  rows  (skim journal.data.db |=([project=@t bytes=@t digest=@t] =(project project.cmd)))
  =/  previous  ?~(rows (hex 64 0) digest.i.rows)
  =/  sequence  +((lent rows))
  =/  container  (container:stead-team-codec cmd)
  =/  receipt
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.receipt/3']  ['status' 'accepted']
        ['request_id' request.cmd]  ['canonical_sha256' digest.cmd]
        ['project_id' project.cmd]  ['resource_id' resource.cmd]
        ['resource_kind' (kind:stead-team-codec operation.cmd)]
        ['container_id' container]  ['resource_revision' (decimal new)]
        ['authority_epoch' (decimal epoch.cmd)]  ['operation' operation.cmd]
        ['principal_id' principal.identity.actor]  ['binding_id' binding.identity.actor]
        ['binding_revision' (decimal revision.identity.actor)]  ['identity_ship' (scot %p ship.identity.actor)]
        ['authentication' method.actor]  ['authentication_strength' strength.actor]
        ['session_audit_id' audit.actor]  ['runtime' runtime.actor]
        ['accepted_at_ms' (decimal now)]  ['git_commit_oid' git]
    ==
  =/  record
    %-  canonical
    %-  object
    :~  ['protocol' 'stead.journal/3']  ['sequence' (decimal sequence)]
        ['previous_digest' previous]  ['canonical_command' canonical-bytes.cmd]
        ['receipt' receipt]  ['old_revision' (decimal old)]  ['new_revision' (decimal new)]
        ['authentication_context' (authentication-json actor)]
        ['grant_target' (grant-target db cmd now)]
    ==
  ?>  (lte (met 3 record) 262.144)
  =/  digest  (hash 'stead.journal/3' record)
  =/  data  data.db
  =.  journal.data  [[project.cmd record digest] journal.data]
  =.  receipts.data  (~(put by receipts.data) [project.cmd principal.identity.actor request.cmd] [digest.cmd resource.cmd operation.cmd canonical-bytes.cmd receipt])
  =/  scopes  ~(tap in (changed-scopes db(data data) cmd))
  =/  generations  generations.db
  |-
  ?~  scopes  [receipt db(data data, generations generations)]
  =/  old-generation  (~(get by generations) [project.cmd i.scopes])
  =/  generation  ?~(old-generation 1 +(u.old-generation))
  ?>  (lte generation 18.446.744.073.709.551.615)
  $(scopes t.scopes, generations (~(put by generations) [project.cmd i.scopes] generation))
++  link-scopes
  |=  [db=state payload=object-map]
  ^-  (set @t)
  =/  containers=(list @t)  ~[(field payload 'source_container_id') (field payload 'target_container_id')]
  =/  private=(set @t)  ~
  |-
  ?~  containers  ?~(private (silt ~['']) private)
  =/  box  (~(get by boxes.db) i.containers)
  =?  private  &(?=(^ box) =('private' visibility.u.box))
    (~(put in private) i.containers)
  $(containers t.containers)
++  changed-scopes
  |=  [db=state cmd=command]
  ^-  (set @t)
  ?:  =('policy.grant' operation.cmd)
    (silt ~[(cat 3 'access:' (field payload.cmd 'principal_id'))])
  ?:  =('policy.revoke' operation.cmd)
    =/  grant  (~(got by grants.data.db) (scope-key:stead-core project.cmd (field payload.cmd 'grant_id')))
    (silt ~[(cat 3 'access:' principal.grant)])
  =/  kind  (kind:stead-team-codec operation.cmd)
  ?:  =('relation' kind)
    =/  link  (~(got by links.db) [project.cmd resource.cmd])
    (link-scopes db data.link)
  =/  container  (container:stead-team-codec cmd)
  =/  scope=@t
    ?:  =('' container)  ''
    =/  box  (~(got by boxes.db) container)
    ?:(=('private' visibility.box) container '')
  =/  scopes  (silt ~[scope])
  ?.  ?|(=('work' kind) =('document' kind))  scopes
  =/  links  ~(tap by links.db)
  |-
  ?~  links  scopes
  =/  row  q.i.links
  =/  key  p.i.links
  ?.  &(=(project.cmd -.key) !(~(has in tombs.db) [project.cmd 'relation' '' +.key]))
    $(links t.links)
  =/  source
    &(=(kind (field data.row 'source_kind')) =(resource.cmd (field data.row 'source_id')) =(container (field data.row 'source_container_id')))
  =/  target
    &(=(kind (field data.row 'target_kind')) =(resource.cmd (field data.row 'target_id')) =(container (field data.row 'target_container_id')))
  ?.  ?|(source target)  $(links t.links)
  $(links t.links, scopes (~(uni in scopes) (link-scopes db data.row)))
++  apply-command
  |=  [db=state actor=authentication cmd=command now=@ud]
  ^-  transition
  =/  result  (evaluate db actor cmd now)
  =/  parsed  (need (parse-result response.result))
  ?>  ?=([%o *] parsed)
  ?.  =('rejected' (field p.parsed 'status'))  result
  result(response (canonical [%o (~(put by (~(put by p.parsed) 'request_id' [%s request.cmd])) 'canonical_sha256' [%s digest.cmd])]))
++  evaluate
  |=  [db=state actor=authentication cmd=command now=@ud]
  ^-  transition
  ?.  =('stead.command/3' protocol.cmd)  [(error 'unsupported_version') db]
  ?.  (allowed db actor cmd now)  [(error 'denied_or_not_found') db]
  =/  epoch=@ud
    ?:  =('project.create' operation.cmd)  1
    epoch:(~(got by projects.data.db) project.cmd)
  ?.  =(epoch epoch.cmd)  [(error 'authority_epoch_conflict') db]
  =/  previous  (~(get by receipts.data.db) [project.cmd principal.identity.actor request.cmd])
  ?^  previous
    ?.  =(digest.cmd digest.u.previous)  [(error 'request_id_reuse') db]
    [bytes.u.previous db]
  =/  old  (revision db cmd)
  ?.  =(old expected.cmd)  [(error 'revision_conflict') db]
  ?:  ?|  =(old 18.446.744.073.709.551.615)
          (gte (event-count db project.cmd =('policy.revoke' operation.cmd)) ?:(=('policy.revoke' operation.cmd) 128 4.096))
      ==
    [(error 'capacity_exceeded') db]
  =/  new  +(old)
  =/  data  data.db
  =/  kind  (kind:stead-team-codec operation.cmd)
  ?:  =('project.create' operation.cmd)
    ?:  (gte (lent ~(tap by projects.data)) 16)  [(error 'capacity_exceeded') db]
    ?:  (~(has by projects.data) project.cmd)  [(error 'invalid_command') db]
    =.  projects.data  (~(put by projects.data) project.cmd [1 1 1 payload.cmd])
    =.  grants.data  (~(put by grants.data) (scope-key:stead-core project.cmd request.cmd) [project.cmd principal.identity.actor 'maintainer' expires.identity.actor |])
    (accept db(data data) actor cmd now old new '')
  ?:  =('policy.grant' operation.cmd)
    =/  id  (field payload.cmd 'grant_id')
    =/  principal  (field payload.cmd 'principal_id')
    =/  config  (need current.registry.db)
    ?.  (lien ~(tap by members.config) |=([ship=@p val=member:stead-team-config] &(=(principal principal.identity.val) (live:stead-session identity.val now))))
      [(error 'invalid_command') db]
    ?:  (~(has by grants.data) (scope-key:stead-core project.cmd id))  [(error 'invalid_command') db]
    =/  own
      %+  skim  ~(tap by grants.data)
      |=  [key=@t val=grant-state:stead-core]
      &(!revoked.val =(project.cmd project.val) =(principal.identity.actor principal.val) =('maintainer' role.val) (gth expires.val now))
    =/  expiry  (uint (field payload.cmd 'expires_at_ms'))
    =/  deadline  (min expires.identity.actor (roll own |=([pair=[@t grant-state:stead-core] limit=@ud] (max limit expires.+.pair))))
    ?.  &((gth expiry now) (lte expiry deadline))  [(error 'invalid_command') db]
    ?:  (gte (lent (skim ~(tap by grants.data) |=([key=@t val=grant-state:stead-core] =(project.cmd project.val)))) 128)
      [(error 'capacity_exceeded') db]
    =/  project  (~(got by projects.data) project.cmd)
    =.  projects.data  (~(put by projects.data) project.cmd project(policy new))
    =.  grants.data  (~(put by grants.data) (scope-key:stead-core project.cmd id) [project.cmd principal (field payload.cmd 'role') expiry |])
    (accept db(data data) actor cmd now old new '')
  ?:  =('policy.revoke' operation.cmd)
    =/  id  (scope-key:stead-core project.cmd (field payload.cmd 'grant_id'))
    =/  grant  (~(got by grants.data) id)
    ?:  revoked.grant  [(error 'invalid_command') db]
    =/  project  (~(got by projects.data) project.cmd)
    =.  projects.data  (~(put by projects.data) project.cmd project(policy new))
    =.  grants.data  (~(put by grants.data) id grant(revoked &))
    (accept db(data data) actor cmd now old new '')
  ?:  =('container.create' operation.cmd)
    ?:  (~(has by boxes.db) resource.cmd)  [(error 'denied_or_not_found') db]
    ?:  (gte (lent (skim ~(tap by boxes.db) |=([id=@t val=box] =(project.cmd project.val)))) 32)
      [(error 'capacity_exceeded') db]
    =.  containers.data  (~(put by containers.data) resource.cmd [project.cmd principal.identity.actor ~ ~ ~])
    =/  next  db(data data, boxes (~(put by boxes.db) resource.cmd [project.cmd principal.identity.actor (field payload.cmd 'visibility') (field payload.cmd 'title')]))
    (accept next actor cmd now old new '')
  ?:  =('work' kind)
    ?:  =('work.create' operation.cmd)
      ?:  (~(has by works.data) [project.cmd resource.cmd])  [(error 'invalid_command') db]
      ?:  (gte (lent (skim ~(tap by works.data) |=([key=[project=@t resource=@t] val=work-state:stead-core] =(project.cmd project.key)))) 128)
        [(error 'capacity_exceeded') db]
      =.  works.data  (~(put by works.data) [project.cmd resource.cmd] [new payload.cmd])
      (accept db(data data) actor cmd now old new '')
    ?:  =('work.update' operation.cmd)
      =.  works.data  (~(put by works.data) [project.cmd resource.cmd] [new payload.cmd])
      (accept db(data data) actor cmd now old new '')
    ?:  (~(has in tombs.db) [project.cmd 'work' '' resource.cmd])  [(error 'invalid_command') db]
    =/  row  (~(got by works.data) [project.cmd resource.cmd])
    =.  works.data  (~(put by works.data) [project.cmd resource.cmd] row(revision new))
    (accept db(data data, tombs (~(put in tombs.db) [project.cmd 'work' '' resource.cmd])) actor cmd now old new '')
  ?:  =('relation' kind)
    ?:  =('relation.create' operation.cmd)
      ?:  (~(has by links.db) [project.cmd resource.cmd])  [(error 'invalid_command') db]
      ?:  (gte (lent (skim ~(tap by links.db) |=([key=[project=@t id=@t] val=link] =(project.cmd project.key)))) 256)
        [(error 'capacity_exceeded') db]
      (accept db(links (~(put by links.db) [project.cmd resource.cmd] [new payload.cmd])) actor cmd now old new '')
    ?:  (~(has in tombs.db) [project.cmd 'relation' '' resource.cmd])  [(error 'invalid_command') db]
    =/  row  (~(got by links.db) [project.cmd resource.cmd])
    =/  next  db(links (~(put by links.db) [project.cmd resource.cmd] row(revision new)), tombs (~(put in tombs.db) [project.cmd 'relation' '' resource.cmd]))
    (accept next actor cmd now old new '')
  (document-command db actor cmd now old new)
++  header
  |=  [id=@t status=@t]
  ^-  @t
  (rap 3 ~['---' 10 'id: ' id 10 'type: page' 10 'state: ' status 10 '---' 10])
++  document-command
  |=  [db=state actor=authentication cmd=command now=@ud old=@ud new=@ud]
  ^-  transition
  =/  cid  (container:stead-team-codec cmd)
  =/  box  (~(got by boxes.db) cid)
  =/  container  (~(got by containers.data.db) cid)
  =/  deleting  =('document.delete' operation.cmd)
  ?:  (gte (lent history.container) 128)  [(error 'capacity_exceeded') db]
  ?:  &(!deleting !(~(has by entries.container) resource.cmd) (gte (lent ~(tap by entries.container)) 32))
    [(error 'capacity_exceeded') db]
  =/  staged=(unit @t)
    ?:  deleting  ~
    ?:  =('document.save' operation.cmd)  (some (field payload.cmd 'markdown'))
    =/  source  (field payload.cmd 'source_container_id')
    =/  source-id  (field payload.cmd 'source_document_id')
    =/  from  (~(got by containers.data.db) source)
    =/  document  (~(got by documents.data.db) [project.cmd (scope-key:stead-core source source-id)])
    ?>  ?=(^ head.from)
    ?.  ?&  =(revision.document (uint (field payload.cmd 'source_revision')))
            =((oid-text:stead-git u.head.from) (field payload.cmd 'source_head'))
        ==
      ~
    =/  blob  (~(got by objects.data.db) blob.document)
    =/  prefix  (header source-id 'draft')
    ?>  =(prefix (cut 3 [0 (met 3 prefix)] data.body.blob))
    (some (cat 3 (header resource.cmd 'published') (cut 3 [(met 3 prefix) (sub length.body.blob (met 3 prefix))] data.body.blob)))
  ?:  &(!deleting ?=(~ staged))  [(error 'revision_conflict') db]
  ?:  ?|  deleting  =('document.publish' operation.cmd)
      ==
    ?.  =(?~(head.container '' (oid-text:stead-git u.head.container)) (field payload.cmd 'expected_head'))
      [(error 'revision_conflict') db]
    (finish-document db actor cmd now old new staged)
  =/  prefix  (header resource.cmd ?:(=('private' visibility.box) 'draft' 'published'))
  ?.  =(prefix (cut 3 [0 (met 3 prefix)] (need staged)))  [(error 'invalid_document') db]
  (finish-document db actor cmd now old new staged)
++  finish-document
  |=  [db=state actor=authentication cmd=command now=@ud old=@ud new=@ud markdown=(unit @t)]
  ^-  transition
  =/  cid  (container:stead-team-codec cmd)
  =/  container  (~(got by containers.data.db) cid)
  =/  prior  (~(get by documents.data.db) [project.cmd (scope-key:stead-core cid resource.cmd)])
  ?~  markdown
    ?:  (~(has in tombs.db) [project.cmd 'document' cid resource.cmd])  [(error 'invalid_command') db]
    ?>  ?=(^ prior)
    =.  entries.container  (~(del by entries.container) resource.cmd)
    (commit-document db actor cmd now old new container ~ blob.u.prior)
  ?.  (prose u.markdown 32.768)  [(error 'invalid_document') db]
  =/  blob  (make-blob:stead-git [(met 3 u.markdown) u.markdown])
  =.  entries.container  (~(put by entries.container) resource.cmd oid.blob)
  (commit-document db actor cmd now old new container [blob ~] oid.blob)
++  commit-document
  |=  $:  db=state  actor=authentication  cmd=command  now=@ud  old=@ud  new=@ud
          container=container-state:stead-core  blobs=(list object:stead-git)  blob=@ux
      ==
  ^-  transition
  =/  tree
    %-  make-tree:stead-git
    (turn ~(tap by entries.container) |=([id=@t oid=@ux] [(cat 3 id '.md') oid]))
  =/  commit  (make-commit:stead-git oid.tree head.container principal.identity.actor (div now 1.000) resource.cmd new)
  =/  additions=(list object:stead-git)  [tree commit blobs]
  =/  objects=(unit (map @ux object:stead-git))
    =/  existing  objects.data.db
    |-
    ?~  additions  (some existing)
    ?.  (immutable-object:stead-core existing i.additions)  ~
    $(additions t.additions, existing (~(put by existing) oid.i.additions i.additions))
  ?~  objects  [(error 'invalid_document') db]
  =/  total  (roll ~(tap by u.objects) |=([pair=[@ux object:stead-git] sum=@ud] (add sum length.body.+.pair)))
  ?:  (gth total 8.388.608)  [(error 'capacity_exceeded') db]
  =/  reachable=(set @ux)
    ?~  head.container  ~
    (~(got by reachable.data.db) u.head.container)
  =.  reachable  (~(uni in reachable) (silt (turn additions |=(obj=object:stead-git oid.obj))))
  =/  data  data.db
  =.  objects.data  u.objects
  =.  object-bytes.data  total
  =.  reachable.data  (~(put by reachable.data) oid.commit reachable)
  =/  cid  (container:stead-team-codec cmd)
  =.  containers.data  (~(put by containers.data) cid container(head [~ oid.commit], history [oid.commit history.container]))
  =.  documents.data  (~(put by documents.data) [project.cmd (scope-key:stead-core cid resource.cmd)] [new cid blob oid.commit])
  =?  tombs.db  =('document.delete' operation.cmd)
    (~(put in tombs.db) [project.cmd 'document' cid resource.cmd])
  (accept db(data data) actor cmd now old new (oid-text:stead-git oid.commit))
--
