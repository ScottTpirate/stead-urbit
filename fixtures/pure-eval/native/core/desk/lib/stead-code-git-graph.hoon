::  Derived structure for SHA-1 Git objects. The home supplies scoped lookup.
/+  stead-code-git-objects
|%
+$  octets  octets:stead-code-git-objects
+$  object  object:stead-code-git-objects
+$  object-kind  ?(%blob %tree %commit %tag)
+$  edge  [oid=@ux type=object-kind]
+$  tree-mode  ?(%directory %file %executable)
+$  tree-entry  [name=@t mode=tree-mode child=edge]
+$  facts
  $%  [%blob ~]
      [%tree entries=(list tree-entry)]
      [%commit root=edge parents=(list edge)]
      [%tag target=edge]
  ==
+$  reader  $-(@ux (unit object))
+$  path-item  $%([%visit edge] [%leave oid=@ux])
+$  closure
  $%  [%checking todo=(list path-item) seen=(map @ux object-kind) active=(set @ux) queued=@ud visits=@ud bytes=@ud]
      [%verified reachable=(map @ux object-kind)]
      [%invalid reason=@tas]
  ==
::
++  until-byte
  |=  [data=@ cursor=@ud stop=@ud sought=@ud]
  ^-  (unit @ud)
  ?:  (gte cursor stop)  ~
  ?:  =(sought (cut 3 [cursor 1] data))  [~ cursor]
  $(cursor +(cursor))
::
++  tree-name
  |=  value=@t
  ^-  ?
  =/  size=@ud  (met 3 value)
  ?:  |(=(0 size) (gth size 255) =(value '.') =(value '..'))  |
  =/  folded=@t  (crip (cass (trip value)))
  ?:  |(=('.git' folded) =('git~1' folded))  |
  =/  last=@ud  (cut 3 [(dec size) 1] value)
  ?:  |(=(32 last) =(46 last))  |
  %+  levy  (trip value)
  |=  byte=@
  &((gte byte 32) !=(byte 127) !=(byte 47) !=(byte 92) !=(byte 58))
::
++  mode-of
  |=  value=@t
  ^-  (unit tree-mode)
  ?:  =('40000' value)  [~ %directory]
  ?:  =('100644' value)  [~ %file]
  ?:  =('100755' value)  [~ %executable]
  ~
::
++  tree-contents
  |=  data=octets
  ^-  (each (list tree-entry) @tas)
  =/  cursor=@ud  0
  =/  count=@ud  0
  =/  entries=(list tree-entry)  ~
  =/  seen=(set @t)  ~
  =/  prior=@t  ''
  |-  ^-  (each (list tree-entry) @tas)
  ?:  =(cursor length.data)  [%& (flop entries)]
  ?:  =(4.096 count)  [%| %tree-entry-bound]
  =/  space  (until-byte data.data cursor (min length.data (add cursor 7)) 32)
  ?~  space  [%| %tree-mode]
  =/  mode  (mode-of (cut 3 [cursor (sub u.space cursor)] data.data))
  ?~  mode  [%| %tree-mode]
  =/  start=@ud  +(u.space)
  =/  stop  (until-byte data.data start (min length.data (add start 256)) 0)
  ?~  stop  [%| %tree-name]
  =/  name=@t  (cut 3 [start (sub u.stop start)] data.data)
  ?.  (tree-name name)  [%| %tree-name]
  ?:  (~(has in seen) name)  [%| %tree-duplicate]
  =/  directory  =(%directory u.mode)
  =/  key=@t  ?:(directory (cat 3 name '/') name)
  ?.  (aor prior key)  [%| %tree-order]
  =/  next=@ud  (add u.stop 21)
  ?:  (gth next length.data)  [%| %tree-oid]
  =/  oid=@ux  (rev 3 20 (cut 3 [+(u.stop) 20] data.data))
  ?:  =(0 oid)  [%| %tree-oid]
  =/  entry=tree-entry  [name u.mode oid ?:(directory %tree %blob)]
  $(cursor next, count +(count), entries [entry entries], seen (~(put in seen) name), prior key)
