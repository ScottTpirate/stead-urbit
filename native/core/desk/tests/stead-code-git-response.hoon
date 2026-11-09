/+  *test, stead-code-git-response, stead-git
=,  stead-code-git-response
|%
++  refs
  |=  count=@ud
  ^-  (list advertised-ref)
  =/  out=(list advertised-ref)  ~
  |-  ^-  (list advertised-ref)
  ?:  =(0 count)  out
  =/  oid=@ux  (add count 0)
  =/  name=@t  (cat 3 'refs/heads/r' (oid-text:stead-git oid))
  $(count (dec count), out [[name oid ~] out])
++  outcomes
  |=  count=@ud
  ^-  (list ref-result)
  (turn (refs count) |=([ref=advertised-ref] [name.ref [%committed ~]]))
++  test-response-upload-empty
  (expect !>(=([%& 109 0x30.3030.300a.6174.6c65.642d.7366.6f00.7d7b.5e73.6569.7469.6c69.6261.7061.6320.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3734.3030.3030.3030.0a6b.6361.702d.6461.6f6c.7075.2d74.6967.3d65.6369.7672.6573.2023.6531.3030] (discovery %git-upload-pack ~ ~['ofs-delta']))))
++  test-response-receive-empty
  (expect !>(=([%& 114 0x3030.3030.0a73.7574.6174.732d.7472.6f70.6572.007d.7b5e.7365.6974.696c.6962.6170.6163.2030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3062.3430.3030.3030.300a.6b63.6170.2d65.7669.6563.6572.2d74.6967.3d65.6369.7672.6573.2023.6631.3030] (discovery %git-receive-pack ~ ~['report-status']))))
++  test-response-head-first
  (expect !>(=([%& 159 0x30.3030.300a.6e69.616d.2f73.6461.6568.2f73.6665.7220.3130.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.6433.3030.0a61.746c.6564.2d73.666f.0044.4145.4820.3130.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.6333.3030.3030.3030.0a6b.6361.702d.6461.6f6c.7075.2d74.6967.3d65.6369.7672.6573.2023.6531.3030] (discovery %git-upload-pack ~[['HEAD' 0x1 ~] ['refs/heads/main' 0x1 ~]] ~['ofs-delta']))))
++  test-response-peeled-tag
  (expect !>(=([%& 167 0x30.3030.300a.7d7b.5e31.762f.7367.6174.2f73.6665.7220.3130.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.6433.3030.0a61.746c.6564.2d73.666f.0031.762f.7367.6174.2f73.6665.7220.3230.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3434.3030.3030.3030.0a6b.6361.702d.6461.6f6c.7075.2d74.6967.3d65.6369.7672.6573.2023.6531.3030] (discovery %git-upload-pack ~[['refs/tags/v1' 0x2 [~ 0x1]]] ~['ofs-delta']))))
++  test-response-receive-capabilities
  (expect !>(=([%& 143 0x30.3030.300a.6369.6d6f.7461.2061.746c.6564.2d73.666f.2073.6665.722d.6574.656c.6564.2073.7574.6174.732d.7472.6f70.6572.006e.6961.6d2f.7364.6165.682f.7366.6572.2031.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3030.3038.3630.3030.3030.300a.6b63.6170.2d65.7669.6563.6572.2d74.6967.3d65.6369.7672.6573.2023.6631.3030] (discovery %git-receive-pack ~[['refs/heads/main' 0x1 ~]] ~['report-status' 'delete-refs' 'ofs-delta' 'atomic']))))
++  test-response-zero-oid
  (expect !>(=([%| %oid-bound] (discovery %git-upload-pack ~[['refs/heads/a' 0x0 ~]] ~['ofs-delta']))))
++  test-response-wide-oid
  (expect !>(=([%| %oid-bound] (discovery %git-upload-pack ~[['refs/heads/a' (bex 160) ~]] ~['ofs-delta']))))
++  test-response-invalid-ref
  (expect !>(=([%| %invalid-ref] (discovery %git-upload-pack ~[['refs/heads/../a' 0x1 ~]] ~['ofs-delta']))))
++  test-response-duplicate-ref
  (expect !>(=([%| %ref-order] (discovery %git-upload-pack ~[['refs/heads/a' 0x1 ~] ['refs/heads/a' 0x2 ~]] ~['ofs-delta']))))
++  test-response-unsorted-ref
  (expect !>(=([%| %ref-order] (discovery %git-upload-pack ~[['refs/heads/z' 0x1 ~] ['refs/heads/a' 0x2 ~]] ~['ofs-delta']))))
++  test-response-head-late
  (expect !>(=([%| %head-position] (discovery %git-upload-pack ~[['refs/heads/a' 0x1 ~] ['HEAD' 0x1 ~]] ~['ofs-delta']))))
++  test-response-head-peeled
  (expect !>(=([%| %head-position] (discovery %git-upload-pack ~[['HEAD' 0x1 [~ 0x2]]] ~['ofs-delta']))))
