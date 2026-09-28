::  Public configured-team protocol/3. No private home-state dependency.
/+  stead-codec
=,  stead-codec
|%
+$  query
  [request=@t kind=@t project=@t container=@t resource=@t search=@t cursor=@t]
++  version-error
  |=  [value=json domain=@t]
  ^-  (unit @t)
  ?>  ?=([%o *] value)
  ?:  =(domain (field p.value 'protocol'))  ~
  =/  request  (field p.value 'request_id')
  ?>  (uuid request)
  :-  ~
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.result/3']  ['status' 'rejected']
      ['request_id' request]  ['canonical_sha256' (hash domain (canonical value))]
      ['error' 'unsupported_version']
  ==
++  opaque
  |=  text=@t
  ^-  ?
  ?&  =(64 (met 3 text))
      (levy (rip 3 text) |=(c=@ ?|(&((gte c 48) (lte c 57)) &((gte c 97) (lte c 102)))))
  ==
++  oid
  |=  text=@t
  ^-  ?
  ?&  =(40 (met 3 text))
      (levy (rip 3 text) |=(c=@ ?|(&((gte c 48) (lte c 57)) &((gte c 97) (lte c 102)))))
  ==
++  scope
  |=  [kind=@t container=@t resource=@t]
  ^-  ?
  ?&  (uuid resource)
      ?:  =('document' kind)  (uuid container)
      &(=('work' kind) =('' container))
  ==
++  decode
  |=  raw=@t
  ^-  command
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['protocol' 'request_id' 'project_id' 'resource_id' 'expected_revision' 'authority_epoch' 'operation' 'payload'])
  ?>  =('stead.command/3' (field obj 'protocol'))
  =/  req  (field obj 'request_id')
  =/  pro  (field obj 'project_id')
  =/  res  (field obj 'resource_id')
  ?>  &((uuid req) (uuid pro) (uuid res))
  =/  exp  (uint (field obj 'expected_revision'))
  =/  epo  (uint (field obj 'authority_epoch'))
  ?>  (gth epo 0)
  =/  op  (field obj 'operation')
  =/  data  (~(got by obj) 'payload')
  ?>  ?=([%o *] data)
  =/  pay  p.data
  ?>
    ?:  =('project.create' op)
      ?&  =(exp 0)  =(pro res)
          (keys pay ~['organization_id' 'owning_team_id' 'title' 'project_key' 'preset'])
          (uuid (field pay 'organization_id'))  (uuid (field pay 'owning_team_id'))
          (title (field pay 'title'))  (project-key (field pay 'project_key'))
          =('general' (field pay 'preset'))
      ==
    ?:  =('work.create' op)  &(=(exp 0) (work-payload pay))
    ?:  =('work.update' op)  &((gth exp 0) (work-payload pay))
    ?:  =('work.delete' op)  &((gth exp 0) (keys pay ~))
    ?:  =('container.create' op)
      ?&  =(exp 0)  (keys pay ~['title' 'visibility'])
          (title (field pay 'title'))
          ?|  =('private' (field pay 'visibility'))  =('shared' (field pay 'visibility'))
          ==
      ==
    ?:  =('document.save' op)
      ?&  (keys pay ~['container_id' 'markdown'])
          (uuid (field pay 'container_id'))  (prose (field pay 'markdown') 32.768)
      ==
    ?:  =('document.delete' op)
      ?&  (gth exp 0)  (keys pay ~['container_id' 'expected_head'])
          (uuid (field pay 'container_id'))  (oid (field pay 'expected_head'))
      ==
    ?:  =('document.publish' op)
      ?&  =(exp 0)
          (keys pay ~['source_project_id' 'source_container_id' 'source_document_id' 'source_revision' 'source_head' 'container_id' 'expected_head'])
          =(pro (field pay 'source_project_id'))  (uuid (field pay 'source_container_id'))
          (uuid (field pay 'source_document_id'))  (gth (uint (field pay 'source_revision')) 0)
          (oid (field pay 'source_head'))  (uuid (field pay 'container_id'))
          ?|  =('' (field pay 'expected_head'))  (oid (field pay 'expected_head'))
          ==
      ==
    ?:  =('relation.create' op)
      ?&  =(exp 0)
          (keys pay ~['type' 'source_project_id' 'source_kind' 'source_container_id' 'source_id' 'target_project_id' 'target_kind' 'target_container_id' 'target_id'])
          (~(has in (silt ~['related_to' 'blocks' 'documents'])) (field pay 'type'))
          =(pro (field pay 'source_project_id'))  =(pro (field pay 'target_project_id'))
          (scope (field pay 'source_kind') (field pay 'source_container_id') (field pay 'source_id'))
          (scope (field pay 'target_kind') (field pay 'target_container_id') (field pay 'target_id'))
          ?:  =('blocks' (field pay 'type'))
            &(=('work' (field pay 'source_kind')) =('work' (field pay 'target_kind')))
          ?:  =('documents' (field pay 'type'))
            &(=('document' (field pay 'source_kind')) =('work' (field pay 'target_kind')))
          &
      ==
    ?:  =('relation.delete' op)  &((gth exp 0) (keys pay ~))
    ?:  =('policy.grant' op)
      ?&  (gth exp 0)  =(pro res)
          (keys pay ~['grant_id' 'principal_id' 'role' 'expires_at_ms'])
          (uuid (field pay 'grant_id'))  (uuid (field pay 'principal_id'))
          (~(has in (silt ~['reader' 'contributor' 'maintainer'])) (field pay 'role'))
          (gth (uint (field pay 'expires_at_ms')) 0)
      ==
    ?:  =('policy.revoke' op)
      ?&  (gth exp 0)  =(pro res)
          (keys pay ~['grant_id'])  (uuid (field pay 'grant_id'))
      ==
    |
  =/  canon  (canonical value)
  ['stead.command/3' req pro res exp epo op pay canon (hash 'stead.command/3' canon)]