::
++  line
  |=  [data=octets at=@ud]
  ^-  (unit [text=@t next=@ud])
  =/  ending  (until-byte data.data at (min length.data 65.536) 10)
  ?~  ending  ~
  =/  width=@ud  (sub u.ending at)
  ?:  ?=(^ (until-byte data.data at u.ending 0))  ~
  [~ (cut 3 [at width] data.data) +(u.ending)]
::
++  oid-line
  |=  [text=@t prefix=@t]
  ^-  (unit @ux)
  =/  width=@ud  (met 3 prefix)
  ?.  &(=((add width 40) (met 3 text)) =(prefix (cut 3 [0 width] text)))
    ~
  =/  oid  (parse-oid:stead-code-git-objects [40 (cut 3 [width 40] text)])
  ?~  oid  ~
  ?:(=(0 u.oid) ~ oid)
::
++  header-end
  |=  [data=octets at=@ud]
  ^-  ?
  =/  row  (line data at)
  ?~  row  |
  ?:  =('' text.u.row)  &
  $(at next.u.row)
::
++  commit-contents
  |=  data=octets
  ^-  (each facts @tas)
  =/  first  (line data 0)
  ?~  first  [%| %commit-tree]
  =/  root  (oid-line text.u.first 'tree ')
  ?~  root  [%| %commit-tree]
  =/  cursor=@ud  next.u.first
  =/  parents=(list edge)  ~
  =/  seen=(set @ux)  ~
  =/  count=@ud  0
  |-  ^-  (each facts @tas)
  =/  row  (line data cursor)
  ?~  row  [%| %commit-header]
  ?:  =('parent ' (cut 3 [0 7] text.u.row))
    ?:  =(64 count)  [%| %commit-parent-bound]
    =/  parent  (oid-line text.u.row 'parent ')
    ?~  parent  [%| %commit-parent]
    ?:  (~(has in seen) u.parent)  [%| %commit-parent]
    $(cursor next.u.row, parents [[u.parent %commit] parents], seen (~(put in seen) u.parent), count +(count))
  ?.  &((gth (met 3 text.u.row) 7) =('author ' (cut 3 [0 7] text.u.row)))
    [%| %commit-author]
  =/  committer  (line data next.u.row)
  ?~  committer  [%| %commit-committer]
  ?.  &((gth (met 3 text.u.committer) 10) =('committer ' (cut 3 [0 10] text.u.committer)))
    [%| %commit-committer]
  ?.  (header-end data next.u.committer)  [%| %commit-header]
  [%& %commit [u.root %tree] (flop parents)]
::
++  tag-contents
  |=  data=octets
  ^-  (each facts @tas)
  =/  first  (line data 0)
  ?~  first  [%| %tag-target]
  =/  target  (oid-line text.u.first 'object ')
  ?~  target  [%| %tag-target]
  =/  type  (line data next.u.first)
  ?~  type  [%| %tag-type]
  =/  parsed=@tas  (cut 3 [5 7] text.u.type)
  ?.  &(?=(object-kind parsed) =(text.u.type (cat 3 'type ' parsed)))  [%| %tag-type]
  =/  label  (line data next.u.type)
  ?~  label  [%| %tag-name]
  ?.  &((gth (met 3 text.u.label) 4) =('tag ' (cut 3 [0 4] text.u.label)))  [%| %tag-name]
  ?.  (header-end data next.u.label)  [%| %tag-header]
  [%& %tag u.target parsed]
::
++  inspect
  |=  item=object
  ^-  (each facts @tas)
  =/  hashed  (hash-object:stead-code-git-objects kind.item body.item)
  ?~  hashed  [%| %object-kind-or-bound]
  ?.  &(=(oid.item oid.u.hashed) !=(0 oid.item))  [%| %object-oid]
  ?+  kind.item  [%| %object-kind-or-bound]
    %blob  [%& %blob ~]
    %commit  (commit-contents body.item)
    %tag  (tag-contents body.item)
    %tree
      =/  children  (tree-contents body.item)
      ?:  ?=(%| -.children)  [%| p.children]
      [%& %tree p.children]
  ==
::
++  edges
  |=  value=facts
  ^-  (list edge)
  ?-  -.value
    %blob  ~
    %tree  (turn entries.value |=([entry=tree-entry] child.entry))
    %commit  [root.value parents.value]
    %tag  ~[target.value]
  ==
