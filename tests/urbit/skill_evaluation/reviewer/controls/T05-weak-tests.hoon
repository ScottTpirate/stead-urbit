/+  *test, eval-authorization
|%
++  test-writer
  (expect !>(=([~ 1] (advance:eval-authorization ~bus ~bus 0 0))))
++  test-stale
  (expect !>(=(~ (advance:eval-authorization ~bus ~bus 1 0))))
++  test-reader-spoof-denied
  (expect !>(=(~ (advance:eval-authorization ~nec ~bus 4 4))))
++  test-writer-claim-ignored
  (expect !>(=([~ 6] (advance:eval-authorization ~bus ~bud 5 5))))
--
