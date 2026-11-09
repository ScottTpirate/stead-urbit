::  Repository authority called only by the configured Home. Repositories
::  persist with the Home; device credentials are never in the saved envelope.
/+  stead-codec, stead-core, stead-team, stead-team-config, stead-session, stead-http, stead-git, stead-code-credentials, stead-code-store, stead-code-service, stead-code-http, stead-code-git-graph, stead-code-git-objects, stead-code-receive, stead-code-upload, stead-code-review-home, stead-code-review-api, stead-code-build-home
=,  stead-codec
|%
+$  repository  [data=repository:stead-code-service protected=(set @t)]
+$  saved  (map @t repository)
+$  boards  (map @t state:stead-code-review-home)
+$  build-data  (map @t state:stead-code-build-home)
+$  persisted  [repos=saved uploads=jobs:stead-code-upload reviews=boards builds=build-data]
+$  state  [repos=saved book=ledger:stead-code-credentials uploads=jobs:stead-code-upload reviews=boards builds=build-data]
+$  admission  $%([%held next=state key=@t] [%refused out=result])
+$  result  [status=@ud mime=@t body=octets:stead-git next=state]
++  text
  |=  [code=state status=@ud mime=@t body=@t]
  ^-  result
  [status mime [(met 3 body) body] code]
++  error
  |=  [code=state status=@ud why=@t]
  ^-  result
  (text code status 'application/json' (error:stead-team why))
++  target
  |=  [db=state:stead-team project=@t]
  ^-  (unit scope:stead-code-credentials)
  =/  config  current.registry.db
  ?~  config  ~
  =/  row  (~(get by projects.data.db) project)
  ?~  row  ~
  [~ home.u.config project project epoch.u.row]
++  rank
  |=  [db=state:stead-team who=actor:stead-session destination=scope:stead-code-credentials now=@ud]
  ^-  @ud
  ?.  =([~ destination] (target db project.destination))  0
  =/  native  (native-context:stead-team db ship.who now)
  ?~  native  0
  ?.  (same-actor:stead-session who identity.u.native)  0
  (role:stead-team db u.native project.destination now)
++  allowed
  |=  [db=state:stead-team now=@ud]
  ^-  allowance:stead-code-credentials
  |=  [who=actor:stead-session destination=scope:stead-code-credentials operation=access:stead-code-credentials]
  =/  current  (rank db who destination now)
  (gte current ?:(=(%read operation) 1 2))
++  member
  |=  [db=state:stead-team now=@ud]
  ^-  membership:stead-code-credentials
  |=  ship=@p
  =/  row  (identity:stead-team-config registry.db ship now)
  ?~  row  ~
  [~ identity.u.row]
++  respond
  |=  [code=state rows=(list [@t @t])]
  ^-  result
  (text code 200 'application/json' (canonical (object [['protocol' 'stead.code/1'] rows])))
++  browser-session
  |=  [db=state:stead-team auth=state:stead-session input=incoming:stead-http now=@ud]
  ^-  (unit session:stead-session)
  =/  previous  (~(get by sessions.auth) (digest:stead-session 'stead.session/1' session.input))
  ?~  previous  ~
  =/  who  ((member db now) ship.identity.u.previous)
  ?~  who  ~
  =/  config  (need current.registry.db)
  (authorize:stead-session auth session.input csrf.input u.who home.config origin.config now)
