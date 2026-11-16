::  Original bounded Git object builders for the minimum Stead document slice.
::  No Urgit code. Git byte formats + pinned Hoon SHA-1 primitive only.
::  Pure construction: callers own authorization, reachability and acceptance.
|%
+$  octets  [length=@ud data=@]
+$  object  [kind=@tas body=octets oid=@ux]
+$  entry  [name=@t oid=@ux]
::
++  valid-octets
  |=  value=octets
  ^-  ?
  ?&  (lte length.value 8.388.608)
      (lte (met 3 data.value) length.value)
  ==
::
++  append
  |=  [left=octets right=octets]
  ^-  octets
  ~|  %stead-git-octets
  ?>  (lte (met 3 data.left) length.left)
  ?>  (lte (met 3 data.right) length.right)
  ?>  (lte (add length.left length.right) 8.388.864)
  [(add length.left length.right) (mix data.left (lsh [3 length.left] data.right))]
::
++  decimal
  |=  value=@ud
  ^-  @t
  ~|  %stead-git-number
  ?>  (lte value 18.446.744.073.709.551.615)
  ?:  =(0 value)  '0'
  =/  digits=tape  ~
  |-  ^-  @t
  ?:  =(0 value)  (crip digits)
  $(value (div value 10), digits [(add 48 (mod value 10)) digits])
::
++  oid-text
  |=  value=@ux
  ^-  @t
  ~|  %stead-git-oid
  ?>  (lte (met 0 value) 160)
  =/  remaining=@ud  40
  =/  digits=tape  ~
  |-  ^-  @t
  ?:  =(0 remaining)  (crip digits)
  $(remaining (dec remaining), value (rsh [2 1] value), digits [(snag (end [2 1] value) "0123456789abcdef") digits])
::
++  valid-uuid
  |=  value=@t
  ^-  ?
  ?.  =(36 (met 3 value))  %.n
  =/  index=@ud  0
  |-  ^-  ?
  ?:  =(36 index)  %.y
  =/  byte=@ud  (cut 3 [index 1] value)
  =/  valid=?
    ?:  ?|(=(index 8) =(index 13) =(index 18) =(index 23))
      =(byte 45)
    ?:  =(index 14)  =(byte 55)
    ?:  =(index 19)  ?|(=(byte 56) =(byte 57) =(byte 97) =(byte 98))
    ?|  ?&((gte byte 48) (lte byte 57))
        ?&((gte byte 97) (lte byte 102))
    ==
  ?.  valid  %.n
  $(index +(index))
::
++  valid-name
  |=  value=@t
  ^-  ?
  ?&  =(39 (met 3 value))
      =('.md' (cut 3 [36 3] value))
      (valid-uuid (cut 3 [0 36] value))
  ==
::
++  make-object
  |=  [kind=@tas body=octets]
  ^-  object
  ~|  %stead-git-object
  ?>  ?|(=(kind %blob) =(kind %tree) =(kind %commit))
  ?>  (valid-octets body)
  =/  header=@t  (cat 3 kind (cat 3 ' ' (decimal length.body)))
  =/  raw=octets  (append [(add 1 (met 3 header)) header] body)
  [kind body (sha-1l:sha [length.raw (rev 3 length.raw data.raw)])]
::
++  make-blob
  |=  body=octets
  ^-  object
  (make-object %blob body)
::
++  make-tree
  |=  entries=(list entry)
  ^-  object
  ~|  %stead-git-tree
  =/  pending  entries
  =/  count=@ud  0
  =.  entries
    |-  ^-  (list entry)
    ?~  pending  entries
    ?>  (lth count 32)
    ?>  (valid-name name.i.pending)
    ?>  (lte (met 0 oid.i.pending) 160)
    $(pending t.pending, count +(count))
  =/  ordered=(list entry)
    (sort entries |=([left=entry right=entry] (aor name.left name.right)))
  =/  previous=(unit @t)  ~
  =/  body=octets  [0 0]
  |-  ^-  object
  ?~  ordered  (make-object %tree body)
  ?^  previous
    ?>  !=(u.previous name.i.ordered)
    $(previous ~)
  =/  prefix=@t  (cat 3 '100644 ' name.i.ordered)
  =/  record=octets
    (append [(add 1 (met 3 prefix)) prefix] [20 (rev 3 20 oid.i.ordered)])
  $(ordered t.ordered, previous [~ name.i.ordered], body (append body record))
::
++  make-commit
  |=  [tree=@ux parent=(unit @ux) principal=@t timestamp=@ud document-id=@t revision=@ud]
  ^-  object
  ~|  %stead-git-commit
  ?>  (valid-uuid principal)
  ?>  (valid-uuid document-id)
  ?>  (gth revision 0)
  =/  tree-line=@t  (rap 3 ~['tree ' (oid-text tree) 10])
  =/  parent-line=@t
    ?~  parent  ''
    (rap 3 ~['parent ' (oid-text u.parent) 10])
  =/  identity=@t
    (rap 3 ~['Stead Fixture <' principal '@stead.invalid> ' (decimal timestamp) ' +0000' 10])
  =/  content=@t
    (rap 3 ~[tree-line parent-line 'author ' identity 'committer ' identity 10 'Save ' document-id ' revision ' (decimal revision) 10])
  (make-object %commit [(met 3 content) content])
--
