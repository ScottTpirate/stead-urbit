::  Authorized read projections and opaque, bounded pagination.
/+  stead-codec, stead-team-codec, stead-team, stead-team-config, stead-core, stead-git, stead-projection, stead-session
=,  stead-codec
|%
+$  row  [id=@t fields=object-map]
+$  cursor-record
  [actor=authentication:stead-team query=query:stead-team-codec generation=@t rank=@ud epoch=@ud offset=@ud expires=@ud purpose=@t owner=@t access=@t]
+$  state  [counter=@ud cursors=(map @t cursor-record)]
+$  result  [response=@t next=state]
++  fields
  |=  pairs=(list [@t @t])
  ^-  object-map
  =/  obj  (object pairs)
  ?>  ?=([%o *] obj)
  p.obj
++  prefix
  |=  [text=@t length=@ud]
  ^-  @t
  (tuft (cut 5 [0 length] (taft text)))
++  contains
  |=  [needle=@t haystack=@t]
  ^-  ?
  ?=(^ (find (rip 3 needle) (rip 3 haystack)))
++  authorized
  |=  [db=state:stead-team actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  ?
  ?.  (current:stead-team db actor now)  |
  ?:  ?|(=('identity' kind.query) =('capabilities' kind.query) =('projects' kind.query))  &
  ?.  (gth (role:stead-team db actor project.query now) 0)  |
  ?:  ?|(=('documents' kind.query) =('document' kind.query))
    ?&  (box-access:stead-team db actor project.query container.query now)
        ?|  =('documents' kind.query)
            (subject:stead-team db actor project.query 'document' container.query resource.query now)
        ==
    ==
  ?:  &(=('work' kind.query) !=('' resource.query))
    (subject:stead-team db actor project.query 'work' '' resource.query now)
  ?:  =('receipt' kind.query)
    =/  receipt  (~(get by receipts.data.db) [project.query principal.identity.actor resource.query])
    ?~  receipt
      ?|  =('' container.query)
          (box-access:stead-team db actor project.query container.query now)
      ==
    =/  cmd  (decode:stead-team-codec command.u.receipt)
    &((allowed:stead-team db actor cmd now) =(container.query (container:stead-team-codec cmd)))
  &
++  generation
  |=  [db=state:stead-team actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  @t
  =/  config  (need current.registry.db)
  =/  selected=(map [@t @t] @ud)  ~
  =/  roles=(map @t [@ud @ud])
    %-  malt
    %+  turn
      %+  skim  ~(tap by projects.data.db)
      |=  [id=@t val=project-state:stead-core]
      &((gth (role:stead-team db actor id now) 0) ?|(=('projects' kind.query) =(id project.query)))
    |=  [id=@t val=project-state:stead-core]
    =/  rank  (role:stead-team db actor id now)
    [id rank ?:(&(=(rank 3) ?|(=('project' kind.query) =('projects' kind.query))) policy.val 0)]
  =/  rows  ~(tap by generations.db)
  |-
  ?~  rows
    =/  identity-view
      ?:  =('identity' kind.query)
        [(~(got by members.config) ship.identity.actor) (~(has in creators.config) principal.identity.actor)]
      ~
    (hash 'stead.view-generation/3' (bytes-hex (jam [identity.actor identity-view roles selected])))
  =/  project  -.p.i.rows
  =/  scope  +.p.i.rows
  =/  value  q.i.rows
  ?.  ?:(=('projects' kind.query) (gth (role:stead-team db actor project now) 0) =(project project.query))
    $(rows t.rows)
  =/  access  =(scope (cat 3 'access:' principal.identity.actor))
  =/  included
    ?:  access  &
    ?:  =('' scope)
      ?:  =('' container.query)  &
      =/  box  (~(got by boxes.db) container.query)
      =('shared' visibility.box)
    ?:  (~(has in (silt ~['identity' 'projects' 'project' 'work'])) kind.query)  |
    ?:  !=('' container.query)  =(scope container.query)
    (box-access:stead-team db actor project scope now)
  $(rows t.rows, selected ?:(included (~(put by selected) p.i.rows value) selected))
++  metadata
  |=  [db=state:stead-team actor=authentication:stead-team project=@t now=@ud]
  ^-  object-map
  =/  item  (~(got by projects.data.db) project)
  =/  role  (role:stead-team db actor project now)
  =/  out  (fields ~[['kind' 'project'] ['resource_id' project] ['project_id' project] ['title' (field data.item 'title')] ['project_key' (field data.item 'project_key')] ['preset' 'general'] ['authority_epoch' (decimal epoch.item)] ['resource_revision' (decimal revision.item)] ['role' ?:(=(role 3) 'maintainer' ?:(=(role 2) 'contributor' 'reader'))]])
  ?:(=(role 3) (~(put by out) 'policy_revision' [%s (decimal policy.item)]) out)
++  resource-row
  |=  [db=state:stead-team actor=authentication:stead-team key=[project=@t kind=@t container=@t id=@t] now=@ud body=?]
  ^-  object-map
  =/  id  id.key
  =/  project  project.key
  =/  kind  kind.key
  =/  container  container.key
  ?:  =('project' kind)  (metadata db actor project now)
  ?:  =('container' kind)
    =/  item  (~(got by boxes.db) id)
    =/  git  (~(got by containers.data.db) id)
    (fields ~[['kind' 'container'] ['resource_id' id] ['container_id' id] ['title' title.item] ['visibility' visibility.item] ['resource_revision' '1'] ['container_head' ?~(head.git '' (oid-text:stead-git u.head.git))]])
  ?:  =('work' kind)
    =/  item  (~(got by works.data.db) [project id])
    =/  displayed  ?:(body data.item (~(put by data.item) 'description' [%s (prefix (field data.item 'description') 160)]))
    %-  ~(uni by displayed)
    (fields ~[['kind' kind] ['resource_id' id] ['container_id' ''] ['resource_revision' (decimal revision.item)] ['snippet' (prefix (field data.item 'description') 160)]])
  ?:  =('document' kind)
    =/  item  (~(got by documents.data.db) [project (scope-key:stead-core container id)])
    =/  git  (~(got by containers.data.db) container)
    =/  box  (~(got by boxes.db) container)
    =/  blob  (~(got by objects.data.db) blob.item)
    =/  markdown  data.body.blob
    =/  header  (header:stead-team id ?:(=('private' visibility.box) 'draft' 'published'))
    =/  content  (cut 3 [(met 3 header) (sub (met 3 markdown) (met 3 header))] markdown)
    =/  title  (prefix content 80)
    =/  out  (fields ~[['kind' kind] ['resource_id' id] ['container_id' container] ['resource_revision' (decimal revision.item)] ['container_head' ?~(head.git '' (oid-text:stead-git u.head.git))] ['title' title] ['snippet' (prefix content 160)] ['visibility' visibility.box]])
    ?:  body  (~(put by out) 'markdown' [%s markdown])
    out
  =/  item  (~(got by links.db) [project id])
  =/  source  (resource-row db actor [project (field data.item 'source_kind') (field data.item 'source_container_id') (field data.item 'source_id')] now |)
  =/  target  (resource-row db actor [project (field data.item 'target_kind') (field data.item 'target_container_id') (field data.item 'target_id')] now |)
  %-  ~(uni by data.item)
  (fields ~[['kind' kind] ['resource_id' id] ['container_id' ''] ['resource_revision' (decimal revision.item)] ['title' (rap 3 ~[(field source 'title') ' — ' (field data.item 'type') ' — ' (field target 'title')])]])
++  searchable
  |=  [db=state:stead-team key=[project=@t kind=@t container=@t id=@t] needle=@t]
  ^-  ?
  ?:  =('' needle)  &
  ?:  =('work' kind.key)
    =/  item  (~(got by works.data.db) [project.key id.key])
    ?|  (contains needle (field data.item 'title'))
        (contains needle (field data.item 'description'))
    ==
  =/  item  (~(got by documents.data.db) [project.key (scope-key:stead-core container.key id.key)])
  =/  blob  (~(got by objects.data.db) blob.item)
  (contains needle data.body.blob)
++  rows
  |=  [db=state:stead-team index=index:stead-projection actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  (list row)
  ?:  =('capabilities' kind.query)
    =/  config  (need current.registry.db)
    ~[['capabilities' (fields ~[['protocol' 'stead.capabilities/3'] ['profile' 'configured-team'] ['commands' 'stead.command/3'] ['queries' 'stead.query/3'] ['updates' 'stead.updates/3'] ['authentication' method.actor] ['max_request_bytes' '65536'] ['max_response_bytes' '262144'] ['page_size' '20'] ['runtime' runtime.config]])]]
  ?:  =('identity' kind.query)
    =/  config  (need current.registry.db)
    =/  person  (~(got by members.config) ship.identity.actor)
    ~[['identity' (fields ~[['principal_id' principal.identity.actor] ['identity_ship' (scot %p ship.identity.actor)] ['binding_id' binding.identity.actor] ['binding_revision' (decimal revision.identity.actor)] ['session_audit_id' audit.actor] ['display_name' display.person] ['organization_id' organization.config] ['team_id' team.config] ['home' (scot %p home.config)] ['can_create' ?:((~(has in creators.config) principal.identity.actor) 'yes' 'no')]])]]
  ?:  =('receipt' kind.query)
    =/  item  (~(get by receipts.data.db) [project.query principal.identity.actor resource.query])
    ?~  item  ~
    =/  value  (need (parse-result bytes.u.item))
    ?>  ?=([%o *] value)
    ~[[resource.query p.value]]
  ?:  ?|(=('activity' kind.query) =('inbox' kind.query))
    (activity db index actor query now)
  =/  keys  ~(tap in resources.index)
  =/  out=(list row)  ~
  |-
  ?~  keys  (sort out |=([a=row b=row] (aor id.a id.b)))
  =/  key=[project=@t kind=@t container=@t id=@t]  i.keys
  =/  matches
    ?:  =('projects' kind.query)  =('project' kind.key)
    ?&  =(project.query project.key)
        ?:  =('search' kind.query)  ?|(=('work' kind.key) =('document' kind.key))
        ?:  =('project' kind.query)  =('project' kind.key)
        ?:  =('work' kind.query)  &(=('work' kind.key) ?|(=('' resource.query) =(resource.query id.key)))
        ?:  =('containers' kind.query)  =('container' kind.key)
        ?:  =('relations' kind.query)  =('relation' kind.key)
        ?&  =('document' kind.key)  =(container.query container.key)
            ?|(=('documents' kind.query) =(resource.query id.key))
        ==
    ==
  ?.  &(matches (subject:stead-team db actor project.key kind.key container.key id.key now))
    $(keys t.keys)
  ?:  &(=('search' kind.query) !(searchable db key search.query))  $(keys t.keys)
  =/  item  (resource-row db actor key now ?|(=('document' kind.query) &(=('work' kind.query) !=('' resource.query))))
  $(keys t.keys, out [[(rap 3 ~[kind.key '/' container.key '/' id.key]) item] out])
++  activity
  |=  [db=state:stead-team index=index:stead-projection actor=authentication:stead-team query=query:stead-team-codec now=@ud]
  ^-  (list row)
  =/  entries  entries.index
  =/  out=(list row)  ~
  |-
  ?~  entries  (flop out)
  =/  item  i.entries
  ?.  &(=(project.query project.item) !=('policy' kind.item))  $(entries t.entries)
  ?:  &(=('inbox' kind.query) =(principal.identity.actor principal.item))  $(entries t.entries)
  =/  accessible
    ?:  =('document' kind.item)  (box-access:stead-team db actor project.item container.item now)
    ?:  =('container' kind.item)  (box-access:stead-team db actor project.item resource.item now)
    ?:  =('relation' kind.item)  (subject:stead-team db actor project.item 'relation' '' resource.item now)
    (gth (role:stead-team db actor project.item now) 0)
  ?.  accessible  $(entries t.entries)
  =/  receipt  (need (parse-result receipt.item))
  ?>  ?=([%o *] receipt)
  =/  row
    (fields ~[['kind' 'activity'] ['resource_id' resource.item] ['container_id' container.item] ['operation' operation.item] ['title' operation.item] ['request_id' request.item] ['principal_id' principal.item] ['accepted_at_ms' (field p.receipt 'accepted_at_ms')]])
  $(entries t.entries, out [[request.item row] out])
++  execute
  |=  [db=state:stead-team view=state:stead-projection prior=state actor=authentication:stead-team query=query:stead-team-codec now=@ud entropy=@]
  ^-  result
  ?.  (authorized db actor query now)  [(error:stead-team 'denied_or_not_found') prior]
  ?.  (ready:stead-projection db view)  [(error:stead-team 'projection_unavailable') prior]
  =/  gen  (generation db actor query now)
  =/  rank  ?:(=('' project.query) 0 (role:stead-team db actor project.query now))
  =/  epoch  ?:(=('' project.query) 0 epoch:(~(got by projects.data.db) project.query))
  =/  offset=@ud  0
  =/  next=state  prior(cursors (malt (skim ~(tap by cursors.prior) |=([key=@t val=cursor-record] (gth expires.val now)))))
  =/  filter  query(request '', cursor '')
  =/  continuation=(unit cursor-record)  (~(get by cursors.next) cursor.query)
  ?:  &(!=('' cursor.query) ?=(~ continuation))  [(error:stead-team 'stale_cursor') prior]
  =/  valid
    ?~  continuation  &
    ?&  =('query' purpose.u.continuation)  =(actor actor.u.continuation)  =(filter query.u.continuation)
        =(gen generation.u.continuation)  =(rank rank.u.continuation)  =(epoch epoch.u.continuation)
    ==
  ?.  valid  [(error:stead-team 'stale_cursor') prior]
  =?  offset  ?=(^ continuation)  offset.u.continuation
  =.  cursors.next  (~(del by cursors.next) cursor.query)
  =/  all  (rows db visible.view actor query now)
  ?:  (gth offset (lent all))  [(error:stead-team 'stale_cursor') prior]
  =/  remaining  (slag offset all)
  =/  page  (scag 20 remaining)
  =/  token=@t  ''
  =/  more  (gth (lent remaining) 20)
  ::  One pagination walk per exact actor. Fresh paginated snapshots supersede
  ::  that actor's old query walks, but metadata reads and update cursors do not.
  ::  Keep this staged until the full bounded response has encoded successfully.
  =?  cursors.next  &(more =('' cursor.query))
    (malt (skip ~(tap by cursors.next) |=([key=@t val=cursor-record] &(=('query' purpose.val) =(actor actor.val)))))
  ?:  &(more ?|((gte counter.next 18.446.744.073.709.551.615) (gte (lent ~(tap by cursors.next)) 64) (gte (lent (skim ~(tap by cursors.next) |=([key=@t val=cursor-record] =(principal.identity.actor principal.identity.actor.val)))) 4)))
    [(error:stead-team 'capacity_exceeded') prior]
  =?  next  more  next(counter +(counter.next))
  =?  token  more  (token:stead-session entropy counter.next 'stead.cursor/3')
  ?:  &(more (~(has by cursors.prior) token))  [(error:stead-team 'capacity_exceeded') prior]
  =?  cursors.next  more
    (~(put by cursors.next) token [actor filter gen rank epoch (add offset (lent page)) (min expires.actor (add now 300.000)) 'query' '' ''])
  =/  response
    (fields ~[['protocol' 'stead.query-result/3'] ['status' 'read'] ['request_id' request.query] ['kind' kind.query] ['project_id' project.query] ['container_id' container.query] ['resource_id' resource.query] ['authority_epoch' (decimal epoch)] ['generation' gen] ['cursor' token]])
  =/  counter=@ud  0
  =/  output=object-map  ~
  |-
  ?~  page
    =/  raw  (canonical [%o (~(put by response) 'rows' [%o output])])
    ?:  (gth (met 3 raw) 262.144)  [(error:stead-team 'capacity_exceeded') prior]
    [raw next]
  $(page t.page, counter +(counter), output (~(put by output) (decimal counter) [%o fields.i.page]))
--
