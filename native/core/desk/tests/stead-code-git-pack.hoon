/+  *test, stead-code-git-pack
::  Header/trailer evidence only. Garbage-entry success is an explicit boundary.
|%
++  test-pack-empty-sha-one
  (expect !>(=([%envelope 2 0 0 0x29d.0882.3bd8.a8ea.b510.ad6a.c75c.823c.fd3e.d31e] (inspect:stead-code-git-pack [32 0x1ed3.3efd.3c82.5cc7.6aad.10b5.eaa8.d83b.8208.9d02.0000.0000.0200.0000.4b43.4150]))))
++  test-pack-version-three
  (expect !>(=([%envelope 3 0 0 0x2fa6.1e7a.e3ad.3d91.0155.34aa.edad.d422.d4a3.929b] (inspect:stead-code-git-pack [32 0x9b92.a3d4.22d4.aded.aa34.5501.913d.ade3.7a1e.a62f.0000.0000.0300.0000.4b43.4150]))))
++  test-pack-unsupported-version
  (expect !>(=([%invalid %version] (inspect:stead-code-git-pack [32 0x4e8a.c23b.c173.9392.6e70.ad19.d0fd.d28b.e7e8.36ee.0000.0000.0400.0000.4b43.4150]))))
++  test-pack-declared-count-bound
  (expect !>(=([%invalid %object-count] (inspect:stead-code-git-pack [32 0x80f2.10c6.1df6.eda9.15ce.8e5b.3336.2c2d.5adf.7383.0110.0000.0200.0000.4b43.4150]))))
++  test-pack-signature
  (expect !>(=([%invalid %signature] (inspect:stead-code-git-pack [32 0x1ed3.3efd.3c82.5cc7.6aad.10b5.eaa8.d83b.8208.9d02.0000.0000.0200.0000.4c49.4146]))))
++  test-pack-checksum
  (expect !>(=([%invalid %checksum] (inspect:stead-code-git-pack [32 0x1fd3.3efd.3c82.5cc7.6aad.10b5.eaa8.d83b.8208.9d02.0000.0000.0200.0000.4b43.4150]))))
++  test-pack-empty-payload
  (expect !>(=([%invalid %empty-pack-payload] (inspect:stead-code-git-pack [33 0xb7.48f0.1e23.11ee.df8b.699e.5db3.7503.504b.8c62.e878.0000.0000.0200.0000.4b43.4150]))))
++  test-pack-missing-entries
  (expect !>(=([%invalid %missing-entries] (inspect:stead-code-git-pack [32 0x45bc.3953.e0d1.c97f.8ab9.dc6d.1c4c.9da2.fd19.3045.0100.0000.0200.0000.4b43.4150]))))
++  test-pack-truncated
  (expect !>(=([%invalid %truncated-envelope] (inspect:stead-code-git-pack [31 0xd3.3efd.3c82.5cc7.6aad.10b5.eaa8.d83b.8208.9d02.0000.0000.0200.0000.4b43.4150]))))
++  test-pack-envelope-does-not-validate-entry
  (expect !>(=([%envelope 2 1 1 0xa85b.0ff3.d90f.822c.9d9c.7d64.6eb3.50c8.826e.3347] (inspect:stead-code-git-pack [33 0x47.336e.82c8.50b3.6e64.7d9c.9d2c.820f.d9f3.0f5b.a800.0100.0000.0200.0000.4b43.4150]))))
++  test-pack-byte-bound
  (expect !>(=([%invalid %byte-bound] (inspect:stead-code-git-pack [8.388.609 0]))))
++  test-pack-explicit-width
  (expect !>(=([%invalid %byte-bound] (inspect:stead-code-git-pack [0 1]))))
--