++  decode-query
  |=  raw=@t
  ^-  query
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  =/  obj  p.value
  ?>  (keys obj ~['protocol' 'request_id' 'kind' 'project_id' 'container_id' 'resource_id' 'search' 'cursor'])
  ?>  =('stead.query/3' (field obj 'protocol'))
  =/  req  (field obj 'request_id')
  =/  kind  (field obj 'kind')
  =/  project  (field obj 'project_id')
  =/  container  (field obj 'container_id')
  =/  resource  (field obj 'resource_id')
  =/  search  (field obj 'search')
  =/  cursor  (field obj 'cursor')
  ?>  (uuid req)
  ?>  ?|  =('' cursor)  (opaque cursor)
      ==
  ?>  ?|  ?&  (~(has in (silt ~['identity' 'capabilities' 'projects'])) kind)
              =('' project)  =('' container)  =('' resource)  =('' search)
          ==
          ?&  (uuid project)
              (~(has in (silt ~['project' 'work' 'containers' 'documents' 'document' 'relations' 'search' 'activity' 'inbox' 'receipt'])) kind)
              ?:  ?|  =('documents' kind)  =('document' kind)
                  ==
                ?&  (uuid container)  =('' search)
                    ?:(=('document' kind) (uuid resource) =('' resource))
                ==
              ?:  =('work' kind)
                &(=('' container) =('' search) ?|(=('' resource) (uuid resource)))
              ?:  =('receipt' kind)
                &((uuid resource) ?|(=('' container) (uuid container)) =('' search))
              ?&  =('' resource)  =('' container)
                  ?:(=('search' kind) (prose search 128) =('' search))
              ==
          ==
      ==
  [req kind project container resource search cursor]
++  kind
  |=  operation=@t
  ^-  @t
  ?:  =('project.create' operation)  'project'
  ?:  =('container.create' operation)  'container'
  ?:  =('document.' (cut 3 [0 9] operation))  'document'
  ?:  =('relation.' (cut 3 [0 9] operation))  'relation'
  ?:  =('policy.' (cut 3 [0 7] operation))  'policy'
  'work'
++  container
  |=  cmd=command
  ^-  @t
  ?:  =('container.create' operation.cmd)  resource.cmd
  ?:  =('document' (kind operation.cmd))  (field payload.cmd 'container_id')
  ''
--