++  manage
  |=  $:  db=state:stead-team  code=state  auth=state:stead-session
          input=incoming:stead-http  now=@ud  entropy=@
      ==
  ^-  result
  =/  session  (browser-session db auth input now)
  ?~  session  (error code 403 'session_or_csrf_required')
  ?.  (lte (met 3 body.input) 16.384)  (error code 400 'invalid_request')
  =/  json  (parse body.input)
  ?.  ?=([~ %o *] json)  (error code 400 'invalid_request')
  =/  values  p.u.json
  ?.  =('stead.code/1' (field values 'protocol'))  (error code 400 'invalid_request')
  =/  operation  (field values 'action')
  =/  is-build  (operation:stead-code-build-home operation)
  ?.  |(is-build (lte (met 3 body.input) 2.048))  (error code 400 'invalid_request')
  =/  project  (field values 'project_id')
  ?.  (uuid project)  (error code 400 'invalid_request')
  =/  destination  (target db project)
  ?~  destination  (error code 404 'denied_or_not_found')
  =/  actor  (browser-context:stead-team db u.session now)
  ?~  actor  (error code 403 'session_or_csrf_required')
  =/  role  (role:stead-team db u.actor project now)
  ?:  =(0 role)  (error code 404 'denied_or_not_found')
  =/  found  (~(get by repos.code) project)
  ?:  &(?=(^ found) !=(destination.data.u.found u.destination))  (error code 409 'authority_epoch_conflict')
  =/  base=(list @t)  ~['protocol' 'action' 'project_id']
  ?:  =('status' operation)
    ?.  (keys values base)  (error code 400 'invalid_request')
    (respond code ~[['status' ?~(found 'disabled' 'ready')] ['write' ?:((gte role 2) 'yes' 'no')] ['manage' ?:(=(3 role) 'yes' 'no')]])
  ?:  =('create' operation)
    ?.  (keys values base)  (error code 400 'invalid_request')
    ?.  =(3 role)  (error code 404 'denied_or_not_found')
    ?^  found  (respond code ~[['status' 'ready']])
    ?:  (gte ~(wyt by repos.code) 4)  (error code 409 'capacity_exceeded')
    =/  next  (~(put by repos.code) project [(empty:stead-code-store u.destination) ~])
    (respond code(repos next) ~[['status' 'ready']])
  ?~  found  (error code 404 'denied_or_not_found')
  ?:  =('issue' operation)
    ?.  (keys values ['access' base])  (error code 400 'invalid_request')
    =/  access  (field values 'access')
    ?.  |(=('read' access) =('write' access))  (error code 400 'invalid_request')
    =/  issued
      (issue:stead-code-credentials book.code identity.u.actor u.destination =('write' access) expires.u.session now entropy (allowed db now))
    ?:  ?=(%| -.issued)  (error code 403 p.issued)
    (respond code(book next.p.issued) ~[['status' 'issued'] ['handle' handle.p.issued] ['bearer' bearer.p.issued] ['expires_at_ms' (decimal expires.p.issued)]])
  ?:  =('revoke' operation)
    ?.  (keys values ['handle' base])  (error code 400 'invalid_request')
    =/  handle  (field values 'handle')
    ?.  (lien ~(tap by credentials.book.code) |=([key=@t row=credential:stead-code-credentials] &(=(handle handle.row) =(u.destination destination.row))))
      (error code 403 'denied_or_not_found')
    =/  revoked  (revoke:stead-code-credentials book.code handle identity.u.actor home.u.destination now)
    ?:  ?=(%| -.revoked)  (error code 403 p.revoked)
    (respond code(book p.revoked) ~[['status' 'revoked']])
  ?:  =('protect' operation)
    ?.  (keys values ['ref' base])  (error code 400 'invalid_request')
    ?.  =(3 role)  (error code 404 'denied_or_not_found')
    =/  ref  (field values 'ref')
    ?.  &((lte (met 3 ref) 128) =('refs/heads/' (cut 3 [0 11] ref)) (valid-ref:stead-code-git-objects [(met 3 ref) ref]))
      (error code 400 'invalid_request')
    =/  protected  (~(put in protected.u.found) ref)
    ?:  (gth ~(wyt in protected) 16)  (error code 409 'capacity_exceeded')
    (respond code(repos (~(put by repos.code) project u.found(protected protected))) ~[['status' 'protected']])
  =/  board  (fall (~(get by reviews.code) project) (empty:stead-code-review-home u.destination))
  ?:  is-build
    ?:  &(|(=('build-queue' operation) =('build-release' operation)) !=(3 role))
      (error code 404 'denied_or_not_found')
    =/  extras  (fall (~(get by builds.code) project) *state:stead-code-build-home)
    =/  out
      (run:stead-code-build-home db board extras data.u.found identity.u.actor now (member db now) values base operation)
    ?-  -.out
      %failed  (error code status.out reason.out)
      %read  (respond code rows.out)
      %accepted
        =/  reviews  (~(put by reviews.code) project board.out)
        =/  builds  (~(put by builds.code) project next.out)
        (respond code(reviews reviews, builds builds) rows.out)
    ==
  =/  out
    (run:stead-code-review-api db board data.u.found protected.u.found identity.u.actor now (member db now) values base operation)
  ?-  -.out
    %failed  (error code status.out reason.out)
    %read  (respond code rows.out)
    %accepted
      =/  repos  (~(put by repos.code) project u.found(data repo.out))
      =/  reviews  (~(put by reviews.code) project next.out)
      (respond code(repos repos, reviews reviews) rows.out)
  ==
