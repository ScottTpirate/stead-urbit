::  Reserved per-Work Doc Change reads. No public carrier exposes this codec.
::  Metadata pages never contain Markdown; each body read pins one result.
/+  stead-codec, stead-team-codec, stead-product-codec
=,  stead-codec
|%
+$  query
  $:  request=@t  kind=@t  project=@t  work=@t  change=@t
      revision=@ud  digest=@t  side=@t  cursor=@t
  ==
++  valid
  |=  query=query
  ^-  ?
  ?&  (uuid request.query)  (uuid project.query)  (uuid work.query)
      (lte revision.query 18.446.744.073.709.551.615)
      ?|(=('' cursor.query) (opaque:stead-team-codec cursor.query))
      ?:  =('changes' kind.query)
        &(=('' change.query) =(0 revision.query) =('' digest.query) =('' side.query))
      ?&  (uuid change.query)
          ?:  =('results' kind.query)
            &(=(0 revision.query) =('' digest.query) =('' side.query))
          ?&  =('' cursor.query)
              ?:  =('change' kind.query)
                &(=('' side.query) ?:(=(0 revision.query) =('' digest.query) (opaque:stead-team-codec digest.query)))
              &(=('body' kind.query) (gth revision.query 0) (opaque:stead-team-codec digest.query) ?|(=('before' side.query) =('after' side.query)))
          ==
      ==
  ==
++  decode
  |=  raw=@t
  ^-  query
  =/  value  (need (parse-product:stead-product-codec raw))
  ?>  ?=([%o *] value)
  =/  data  p.value
  ?>  (keys data ~['protocol' 'request_id' 'kind' 'project_id' 'work_id' 'change_id' 'result_revision' 'result_digest' 'side' 'cursor'])
  ?>  =('stead.doc-change-query/1' (field data 'protocol'))
  =/  query=query
    :*  (field data 'request_id')  (field data 'kind')
        (field data 'project_id')  (field data 'work_id')
        (field data 'change_id')  (uint (field data 'result_revision'))
        (field data 'result_digest')  (field data 'side')  (field data 'cursor')
    ==
  ?>  (valid query)
  query
++  bytes
  |=  query=query
  ^-  @t
  %-  canonical
  %-  object
  :~  ['protocol' 'stead.doc-change-query/1']
      ['request_id' request.query]  ['kind' kind.query]
      ['project_id' project.query]  ['work_id' work.query]
      ['change_id' change.query]  ['result_revision' (decimal revision.query)]
      ['result_digest' digest.query]  ['side' side.query]  ['cursor' cursor.query]
  ==
--
