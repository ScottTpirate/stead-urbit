/+  *test, eval-authorization
|%
++  test-writer
  (expect !>(=([~ 1] (advance:eval-authorization ~bus ~bus 0 0))))
++  test-stale
  (expect !>(=(~ (advance:eval-authorization ~bus ~bus 1 0))))
--