++  request-id
  |=  [entropy=@ serial=@ud]
  ^-  @t
  =/  source  (token:stead-session entropy serial 'stead.git-operation/1')
  (rap 3 ~[(cut 3 [0 8] source) '-' (cut 3 [8 4] source) '-7' (cut 3 [12 3] source) '-8' (cut 3 [15 3] source) '-' (cut 3 [18 12] source)])
++  quarantine
  |=  [db=state:stead-team code=state input=incoming:stead-code-http now=@ud request=@t]
  ^-  admission
  =/  found  (~(get by repos.code) project.input)
  ?~  found  [%refused (error code 401 'denied_or_not_found')]
  =/  scope  destination.data.u.found
  =/  who  (check:stead-code-credentials book.code bearer.input scope %write now (member db now) (allowed db now))
  ?~  who  [%refused (error code 401 'denied_or_not_found')]
  =/  queued  (stage:stead-code-upload uploads.code scope u.who body.input now request)
  ?:  ?=(%| -.queued)  [%refused (error code 429 p.queued)]
  [%held code(uploads next.p.queued) key.p.queued]
++  finish-upload
  |=  [db=state:stead-team code=state key=@t bearer=@t now=@ud]
  ^-  result
  =/  found  (~(get by uploads.code) key)
  ?~  found  (error code 409 'upload_unavailable')
  =/  next  code(uploads (~(del by uploads.code) key))
  =/  job  u.found
  ?:  (lte until.job now)  (error next 409 'upload_expired')
  =/  scope  destination.job
  ?.  =([~ scope] (target db project.scope))  (error next 401 'denied_or_not_found')
  =/  who  (check:stead-code-credentials book.code bearer scope %write now (member db now) (allowed db now))
  ?~  who  (error next 401 'denied_or_not_found')
  ?.  (same-actor:stead-session owner.job u.who)  (error next 401 'denied_or_not_found')
  (serve db next [project.scope [%receive ~] bearer wire.job] now request.job)
++  validate-persisted
  |=  [team=state:stead-team rows=persisted]
  ^-  ?
  ?.  (validate-saved team repos.rows)  |
  ?.  (valid:stead-code-upload uploads.rows)  |
  ?.  &((lte ~(wyt by reviews.rows) 4) (lte ~(wyt by builds.rows) 4))  |
  ?.  (levy ~(tap by builds.rows) |=([id=@t data=state:stead-code-build-home] (~(has by reviews.rows) id)))  |
  ?.  %+  levy  ~(tap by reviews.rows)
      |=  [id=@t board=state:stead-code-review-home]
      =/  repo  (~(get by repos.rows) id)
      ?~  repo  |
      =/  extras  (fall (~(get by builds.rows) id) *state:stead-code-build-home)
      &((validate-saved:stead-code-review-home board data.u.repo) (validate-saved:stead-code-build-home board extras data.u.repo))
    |
  %+  levy  ~(tap by uploads.rows)
  |=  [key=@t job=upload:stead-code-upload]
  =/  scope  destination.job
  =/  repo  (~(get by repos.rows) project.scope)
  ?~  repo  |
  =(scope destination.data.u.repo)
