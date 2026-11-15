::  Reserved per-Work run reads. No public mark or carrier exposes this.
/+  stead-codec, stead-team-codec
=,  stead-codec
|%
+$  query  [request=@t kind=@t project=@t work=@t run=@t cursor=@t]
++  valid
  |=  query=query
  ^-  ?
  ?&  (uuid request.query)  (uuid project.query)  (uuid work.query)
      ?|(=('' cursor.query) (opaque:stead-team-codec cursor.query))
      ?:  =('runs' kind.query)  =('' run.query)
      &(=('run' kind.query) (uuid run.query) =('' cursor.query))
  ==
++  decode
  |=  raw=@t
  ^-  query
  =/  value  (need (parse raw))
  ?>  ?=([%o *] value)
  ?>  (keys p.value ~['protocol' 'request_id' 'kind' 'project_id' 'work_id' 'run_id' 'cursor'])
  ?>  =('stead.run-query/1' (field p.value 'protocol'))
  =/  query=query
    [(field p.value 'request_id') (field p.value 'kind') (field p.value 'project_id') (field p.value 'work_id') (field p.value 'run_id') (field p.value 'cursor')]
  ?>  (valid query)
  query
++  bytes
  |=  query=query
  ^-  @t
  (canonical (object ~[['protocol' 'stead.run-query/1'] ['request_id' request.query] ['kind' kind.query] ['project_id' project.query] ['work_id' work.query] ['run_id' run.query] ['cursor' cursor.query]]))
--