::  The home gives a bounded inventory of requested ref/proposal roots.
++  start
  |=  roots=(list edge)
  ^-  closure
  =/  count  (lent (scag 257 roots))
  ?:  (gth count 256)  [%invalid %root-bound]
  [%checking (turn roots |=([root=edge] [%visit root])) ~ ~ count 32.768 67.108.864]
::
++  walk
  |=  [work=closure load=reader]
  ^-  closure
  ?.  ?=(%checking -.work)  work
  ?~  todo.work  [%verified seen.work]
  ?:  =(0 queued.work)  [%invalid %graph-queue-state]
  =/  action  i.todo.work
  =/  pending=(list path-item)  t.todo.work
  =/  remaining=@ud  (dec queued.work)
  ?:  ?=(%leave -.action)
    [%checking pending seen.work (~(del in active.work) oid.action) remaining visits.work bytes.work]
  ?:  =(0 visits.work)  [%invalid %graph-edge-bound]
  =/  visits=@ud  (dec visits.work)
  =/  [oid=@ux type=object-kind]  +.action
  ?:  (~(has in active.work) oid)  [%invalid %graph-cycle]
  =/  known  (~(get by seen.work) oid)
  ?^  known
    ?.  =(u.known type)  [%invalid %edge-kind]
    [%checking pending seen.work active.work remaining visits bytes.work]
  =/  value  (load oid)
  ?~  value  [%invalid %missing-object]
  ?.  &(=(oid oid.u.value) =(type kind.u.value))  [%invalid %edge-kind]
  ?:  (gth length.body.u.value bytes.work)  [%invalid %graph-byte-bound]
  =/  parsed  (inspect u.value)
  ?:  ?=(%| -.parsed)  [%invalid p.parsed]
  =/  next=(list path-item)  (turn (edges p.parsed) |=([child=edge] [%visit child]))
  =/  queued  (add remaining +((lent next)))
  ?:  (gth queued 32.768)  [%invalid %graph-queue-bound]
  =/  tail=(list path-item)  [[%leave oid] pending]
  [%checking (weld next tail) (~(put by seen.work) oid type) (~(put in active.work) oid) queued visits (sub bytes.work length.body.u.value)]
::
::  Read by exact commit and path inside a closure selected by the home.
::  The caller reauthorizes its principal and roots on every read.
++  read-path
  |=  $:  revision=@ux  path=(list @t)
          allowed=(map @ux object-kind)  load=reader
      ==
  ^-  (each object @tas)
  ?.  &((lte (lent (scag 33 path)) 32) (levy path tree-name))  [%| %path-bound]
  ?~  path  [%| %path-bound]
  ?.  =([~ %commit] (~(get by allowed) revision))  [%| %unavailable]
  =/  commit  (load revision)
  ?~  commit  [%| %unavailable]
  ?.  =(revision oid.u.commit)  [%| %unavailable]
  =/  parsed  (inspect u.commit)
  ?.  ?=([%& %commit *] parsed)  [%| %unavailable]
  =/  oid=@ux  oid.root.p.parsed
  |-  ^-  (each object @tas)
  ?.  =([~ %tree] (~(get by allowed) oid))  [%| %unavailable]
  =/  current  (load oid)
  ?~  current  [%| %unavailable]
  ?.  =(oid oid.u.current)  [%| %unavailable]
  =/  tree  (inspect u.current)
  ?.  ?=([%& %tree *] tree)  [%| %unavailable]
  =/  match  (skim entries.p.tree |=(item=tree-entry =(i.path name.item)))
  ?~  match  [%| %unavailable]
  =/  child=edge  child.i.match
  ?:  ?=(^ t.path)
    ?.  =(%tree type.child)  [%| %unavailable]
    $(path t.path, oid oid.child)
  ?.  &(!=(%tree type.child) =([~ %blob] (~(get by allowed) oid.child)))  [%| %unavailable]
  =/  blob  (load oid.child)
  ?~  blob  [%| %unavailable]
  ?.  &(=(oid.child oid.u.blob) ?=([%& %blob *] (inspect u.blob)))  [%| %unavailable]
  [%& u.blob]
--