++  serve
  |=  [db=state:stead-team code=state input=incoming:stead-code-http now=@ud request=@t]
  ^-  result
  =/  found  (~(get by repos.code) project.input)
  ?~  found  (error code 401 'denied_or_not_found')
  =/  repo  u.found
  =/  scope  destination.data.repo
  =/  operation=access:stead-code-credentials
    ?:  ?=(%receive -.operation.input)  %write
    ?:  ?=([%advertise %git-receive-pack] operation.input)  %write
    %read
  =/  resolve  (member db now)
  =/  allows  (allowed db now)
  =/  who  (check:stead-code-credentials book.code bearer.input scope operation now resolve allows)
  ?~  who  (error code 401 'denied_or_not_found')
  ?-  -.operation.input
    %advertise
      =/  mime  (rap 3 ~['application/x-' kind.operation.input '-advertisement'])
      [200 mime (discover:stead-code-service data.repo kind.operation.input) code]
    %fetch
      =/  fetched  (fetch:stead-code-service data.repo body.input)
      ?:  ?=(%| -.fetched)  (error code 400 p.fetched)
      [200 'application/x-git-upload-pack-result' p.fetched code]
    %receive
      =/  policy=ref-policy:stead-code-store
        |=  [actor=actor:stead-session destination=scope:stead-code-credentials action=action:stead-code-store change=update:stead-code-store]
        (allows actor destination %write)
      =/  result
        (receive:stead-code-service data.repo body.input request book.code bearer.input now resolve allows policy protected.repo)
      ?:  ?=(%| -.result)  (error code 400 p.result)
      =/  updated  (~(put by repos.code) project.input repo(data next.p.result))
      [200 'application/x-git-receive-pack-result' body.p.result code(repos updated)]
  ==
::  Saved code is outside the Work/Docs projection. Validate before the Home
::  makes its new incarnation available. Receipt order rebuilds current refs.
++  validate-saved
  |=  [team=state:stead-team rows=saved]
  ^-  ?
  ?.  (lte ~(wyt by rows) 4)  |
  %+  levy  ~(tap by rows)
  |=  [project=@t repo=repository]
  =/  db  data.repo
  ?&  (uuid project)
      =(1 version.db)
      =([~ destination.db] (target team project))
      ?=(~ pending.db)
      (lte ~(wyt by refs.db) 16)
      (lte ~(wyt in protected.repo) 16)
      (levy ~(tap in protected.repo) |=(ref=@t &((lte (met 3 ref) 128) =('refs/heads/' (cut 3 [0 11] ref)) (valid-ref:stead-code-git-objects [(met 3 ref) ref]))))
      (lte (lent (scag 33 journal.db)) 32)
      =(revision.db (lent journal.db))
      =(revision.db ~(wyt by receipts.db))
      (validate-objects db)
      (validate-journal db)
  ==
++  validate-objects
  |=  db=repository:stead-code-service
  ^-  ?
  ?:  ?=([%| *] (combine:stead-code-store objects.db ~))  |
  ?.  (levy ~(tap by objects.db) |=([id=@ux item=object:stead-git] ?=([%& *] (inspect:stead-code-git-graph item))))  |
  ?=([%& *] (closure:stead-code-store refs.db (read-object:stead-code-service db)))
++  validate-journal
  |=  db=repository:stead-code-service
  ^-  ?
  =/  pending  (flop journal.db)
  =/  revision=@ud  0
  =/  refs=refs:stead-code-store  ~
  |-  ^-  ?
  ?~  pending  =(refs refs.db)
  =/  row  (~(get by receipts.db) i.pending)
  ?~  row  |
  =/  receipt  u.row
  ?.  &((uuid i.pending) =(i.pending id.receipt) =(1 version.receipt) =(destination.db destination.receipt) =(+(revision) revision.receipt) (token-valid:stead-session digest.receipt) (live:stead-session owner.receipt 0))
    |
  ?.  (payload-bounds:stead-code-store [destination.db id.receipt owner.receipt changes.receipt ~])  |
  =/  kind=$-(@ux (unit @tas))
    |=  id=@ux
    =/  object  (~(get by objects.db) id)
    ?~  object  ~
    [~ kind.u.object]
  =/  replayed
    %-  decide:stead-code-receive
    :*  refs  epoch.destination.db  epoch.destination.db  changes.receipt  ~
        |=([action=action:stead-code-store update=update:stead-code-store] &)
        kind
        |=([base=@ux tip=@ux] (descends:stead-code-store base tip (read-object:stead-code-service db)))
    ==
  ?:  ?=(%| -.replayed)  |
  $(pending t.pending, revision +(revision), refs p.replayed)
--
