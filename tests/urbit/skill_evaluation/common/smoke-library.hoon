::  Synthetic URB-020 probe, not Stead business authorization.
::  Only the explicitly selected fake contributor may increment once per revision.
|%
++  advance
  |=  [sender=@p current=@ud expected=@ud]
  ^-  (unit @ud)
  ?.  =(~bus sender)  ~
  ?.  =(current expected)  ~
  [~ +(current)]
--