++  test-response-branch-peeled
  (expect !>(=([%| %peeled-ref] (discovery %git-upload-pack ~[['refs/heads/a' 0x1 [~ 0x2]]] ~['ofs-delta']))))
++  test-response-zero-peeled
  (expect !>(=([%| %peeled-oid] (discovery %git-upload-pack ~[['refs/tags/a' 0x1 [~ 0x0]]] ~['ofs-delta']))))
++  test-response-wide-peeled
  (expect !>(=([%| %peeled-oid] (discovery %git-upload-pack ~[['refs/tags/a' 0x1 [~ (bex 160)]]] ~['ofs-delta']))))
++  test-response-empty-capabilities
  (expect !>(=([%| %capabilities-empty] (discovery %git-upload-pack ~ ~))))
++  test-response-wrong-service-capability
  (expect !>(=([%| %unsupported-capability] (discovery %git-upload-pack ~ ~['report-status']))))
++  test-response-unknown-capability
  (expect !>(=([%| %unsupported-capability] (discovery %git-receive-pack ~ ~['side-band-64k']))))
++  test-response-duplicate-capability
  (expect !>(=([%| %duplicate-capability] (discovery %git-receive-pack ~ ~['atomic' 'atomic']))))
++  test-response-ref-count-over
  (expect !>(=([%| %ref-bound] (discovery %git-upload-pack (refs 257) ~['ofs-delta']))))
++  test-response-ref-count-at
  =/  result  (discovery %git-upload-pack (refs 256) ~['ofs-delta'])
  (expect !>(?=(%& -.result)))
++  test-response-status-committed
  (expect !>(=([%& 41 0x30.3030.300a.6e69.616d.2f73.6461.6568.2f73.6665.7220.6b6f.3731.3030.0a6b.6f20.6b63.6170.6e75.6530.3030] (report [%unpacked ~] ~[['refs/heads/main' [%committed ~]]]))))
++  test-response-status-rejected
  (expect !>(=([%& 51 0x30.3030.300a.6665.722d.656c.6174.7320.6e69.616d.2f73.6461.6568.2f73.6665.7220.676e.3132.3030.0a6b.6f20.6b63.6170.6e75.6530.3030] (report [%unpacked ~] ~[['refs/heads/main' [%rejected 'stale-ref']]]))))
++  test-response-status-unpack-failed
  (expect !>(=([%& 61 0x30.3030.300a.6465.6c69.6166.2d6b.6361.706e.7520.6e69.616d.2f73.6461.6568.2f73.6665.7220.676e.3532.3030.0a6d.7573.6b63.6568.6320.6b63.6170.6e75.3431.3030] (report [%failed 'checksum'] ~[['refs/heads/main' [%rejected 'unpack-failed']]]))))
++  test-response-status-mixed
  (expect !>(=([%& 65 0x30.3030.300a.6465.696e.6564.2062.2f73.6461.6568.2f73.6665.7220.676e.6231.3030.0a61.2f73.6461.6568.2f73.6665.7220.6b6f.3431.3030.0a6b.6f20.6b63.6170.6e75.6530.3030] (report [%unpacked ~] ~[['refs/heads/a' [%committed ~]] ['refs/heads/b' [%rejected 'denied']]]))))
++  test-response-status-empty
  (expect !>(=([%| %empty-outcomes] (report [%unpacked ~] ~))))
++  test-response-status-contradiction
  (expect !>(=([%| %unpack-failed-success] (report [%failed 'checksum'] ~[['refs/heads/a' [%committed ~]]]))))
++  test-response-status-duplicate
  (expect !>(=([%| %duplicate-ref] (report [%unpacked ~] ~[['refs/heads/a' [%committed ~]] ['refs/heads/a' [%committed ~]]]))))
++  test-response-status-bad-ref
  (expect !>(=([%| %invalid-ref] (report [%unpacked ~] ~[['refs/heads/../a' [%committed ~]]]))))
++  test-response-status-empty-reason
  (expect !>(=([%| %invalid-reason] (report [%unpacked ~] ~[['refs/heads/a' [%rejected '']]]))))
++  test-response-status-ok-error
  (expect !>(=([%| %invalid-reason] (report [%failed 'ok'] ~[['refs/heads/a' [%rejected 'failed']]]))))
++  test-response-status-line-injection
  (expect !>(=([%| %invalid-reason] (report [%unpacked ~] ~[['refs/heads/a' [%rejected (cat 3 'bad' 10)]]]))))
++  test-response-status-long-reason
  (expect !>(=([%| %invalid-reason] (report [%unpacked ~] ~[['refs/heads/a' [%rejected (crip (reap 129 'x'))]]]))))
++  test-response-status-count-over
  (expect !>(=([%| %outcome-bound] (report [%unpacked ~] (outcomes 33)))))
++  test-response-status-count-at
  =/  result  (report [%unpacked ~] (outcomes 32))
  (expect !>(?=(%& -.result)))
++  failure-control
  (expect !>(%.n))
--
