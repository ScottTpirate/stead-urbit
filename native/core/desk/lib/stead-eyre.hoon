::  Pinned kernel HTTP provenance. Guest src alone is not owner authentication.
::  Arvo prepends the vane to an unforgeable routing duct; Gall stores it in sup.
::  Remote Ames and raw Eyre channels cannot choose /eyre/watch-response/<id>.
|%
++  response-source
  |=  [subscriptions=(map duct [ship=@p route=path]) sender=@p id=@ta]
  ^-  ?
  ?.  &((gth (met 3 id) 0) (lte (met 3 id) 128))  |
  =/  route=path  [%http-response id ~]
  =/  found  (skim ~(tap by subscriptions) |=([key=duct val=[ship=@p route=path]] =(route route.val)))
  ?.  ?=([^ ~] found)  |
  =/  key  p.i.found
  =/  value  q.i.found
  ?.  &(=(sender ship.value) ?=(^ key))  |
  =(i.key [%eyre %watch-response id ~])
--
