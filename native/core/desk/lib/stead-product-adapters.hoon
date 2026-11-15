::  Reserved current-state adapters for native member Work commands.
::  These are Home internals, never client-supplied permission assertions.
::  They do not implement historical replay or accepted Change authority.
/+  stead-codec, stead-core, stead-git, stead-team, stead-principals, stead-product-codec, stead-product-work
=,  stead-codec
|%
++  markdown-sha256
  |=  raw=octets:stead-git
  ^-  @t
  ?>  &((valid-octets:stead-git raw) (lte length.raw 32.768))
  ::  Exact stored bytes and length: no frontmatter or whitespace rewriting.
  (hex 64 (sha-256l:sha [length.raw (rev 3 length.raw data.raw)]))
++  current-kind
  |=  [db=state:stead-team catalog=state:stead-principals project=@t principal=@t now=@ud]
  ^-  (unit principal-kind:stead-product-work)
  =/  kind  (native-kind:stead-principals catalog registry.db principal now)
  ?~  kind  ~
  =/  member  (active-member:stead-team db principal now)
  ?~  member  ~
  =/  actor  (native-context:stead-team db ship.identity.u.member now)
  ?~  actor  ~
  ?.  (gte (role:stead-team db u.actor project now) 2)  ~
  kind
++  target-check
  |=  [db=state:stead-team actor=authentication:stead-team project=@t work=@t principal=@t target=json now=@ud]
  ^-  ?
  ?.  &((current:stead-team db actor now) =(principal principal.identity.actor))  |
  ?.  (gte (role:stead-team db actor project now) 2)  |
  ?.  (outcome:stead-product-codec project work target)  |
  ?>  ?=([%o *] target)
  ?.  =('document' (field p.target 'kind'))  |
  =/  collection  (field p.target 'collection_id')
  =/  document  (field p.target 'document_id')
  =/  box  (~(get by boxes.db) collection)
  ?~  box  |
  ?.  &(=(project project.u.box) =('shared' visibility.u.box))  |
  ?.  (box-access:stead-team db actor project collection now)  |
  ?:  (~(has in tombs.db) [project 'document' collection document])  |
  =/  item  (~(get by documents.data.db) [project (scope-key:stead-core collection document)])
  =/  revision  (uint (field p.target 'expected_revision'))
  ?:  =(revision 0)  ?=(~ item)
  ?~  item  |
  ?.  =(revision revision.u.item)  |
  =/  blob  (~(get by objects.data.db) blob.u.item)
  ?~  blob  |
  ?.  =(%blob kind.u.blob)  |
  =((field p.target 'base_markdown_sha256') (markdown-sha256 body.u.blob))
++  current-target
  |=  [db=state:stead-team actor=authentication:stead-team project=@t work=@t principal=@t target=json now=@ud]
  ^-  ?
  =/  checked  (mule |.((target-check db actor project work principal target now)))
  ?:  ?=(%| -.checked)  |
  p.checked
++  deny-proof
  |=  request=proof-request:stead-product-work
  ^-  (unit proof:stead-product-work)
  ::  Completion waits for independently accepted Change/check evidence.
  ~
++  current
  |=  [db=state:stead-team catalog=state:stead-principals actor=authentication:stead-team]
  ^-  resolvers:stead-product-work
  =/  kinds=kind-resolver:stead-product-work
    |=  [project=@t principal=@t now=@ud]
    (current-kind db catalog project principal now)
  =/  targets=target-resolver:stead-product-work
    |=  [project=@t work=@t principal=@t target=json now=@ud]
    (current-target db actor project work principal target now)
  [kinds targets deny-proof]
--
